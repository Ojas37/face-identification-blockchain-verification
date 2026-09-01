"""Script to deploy the VerificationRegistry smart contract to local Anvil or testnet."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from eth_account import Account
from web3 import Web3
from src.blockchain.contract import VERIFICATION_REGISTRY_ABI, VERIFICATION_REGISTRY_BYTECODE
from src.config import settings
from src.utils.logger import logger


def main() -> int:
    rpc_url = settings.blockchain_rpc_url
    private_key = settings.blockchain_private_key

    logger.info("=" * 65)
    logger.info("SMART CONTRACT DEPLOYMENT: VerificationRegistry.sol")
    logger.info("=" * 65)

    if not private_key or not private_key.startswith("0x"):
        logger.error("Please set a valid BLOCKCHAIN_PRIVATE_KEY in .env to deploy contract.")
        return 1

    if not VERIFICATION_REGISTRY_BYTECODE:
        logger.error("Compiled contract bytecode not found in src/blockchain/contracts/VerificationRegistry.json")
        return 1

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        logger.error(
            f"Cannot connect to EVM node at {rpc_url}.\n"
            "Ensure Anvil (or Ganache) is running in a separate terminal:\n"
            "  $ anvil\n"
            "or configure a valid testnet RPC in .env."
        )
        return 1

    account = Account.from_key(private_key)
    logger.info(f"Deployer Account:   {account.address}")
    logger.info(f"Connected to RPC:   {rpc_url} (Chain ID: {w3.eth.chain_id})")

    nonce = w3.eth.get_transaction_count(account.address)
    gas_price = w3.eth.gas_price

    contract_factory = w3.eth.contract(
        abi=VERIFICATION_REGISTRY_ABI,
        bytecode=VERIFICATION_REGISTRY_BYTECODE,
    )

    logger.info("Building deployment transaction...")
    deploy_tx = contract_factory.constructor().build_transaction({
        "from": account.address,
        "nonce": nonce,
        "gas": 1500000,
        "gasPrice": gas_price,
        "chainId": w3.eth.chain_id,
    })

    signed_tx = account.sign_transaction(deploy_tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    logger.info(f"Broadcasted Deployment TX: {tx_hash.hex()}")

    logger.info("Waiting for block confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    contract_address = receipt.get("contractAddress") or receipt.get("contract_address")

    logger.info("\n" + "=" * 65)
    logger.info("✓ CONTRACT DEPLOYED SUCCESSFULLY!")
    logger.info("=" * 65)
    logger.info(f"Contract Address:   {contract_address}")
    block_num = receipt.get("blockNumber") or receipt.get("block_number")
    gas_used = receipt.get("gasUsed") or receipt.get("gas_used")
    logger.info(f"Deployment Block:   #{block_num}")
    logger.info(f"Gas Used:           {gas_used}")
    logger.info("-" * 65)
    logger.info("NEXT STEP: Update your .env file with this address:")
    logger.info(f"REGISTRY_CONTRACT_ADDRESS={contract_address}")
    logger.info("=" * 65 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
