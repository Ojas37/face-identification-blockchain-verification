"""Unit tests for EVM Blockchain Client and Record Storage (Phases 9, 10 & 11)."""

from unittest.mock import MagicMock, patch
import pytest
from hexbytes import HexBytes

from src.blockchain.client import BlockchainClient, BlockchainConnectionError, RecordNotFoundError
from src.pipeline.models import VerificationRecord


def test_blockchain_connection_error():
    """Test that client raises BlockchainConnectionError when RPC endpoint is unreachable."""
    client = BlockchainClient(rpc_url="http://127.0.0.1:99999")
    with pytest.raises(BlockchainConnectionError):
        client.ensure_connection()


def test_blockchain_upload_and_retrieve_mocked():
    """Test end-to-end mocked EVM transaction signing, broadcast, and retrieval."""
    test_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    test_hash = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"

    client = BlockchainClient(
        rpc_url="http://127.0.0.1:8545",
        private_key=test_key,
        mode="calldata",
    )

    # Mock Web3 RPC responses
    mock_w3 = MagicMock()
    mock_w3.is_connected.return_value = True
    mock_w3.eth.get_transaction_count.return_value = 0
    mock_w3.eth.chain_id = 31337
    mock_w3.eth.gas_price = 1000000000

    mock_signed = MagicMock()
    mock_signed.raw_transaction = b"signed_raw_tx_bytes"
    mock_w3.eth.account.sign_transaction.return_value = mock_signed

    tx_hash_hex = "0x9876543210abcdef9876543210abcdef9876543210abcdef9876543210abcdef"
    mock_w3.eth.send_raw_transaction.return_value = HexBytes(tx_hash_hex)

    mock_receipt = {
        "status": 1,
        "blockNumber": 42,
        "gasUsed": 21000,
        "transactionHash": HexBytes(tx_hash_hex),
    }
    mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt
    mock_w3.eth.get_block.return_value = {"timestamp": 1700000000}

    mock_tx = {
        "from": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        "input": HexBytes("0x" + test_hash + "7b7d"),
    }
    mock_w3.eth.get_transaction.return_value = mock_tx
    mock_w3.eth.get_transaction_receipt.return_value = mock_receipt

    client.w3 = mock_w3

    # 1. Test Upload
    record = client.upload_record(
        content_hash=test_hash,
        source="example.com",
        url="https://example.com/post/1",
    )

    assert isinstance(record, VerificationRecord)
    assert record.content_hash == test_hash
    assert record.block_number == 42
    assert record.tx_hash == tx_hash_hex

    # 2. Test Retrieval
    retrieved = client.retrieve_record(content_hash=test_hash, tx_hash=tx_hash_hex)
    assert isinstance(retrieved, VerificationRecord)
    assert retrieved.content_hash == test_hash
    assert retrieved.block_number == 42
