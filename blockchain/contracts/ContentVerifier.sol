// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/**
 * @title ContentVerifier
 * @notice Stores SHA-256 hashes of social media content discovered during
 *         face identification. Provides tamper-evident, on-chain verification
 *         that a specific piece of content was found at a given moment in time.
 */
contract ContentVerifier {
    struct Record {
        string  url;        // URL of the discovered social media content
        string  title;      // Title / caption of the content
        uint256 timestamp;  // Block timestamp when the record was stored
        bool    exists;     // Guard flag to detect presence
    }

    /// @dev Maps keccak256-padded SHA-256 hash → Record
    mapping(bytes32 => Record) private records;

    address public owner;
    uint256 public totalRecords;

    event RecordStored(
        bytes32 indexed contentHash,
        string  url,
        string  title,
        uint256 timestamp
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Store a content hash on-chain.
     * @param contentHash  SHA-256 hash (as bytes32) of the discovered content.
     * @param url          URL where the content was found.
     * @param title        Title/caption of the matched content.
     */
    function storeRecord(
        bytes32 contentHash,
        string calldata url,
        string calldata title
    ) external {
        require(!records[contentHash].exists, "ContentVerifier: record already exists");
        require(bytes(url).length > 0, "ContentVerifier: url cannot be empty");

        records[contentHash] = Record({
            url:       url,
            title:     title,
            timestamp: block.timestamp,
            exists:    true
        });

        totalRecords++;
        emit RecordStored(contentHash, url, title, block.timestamp);
    }

    /**
     * @notice Verify whether a content hash exists on-chain and retrieve its data.
     * @param contentHash  SHA-256 hash (as bytes32) to verify.
     * @return exists      True if the hash is registered on-chain.
     * @return url         URL stored with the record.
     * @return title       Title stored with the record.
     * @return timestamp   Unix timestamp of when the record was stored.
     */
    function verifyRecord(bytes32 contentHash)
        external
        view
        returns (
            bool    exists,
            string  memory url,
            string  memory title,
            uint256 timestamp
        )
    {
        Record storage r = records[contentHash];
        return (r.exists, r.url, r.title, r.timestamp);
    }
}
