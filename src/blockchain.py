import os
import json
from web3 import Web3
import solcx
from dotenv import load_dotenv

load_dotenv()

def _compile_contract():
    try:
        solcx.install_solc('0.8.0')
    except Exception as e:
        print(f"Note: Error installing solc: {e}")
    contract_path = os.path.join(os.path.dirname(__file__), '..', 'contracts', 'EvidenceRegistry.sol')
    with open(contract_path, 'r') as f:
        source = f.read()
    compiled = solcx.compile_source(
        source,
        output_values=['abi', 'bin'],
        solc_version='0.8.0'
    )
    contract_id, contract_interface = compiled.popitem()
    return contract_interface['abi'], contract_interface['bin']

class BlockchainClient:
    def __init__(self, rpc_url=None, private_key=None, use_mock=False):
        self.use_mock = use_mock
        if use_mock:
            # Use EthereumTester for local in-memory simulation
            print("      -> [MOCK] Using local in-memory Web3 provider (EthereumTester)")
            self.w3 = Web3(Web3.EthereumTesterProvider())
            self.account = self.w3.eth.accounts[0]
        else:
            rpc = rpc_url or os.getenv("RPC_URL", "http://127.0.0.1:8545")
            print(f"      -> Connecting to Web3 RPC: {rpc}")
            self.w3 = Web3(Web3.HTTPProvider(rpc))
            self.private_key = private_key or os.getenv("PRIVATE_KEY")
            if not self.private_key:
                raise ValueError("PRIVATE_KEY must be set for live network interaction")
            self.account = self.w3.eth.account.from_key(self.private_key).address

        if not self.w3.is_connected():
            raise ConnectionError("Failed to connect to the blockchain RPC")

        print("      -> Compiling EvidenceRegistry.sol...")
        self.abi, self.bytecode = _compile_contract()
        self.contract = None

    def deploy_contract(self):
        print("      -> Deploying EvidenceRegistry contract...")
        EvidenceRegistry = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        
        if self.use_mock:
            tx_hash = EvidenceRegistry.constructor().transact({'from': self.account})
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            self.contract = self.w3.eth.contract(address=tx_receipt.contractAddress, abi=self.abi)
        else:
            # Live deployment
            transaction = EvidenceRegistry.constructor().build_transaction({
                'from': self.account,
                'nonce': self.w3.eth.get_transaction_count(self.account),
                'gas': 2000000,
                'gasPrice': self.w3.eth.gas_price
            })
            signed_tx = self.w3.eth.account.sign_transaction(transaction, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            self.contract = self.w3.eth.contract(address=tx_receipt.contractAddress, abi=self.abi)

        print(f"      -> Contract deployed at: {self.contract.address}")
        return self.contract.address

    def record_evidence(self, digest):
        print(f"      -> Recording evidence hash {digest} on-chain...")
        hash_bytes = self.w3.to_bytes(hexstr=digest)
        if self.use_mock:
            tx_hash = self.contract.functions.recordEvidence(hash_bytes).transact({'from': self.account})
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
        else:
            transaction = self.contract.functions.recordEvidence(hash_bytes).build_transaction({
                'from': self.account,
                'nonce': self.w3.eth.get_transaction_count(self.account),
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price
            })
            signed_tx = self.w3.eth.account.sign_transaction(transaction, private_key=self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
        print("      -> Evidence successfully recorded!")

    def verify_evidence(self, digest):
        print(f"      -> Verifying evidence hash {digest} on-chain...")
        hash_bytes = self.w3.to_bytes(hexstr=digest)
        exists, timestamp = self.contract.functions.verifyEvidence(hash_bytes).call()
        if exists:
            print(f"      -> [SUCCESS] MATCH CONFIRMED (VERIFIED). Evidence found on-chain at timestamp {timestamp}.")
            return True, timestamp
        else:
            print("      -> [FAILED] TAMPER DETECTED (UNVERIFIED). No matching record found on-chain.")
            return False, 0
