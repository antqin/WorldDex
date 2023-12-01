from fastapi import FastAPI, HTTPException
from web3 import Web3
from web3.middleware import geth_poa_middleware
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Ethereum node connection
WEB3_PROVIDER_URI = os.getenv("WEB3_PROVIDER")
web3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER_URI))

# Inject middleware for compatibility with networks like Binance Smart Chain
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Contract details
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

# Load the ABI from the file
with open('contract_abi.txt', 'r') as abi_file:
    CONTRACT_ABI = json.load(abi_file)

contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

# Wallet details for the transaction sender
WALLET_PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS")

@app.post("/mint-nft/")
async def mint_nft(cid: str, user_address: str):
    # Ensure Ethereum address is valid
    if not web3.is_address(user_address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address")

    # Token URI (IPFS URL)
    token_uri = f"ipfs://{cid}"

    # Create a transaction
    nonce = web3.eth.get_transaction_count(WALLET_ADDRESS)
    # Prepare the transaction
    txn = contract.functions.mintNFT(user_address, token_uri).build_transaction({
        'from': WALLET_ADDRESS,  # The address the transaction is sent from
        'chainId': 11155111,  # Replace with the correct chain ID
        'gas': 2000000,
        'gasPrice': web3.to_wei('50', 'gwei'),
        'nonce': nonce,
    })


    # Sign the transaction
    signed_txn = web3.eth.account.sign_transaction(txn, private_key=WALLET_PRIVATE_KEY)

    # Send the transaction
    txn_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)

    # Wait for transaction receipt (optional)
    receipt = web3.eth.wait_for_transaction_receipt(txn_hash)

    return {"transaction_hash": receipt.transactionHash.hex(), "status": "NFT Minted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)