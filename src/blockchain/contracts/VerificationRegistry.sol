// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title VerificationRegistry
 * @dev Immutable on-chain registry for face identification content hashes and provenance metadata.
 */
contract VerificationRegistry {
    struct Record {
        bytes32 contentHash;
        string source;
        string url;
        uint256 timestamp;
        address recorder;
    }

    // Mapping from content SHA-256 hash to Record
    mapping(bytes32 => Record) public records;

    // Emitted when a new verification record is permanently anchored to the blockchain
    event RecordStored(
        bytes32 indexed contentHash,
        string source,
        string url,
        uint256 timestamp,
        address indexed recorder
    );

    /**
     * @notice Store a cryptographic verification fingerprint.
     * @param _contentHash The 32-byte SHA-256 hash of the canonical post data.
     * @param _source The source platform/domain.
     * @param _url The original source URL.
     */
    function storeRecord(
        bytes32 _contentHash,
        string calldata _source,
        string calldata _url
    ) external {
        require(records[_contentHash].timestamp == 0, "Record already exists");

        records[_contentHash] = Record({
            contentHash: _contentHash,
            source: _source,
            url: _url,
            timestamp: block.timestamp,
            recorder: msg.sender
        });

        emit RecordStored(_contentHash, _source, _url, block.timestamp, msg.sender);
    }

    /**
     * @notice Retrieve an existing verification record by content hash.
     * @param _contentHash The 32-byte SHA-256 hash to query.
     */
    function getRecord(bytes32 _contentHash)
        external
        view
        returns (
            bytes32 contentHash,
            string memory source,
            string memory url,
            uint256 timestamp,
            address recorder
        )
    {
        Record memory r = records[_contentHash];
        require(r.timestamp > 0, "Record not found");
        return (r.contentHash, r.source, r.url, r.timestamp, r.recorder);
    }
}
