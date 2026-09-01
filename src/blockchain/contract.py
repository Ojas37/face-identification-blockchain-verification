"""Smart contract ABI definition and interface utilities."""

from __future__ import annotations

import json
from typing import Any, Dict, List

# Standard ABI for VerificationRegistry
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
