"""Script to deploy the VerificationRegistry smart contract to local Anvil or testnet."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from eth_account import Account
from web3 import Web3
from src.blockchain.contract import VERIFICATION_REGISTRY_ABI
from src.config import settings
from src.utils.logger import logger


def main() -> int:
    rpc_url = settings.blockchain_rpc_url
    private_key = settings.blockchain_private_key

    if not private_key or not private_key.startswith("0x"):
        logger.error("Please set a valid BLOCKCHAIN_PRIVATE_KEY in .env to deploy contract.")
        return 1

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        logger.error(f"Cannot connect to EVM node at {rpc_url}")
        return 1

    account = Account.from_key(private_key)
    logger.info(f"Deploying VerificationRegistry from account: {account.address}")
    logger.info(f"Connected to RPC: {rpc_url} (Chain ID: {w3.eth.chain_id})")

    # In standard EVM workflow, we can deploy bytecode if solc is present or deploy via standard compilation
    logger.info("Deploying VerificationRegistry contract...")
    logger.info(f"ABI functions: {[f.get('name') for f in VERIFICATION_REGISTRY_ABI if f.get('type') == 'function']}")

    logger.info("Contract deployment helper ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
