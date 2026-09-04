// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract EvidenceRegistry {
    // Mapping from hash to timestamp
    mapping(bytes32 => uint256) public records;

    // Event for new evidence
    event EvidenceRecorded(bytes32 indexed hash, uint256 timestamp);

    function recordEvidence(bytes32 hash) external {
        require(records[hash] == 0, "Evidence already recorded");
        records[hash] = block.timestamp;
        emit EvidenceRecorded(hash, block.timestamp);
    }

    function verifyEvidence(bytes32 hash) external view returns (bool exists, uint256 timestamp) {
        if (records[hash] != 0) {
            return (true, records[hash]);
        }
        return (false, 0);
    }
}
