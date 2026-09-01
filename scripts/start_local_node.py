"""Local EVM JSON-RPC Server Provider.
Runs a local EVM node listening on http://127.0.0.1:8545 using eth-tester/py-evm.
Alternative to Anvil / Ganache for zero-dependency local testing.
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from eth_tester import EthereumTester, PyEVMBackend
from eth_utils import to_hex, to_bytes
from web3 import Web3, EthereumTesterProvider
from src.utils.logger import logger


def serialize_eth_data(obj):
    """Recursively convert bytes/HexBytes/tuples/non-JSON types to JSON-serializable primitives."""
    if isinstance(obj, (bytes, bytearray)):
        return "0x" + bytes(obj).hex()
    if isinstance(obj, (list, tuple, set)):
        return [serialize_eth_data(x) for x in obj]
    if isinstance(obj, dict):
        return {k: serialize_eth_data(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return serialize_eth_data(vars(obj))
    return obj


def normalize_rpc_params(method, params):
    """Normalize standard Ethereum JSON-RPC hex arguments and defaults for eth-tester."""
    if not params:
        return params
    params = list(params)
    if method == "eth_call":
        if params and isinstance(params[0], dict):
            tx_dict = dict(params[0])
            if "from" not in tx_dict or not tx_dict["from"]:
                tx_dict["from"] = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
            params[0] = tx_dict
    elif method in ("eth_getBlockByNumber", "eth_getBlockTransactionCountByNumber"):
        if isinstance(params[0], str) and params[0].startswith("0x"):
            params[0] = int(params[0], 16)
    elif method in ("eth_getTransactionByBlockNumberAndIndex",):
        if isinstance(params[0], str) and params[0].startswith("0x"):
            params[0] = int(params[0], 16)
        if len(params) > 1 and isinstance(params[1], str) and params[1].startswith("0x"):
            params[1] = int(params[1], 16)
    return params


class EVMServerHandler(BaseHTTPRequestHandler):
    """Handles standard Ethereum JSON-RPC HTTP POST requests."""

    provider: EthereumTesterProvider

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_len)

        try:
            req = json.loads(post_data.decode("utf-8"))
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        # Execute RPC request against EthereumTesterProvider
        if isinstance(req, list):
            # Batch request
            responses = []
            for item in req:
                method = item.get("method")
                params = normalize_rpc_params(method, item.get("params", []))
                resp = self.provider.make_request(method, params)
                resp["id"] = item.get("id")
                resp["jsonrpc"] = "2.0"
                responses.append(serialize_eth_data(resp))
            response_body = json.dumps(responses).encode("utf-8")
        else:
            method = req.get("method")
            params = normalize_rpc_params(method, req.get("params", []))
            resp = self.provider.make_request(method, params)
            resp["id"] = req.get("id")
            resp["jsonrpc"] = "2.0"
            resp = serialize_eth_data(resp)
            response_body = json.dumps(resp).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        # Silence HTTP access noise in CLI
        pass


def run_server(host: str = "127.0.0.1", port: int = 8545) -> None:
    backend = PyEVMBackend()
    eth_tester = EthereumTester(backend)
    provider = EthereumTesterProvider(eth_tester)

    # Pre-fund default Anvil test account: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
    default_anvil_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    target_address = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    
    genesis_accounts = eth_tester.get_accounts()
    if genesis_accounts:
        # Transfer 1000 ETH from genesis account to target account
        eth_tester.send_transaction({
            "from": genesis_accounts[0],
            "to": target_address,
            "value": 1000 * 10**18,
            "gas": 21000,
        })

    eth_tester.add_account(default_anvil_key)

    logger.info("=" * 65)
    logger.info("LOCAL EVM NODE RUNNING (eth-tester / py-evm)")
    logger.info("=" * 65)
    logger.info(f"JSON-RPC Endpoint:  http://{host}:{port}")
    logger.info(f"Pre-funded Account: {target_address} (Balance: 1000 ETH)")
    logger.info(f"Private Key:        {default_anvil_key}")
    logger.info("=" * 65)
    logger.info("Ready for deploy_contract.py and main.py transactions...")

    EVMServerHandler.provider = provider
    server = HTTPServer((host, port), EVMServerHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nStopping local EVM server.")
        server.server_close()


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 8545
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run_server(host, port)
