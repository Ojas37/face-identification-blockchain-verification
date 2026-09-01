"""Smart contract ABI and bytecode definition for VerificationRegistry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

CONTRACT_JSON_PATH = Path(__file__).resolve().parent / "contracts" / "VerificationRegistry.json"

if CONTRACT_JSON_PATH.exists():
    with open(CONTRACT_JSON_PATH, "r", encoding="utf-8") as f:
        _artifact = json.load(f)
        VERIFICATION_REGISTRY_ABI: List[Dict[str, Any]] = _artifact.get("abi", [])
        VERIFICATION_REGISTRY_BYTECODE: str = _artifact.get("bytecode", "")
else:
    # Fallback standard ABI
    VERIFICATION_REGISTRY_ABI: List[Dict[str, Any]] = [
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "internalType": "bytes32", "name": "contentHash", "type": "bytes32"},
                {"indexed": False, "internalType": "string", "name": "source", "type": "string"},
                {"indexed": False, "internalType": "string", "name": "url", "type": "string"},
                {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
                {"indexed": True, "internalType": "address", "name": "recorder", "type": "address"},
            ],
            "name": "RecordStored",
            "type": "event",
        },
        {
            "inputs": [
                {"internalType": "bytes32", "name": "_contentHash", "type": "bytes32"},
                {"internalType": "string", "name": "_source", "type": "string"},
                {"internalType": "string", "name": "_url", "type": "string"},
            ],
            "name": "storeRecord",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "bytes32", "name": "_contentHash", "type": "bytes32"},
            ],
            "name": "getRecord",
            "outputs": [
                {"internalType": "bytes32", "name": "contentHash", "type": "bytes32"},
                {"internalType": "string", "name": "source", "type": "string"},
                {"internalType": "string", "name": "url", "type": "string"},
                {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                {"internalType": "address", "name": "recorder", "type": "address"},
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "bytes32", "name": "", "type": "bytes32"},
            ],
            "name": "records",
            "outputs": [
                {"internalType": "bytes32", "name": "contentHash", "type": "bytes32"},
                {"internalType": "string", "name": "source", "type": "string"},
                {"internalType": "string", "name": "url", "type": "string"},
                {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                {"internalType": "address", "name": "recorder", "type": "address"},
            ],
            "stateMutability": "view",
            "type": "function",
        },
    ]
    VERIFICATION_REGISTRY_BYTECODE = ""
