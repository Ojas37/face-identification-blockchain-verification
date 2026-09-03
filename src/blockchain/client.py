"""EVM Blockchain interaction client using Web3.py for real immutable records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from eth_account import Account
from eth_account.signers.local import LocalAccount
from hexbytes import HexBytes
from web3 import Web3
from web3.exceptions import ContractLogicError, TransactionNotFound

from src.config import settings
from src.blockchain.contract import VERIFICATION_REGISTRY_ABI
from src.pipeline.models import VerificationRecord
from src.utils.logger import logger


class BlockchainError(Exception):
    """Base exception for blockchain interaction failures."""
    pass


class BlockchainConnectionError(BlockchainError):
    """Exception raised when unable to connect to RPC node."""
    pass


class RecordNotFoundError(BlockchainError):
    """Exception raised when querying a record that does not exist on-chain."""
    pass


class BlockchainClient:
    """
    EVM blockchain client supporting real on-chain record submission and retrieval
    via Anvil local EVM or public testnets (Polygon Amoy / Ethereum Sepolia).
    """

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        contract_address: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> None:
        self.rpc_url = rpc_url or settings.blockchain_rpc_url
        self.raw_private_key = private_key or settings.blockchain_private_key
        self.contract_address = contract_address or settings.registry_contract_address
        self.mode = mode or settings.blockchain_mode

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.account: Optional[LocalAccount] = None

        self._init_account()
        self.contract = None
        if self.contract_address and self.w3.is_address(self.contract_address):
            checksum_addr = self.w3.to_checksum_address(self.contract_address)
            self.contract = self.w3.eth.contract(
                address=checksum_addr,
                abi=VERIFICATION_REGISTRY_ABI,
            )

    def _init_account(self) -> None:
        """Initialize signing account from private key or test key."""
        if self.raw_private_key and self.raw_private_key.startswith("0x") and len(self.raw_private_key) == 66:
            try:
                self.account = Account.from_key(self.raw_private_key)
            except Exception as e:
                logger.warning(f"Failed to load configured private key: {e}")

    def is_connected(self) -> bool:
        """Check if Web3 RPC provider is reachable."""
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    def ensure_connection(self) -> None:
        """Ensure connection to blockchain node or raise BlockchainConnectionError."""
        if not self.is_connected():
            raise BlockchainConnectionError(
                f"Cannot connect to EVM RPC node at {self.rpc_url}. "
                "Ensure local node (Anvil/Ganache) is running or valid testnet RPC is configured in .env."
            )

    def upload_record(
        self,
        content_hash: str,
        source: str,
        url: str,
    ) -> VerificationRecord:
        """
        Submit a SHA-256 content fingerprint to the blockchain.

        Args:
            content_hash: 64-character hex SHA-256 digest string.
            source: Source platform/domain.
            url: Source content URL.

        Returns:
            VerificationRecord with confirmed transaction metadata.
        """
        self.ensure_connection()

        if not self.account:
            raise BlockchainError(
                "No valid BLOCKCHAIN_PRIVATE_KEY configured to sign EVM transactions."
            )

        # Normalize hash to 32 bytes
        clean_hash = content_hash.strip().lower()
        if clean_hash.startswith("0x"):
            clean_hash = clean_hash[2:]
        if len(clean_hash) != 64:
            raise ValueError(f"Expected 64-char SHA-256 hex string, got {len(clean_hash)} chars.")

        hash_bytes32 = bytes.fromhex(clean_hash)
        sender_address = self.account.address
        nonce = self.w3.eth.get_transaction_count(sender_address)
        chain_id = self.w3.eth.chain_id
        gas_price = self.w3.eth.gas_price

        logger.info(f"[BLOCKCHAIN] Preparing transaction for hash: {clean_hash[:16]}...")
        logger.info(f"[BLOCKCHAIN] Sender Account: {sender_address} (Nonce: {nonce})")

        if self.contract and self.mode == "contract":
            # Smart Contract Execution
            try:
                gas_est = self.contract.functions.storeRecord(
                    hash_bytes32,
                    source,
                    url,
                ).estimate_gas({"from": sender_address})
                gas_limit = int(gas_est * 1.3) + 25000
            except Exception:
                gas_limit = 400000

            tx = self.contract.functions.storeRecord(
                hash_bytes32,
                source,
                url,
            ).build_transaction({
                "from": sender_address,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "chainId": chain_id,
            })
        else:
            # Calldata fallback mode
            payload = {
                "hash": clean_hash,
                "source": source,
                "url": url,
            }
            calldata = "0x" + clean_hash + json.dumps(payload).encode("utf-8").hex()
            tx = {
                "to": sender_address,
                "value": 0,
                "data": calldata,
                "nonce": nonce,
                "gas": 100000,
                "gasPrice": gas_price,
                "chainId": chain_id,
            }

        # Sign transaction locally using private key
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=self.account.key)

        # Broadcast raw transaction
        tx_hash_bytes = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        raw_hex = tx_hash_bytes.hex()
        tx_hash = "0x" + raw_hex if not raw_hex.startswith("0x") else raw_hex
        logger.info(f"[BLOCKCHAIN] Broadcasted TX: {tx_hash}")

        # Wait for block confirmation
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=60)
        status = receipt.get("status")
        if status != 1:
            raise BlockchainError(f"Transaction reverted on-chain. TX: {tx_hash}")

        block_num = receipt.get("blockNumber") or receipt.get("block_number")
        gas_used = receipt.get("gasUsed") or receipt.get("gas_used")
        block = self.w3.eth.get_block(block_num)
        block_timestamp = block.get("timestamp", 0)

        logger.info(
            f"[BLOCKCHAIN] ✓ TX Confirmed in Block #{block_num} "
            f"(Gas Used: {gas_used})"
        )

        return VerificationRecord(
            content_hash=clean_hash,
            source=source,
            url=url,
            timestamp=block_timestamp,
            tx_hash=tx_hash,
            block_number=block_num,
            recorder=sender_address,
        )

    def retrieve_record(
        self,
        content_hash: str,
        tx_hash: Optional[str] = None,
    ) -> VerificationRecord:
        """
        Retrieve on-chain verification record by content hash or transaction hash.

        Args:
            content_hash: 64-character SHA-256 fingerprint.
            tx_hash: Optional transaction hash to query directly.

        Returns:
            VerificationRecord retrieved from blockchain state.
        """
        self.ensure_connection()

        clean_hash = content_hash.strip().lower()
        if clean_hash.startswith("0x"):
            clean_hash = clean_hash[2:]

        # 1. If contract is available and configured, query smart contract state
        if self.contract and self.mode == "contract":
            try:
                hash_bytes32 = bytes.fromhex(clean_hash)
                record_data = self.contract.functions.getRecord(hash_bytes32).call()
                ret_hash_bytes, source, url, timestamp, recorder = record_data
                ret_hash = ret_hash_bytes.hex().lower()
                if ret_hash.startswith("0x"):
                    ret_hash = ret_hash[2:]

                return VerificationRecord(
                    content_hash=ret_hash,
                    source=source,
                    url=url,
                    timestamp=timestamp,
                    tx_hash=tx_hash,
                    recorder=recorder,
                )
            except ContractLogicError as e:
                raise RecordNotFoundError(f"Record for hash {clean_hash} not found in smart contract.") from e
            except Exception as e:
                logger.debug(f"Contract call error, falling back to transaction lookup if tx_hash provided: {e}")

        # 2. Fallback to transaction data inspection if tx_hash is provided
        if tx_hash:
            try:
                tx = self.w3.eth.get_transaction(tx_hash)
                receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                block_num = receipt.get("blockNumber") or receipt.get("block_number")
                block = self.w3.eth.get_block(block_num)

                raw_input = tx.get("input", "")
                if isinstance(raw_input, HexBytes):
                    raw_input = raw_input.hex()

                # Extract stored hash from input data
                input_clean = raw_input[2:] if raw_input.startswith("0x") else raw_input
                stored_hash = input_clean[:64].lower()

                return VerificationRecord(
                    content_hash=stored_hash,
                    source="on-chain tx",
                    url=f"tx:{tx_hash}",
                    timestamp=block.get("timestamp", 0),
                    tx_hash=tx_hash,
                    block_number=block_num,
                    recorder=tx.get("from"),
                )
            except TransactionNotFound as e:
                raise RecordNotFoundError(f"Transaction {tx_hash} not found on chain.") from e

        raise RecordNotFoundError(f"Unable to retrieve verification record for hash {clean_hash}.")
