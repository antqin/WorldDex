from fastapi import FastAPI, File, UploadFile, HTTPException, Form, status
from web3 import Web3
from web3.middleware import geth_poa_middleware
from typing import Optional
from cryptography.fernet import Fernet
import base64
import json
import os
from httpx import AsyncClient, TimeoutException
from parse_public import eth_address_to_pub_key
from ecies import encrypt, decrypt
from io import BytesIO
from azure.storage.blob import BlobServiceClient, ContainerClient, generate_blob_sas, BlobSasPermissions
from azure.data.tables import TableServiceClient, TableEntity
import threading
from typing import List
from urllib.parse import urlparse
import hashlib
from dotenv import load_dotenv
import datetime
import time
import asyncio
from starlette.concurrency import run_in_threadpool
import pytz

lock = threading.Lock()

load_dotenv()

app = FastAPI()

# Set your NFT.storage API key in environment variable
nft_storage_api_key = os.environ.get('NFT_STORAGE_API_KEY')
# Set Etherscan API Key
etherscan_api_key = os.environ.get('ETHERSCAN_API_KEY')
# Set Web3 Provider
web3provider = os.environ.get('WEB3_PROVIDER')

# Azure storage account details
account_name = "worlddexstorage2"
blob_storage_name = "dex-storage"
account_key = os.environ.get("BLOB_ACCOUNT_KEY")
connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"

# Initialize Azure Blob Service Client
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Initialize Azure Table Service Client
table_service_client = TableServiceClient.from_connection_string(connection_string)
table_client = table_service_client.get_table_client(table_name="dextablestorage")
users_table_client = table_service_client.get_table_client(table_name="users")

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

@app.get("/userData")
async def user_data(username: str):
    # try:
        # Query for the specific user
    filter_query = f"PartitionKey eq '{username}' and RowKey eq 'userinfo'"
    user_entities = list(users_table_client.query_entities(filter_query))

    if not user_entities:
        raise HTTPException(status_code=404, detail="User not found")

    user_entity = user_entities[0]

    # Assuming 'Email' and 'EthereumAddress' are the field names in your table
    email = user_entity.get('Email', 'No email provided')
    ethereum_address = user_entity.get('EthereumAddress', 'No Ethereum address provided')

    return {"email": email, "ethereum_address": ethereum_address}
# except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))

@app.post("/registerUser")
async def register_user(username: str, password: str, email: str, ethereum_address: str = None):
    try:
        # Check if username already exists
        username_query = f"PartitionKey eq '{username}'"
        existing_users_by_username = list(users_table_client.query_entities(username_query))
        if existing_users_by_username:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Check if email already exists
        email_query = f"Email eq '{email}'"
        existing_users_by_email = list(users_table_client.query_entities(email_query))
        if existing_users_by_email:
            raise HTTPException(status_code=400, detail="Email already exists")

        # Hash the password
        hashed_password = hash_password(password)

        # Create user entity
        user_entity = TableEntity()
        user_entity['PartitionKey'] = username
        user_entity['RowKey'] = 'userinfo'  # Or some other suitable row key
        user_entity['Password'] = hashed_password
        user_entity['Email'] = email
        user_entity['EthereumAddress'] = ethereum_address

        # Add to table
        users_table_client.create_entity(user_entity)

        return {"message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

      
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    filter_query = f"PartitionKey eq '{username}' and RowKey eq 'userinfo'"
    user_entities = list(users_table_client.query_entities(filter_query))

    if not user_entities:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid username or password")

    user_entity = user_entities[0]
    hashed_password = hash_password(password)

    if user_entity['Password'] == hashed_password:
        return {"status": "success", "message": "Login successful"}
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                            detail="Invalid username or password")
      
@app.get("/getAllUsernames")
async def get_all_usernames():
    try:
        # Query to retrieve all user entities
        filter_query = "RowKey eq 'userinfo'"  # Assuming 'userinfo' is the RowKey for all user entries
        user_entities = users_table_client.query_entities(filter_query)

        # Extracting usernames (PartitionKey)
        usernames = [entity['PartitionKey'] for entity in user_entities]

        return {"usernames": usernames}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/getUserImageUrls")
async def get_user_image_urls(user_id: str):
    # try:
        filter_query = f"PartitionKey eq '{user_id}'"
        queried_entities = table_client.query_entities(filter_query)

        processed_entries = convert_queries_to_entries(queried_entities)

        return {"images": processed_entries}

    # except Exception as e:
    #     raise HTTPException(status_code=500, detail="Internal Server Error")
      
@app.get("/excludeUserImageUrls")
async def exclude_user_images_urls(user_id: str, page: int = 1, items_per_page: int = 3):
  try:
      start_index = (page - 1) * items_per_page
      end_index = start_index + items_per_page
      filter_query = f"PartitionKey ne '{user_id}'"
      queried_entities = table_client.query_entities(filter_query)
      
      processed_entries = convert_queries_to_entries(queried_entities)
      sorted_entries = sorted(processed_entries, key=lambda x: x['date_added'], reverse=True)

      paginated_entries = sorted_entries[start_index:end_index]
      
      return {"images": paginated_entries}
  except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error")
      
def create_service_sas_blob(blob_url: str, account_key: str):
    # Parse the URL to get blob container and name
    parsed_url = urlparse(blob_url)
    blob_path = parsed_url.path.lstrip('/')  # Remove leading '/'
    container_name, blob_name = blob_path.split('/', 1)

    # Create a SAS token valid for one day
    start_time = datetime.datetime.now(datetime.timezone.utc)
    expiry_time = start_time + datetime.timedelta(days=1)

    sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=BlobSasPermissions(read=True),
        expiry=expiry_time,
        start=start_time
    )

    return f"{blob_url}?{sas_token}"

def convert_queries_to_entries(queries):
    result = []
    for entity in queries:
        cropped_image_blob_url = entity.get('CroppedImageBlobURL', '')
        image_blob_url = entity.get('ImageBlobURL', '')

        # Generate SAS URLs
        if cropped_image_blob_url:
            cropped_image_blob_url = create_service_sas_blob(cropped_image_blob_url, account_key)
        if image_blob_url:
            image_blob_url = create_service_sas_blob(image_blob_url, account_key)

        image_info = {
            "image_id": entity['RowKey'],
            "user_id": entity['PartitionKey'],
            "ipfs_cid": entity.get('IPFSCid', ''),
            "date_added": entity.get('DateAdded', ''),
            "location_taken": entity.get('LocationTaken', ''),
            "details": entity.get('Details', ''),
            "probability": entity.get('Probability', ''),
            "image_classification": entity.get('ImageClassification', ''),
            "cropped_image_url": cropped_image_blob_url,
            "image_url": image_blob_url
        }
        result.append(image_info)
    return result

@app.post("/upload")
async def upload(
    image_base64: str = Form(...), 
    cropped_image_base64: str = Form(...), 
    decentralize_storage: Optional[str] = Form("false"), 
    eth_address: Optional[str] = Form(None), 
    user_id: str = Form(...), 
    location_taken: str = Form(...), 
    details: str = Form(...), 
    probability: str = Form(...),
    image_classification: str = Form(...)
):
    start_time = time.time()  # Start timing

    if not await is_valid_username(user_id):
      raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # print(f"User validation completed in {time.time() - start_time} seconds")
    
    decentralize_storage_bool = decentralize_storage.lower() in ["true", "1", "yes"]
        
    # Convert base64 images back to bytes for decentralized upload
    cropped_image_content = base64.b64decode(cropped_image_base64)
    image_content = base64.b64decode(image_base64)
    decentralized_upload_successful = False
    metadata_cid = None
    metadata_url = ""
    
    if decentralize_storage_bool:
      segment_start = time.time()
      # print(f'eth address: {eth_address}\n')
      public_key, _ = eth_address_to_pub_key(eth_address, etherscan_api_key, "SEP", web3provider)
      public_key_hex = public_key.to_hex()
      encrypted_key, encrypted_image = encrypt_image(cropped_image_content, public_key_hex)
      # print(f"Encryption and key retrieval completed in {time.time() - segment_start} seconds")

      segment_start = time.time()
      # NFT Storage Upload
      async with AsyncClient() as client:
        image_cid = await upload_to_nft_storage(client, encrypted_image, image_classification)
        # print(f"NFT storage upload completed in {time.time() - segment_start} seconds")

        segment_start = time.time()
        # Prepare metadata
        metadata = {
            "name": "Encrypted Image",
            "description": "An encrypted image with its encrypted symmetric key",
            "image": f"ipfs://{image_cid}",
            "properties": {"encrypted_key": encrypted_key}
        }

        metadata_cid = await upload_metadata_to_nft_storage(client, metadata, image_cid)
        metadata_url = f"https://{metadata_cid}.ipfs.nftstorage.link"
        # print(f"Metadata upload completed in {time.time() - segment_start} seconds")

        decentralized_upload_successful = True
        if decentralized_upload_successful:
            segment_start = time.time()
            mint_response = await mint_nft(metadata_cid, eth_address)
            # print(f"NFT minting completed in {time.time() - segment_start} seconds")


    # Centralized upload logic
    segment_start = time.time()
    image_id = get_next_image_id()  # Get a unique image identifier
    # print(f"Image ID generation completed in {time.time() - segment_start} seconds")

    segment_start = time.time()
    # Call to centralized upload function
    centralized_upload_response = await centralized_upload(
        image=image_content,
        cropped_image=cropped_image_content,
        user_id=user_id,
        image_id=image_id,
        location_taken=location_taken,
        user_address=eth_address,
        details=details,
        probability=probability,
        image_classification=image_classification,
        ipfs_cid=metadata_cid or "N/A"
    )
    # print(f"Centralized upload completed in {time.time() - segment_start} seconds")

    total_time = time.time() - start_time
    # print(f"Total upload process completed in {total_time} seconds")
    
    return {
        "decentralized_upload": decentralized_upload_successful,
        "centralized_upload": centralized_upload_response,
        "message": "Upload process completed.",
        "metadata_cid": metadata_cid,
        "metadata_url": metadata_url
    }

    
async def upload_to_nft_storage(client, encrypted_image, image_classification):
    image_response = await client.post(
        'https://api.nft.storage/upload',
        files={'file': (image_classification, encrypted_image, 'application/octet-stream')},
        headers={'Authorization': f'Bearer {nft_storage_api_key}'}
    )
    if image_response.status_code == 200:
        image_cid = image_response.json().get('value', {}).get('cid')
        return image_cid
    else:
        raise HTTPException(status_code=image_response.status_code, detail="Failed to upload to NFT Storage")

async def upload_metadata_to_nft_storage(client, metadata, image_cid):
    metadata_bytes = json.dumps(metadata).encode('utf-8')
    metadata_file = BytesIO(metadata_bytes)
    metadata_file.seek(0)
    metadata_response = await client.post(
        'https://api.nft.storage/upload',
        files={'file': ('metadata.json', metadata_file, 'application/octet-stream')},
        headers={'Authorization': f'Bearer {nft_storage_api_key}'}
    )
    if metadata_response.status_code == 200:
        metadata_cid = metadata_response.json().get('value', {}).get('cid')
        return metadata_cid
    else:
        raise HTTPException(status_code=metadata_response.status_code, detail="Failed to upload metadata to NFT Storage")
    

# New endpoint for centralized storage upload
@app.post("/centralized_upload/")
async def centralized_upload(image: str = Form(...), cropped_image: str = Form(...), user_id: str = Form(...), image_id: str = Form(...), location_taken: str = Form(...), user_address: str = Form(...), details: str = Form(...), probability: str = Form(...), ipfs_cid: str = Form(...), image_classification: str = Form(...)):
    try:
        # Upload images to blob storage
        image_blob_url = upload_image_to_blob(blob_storage_name, f"{image_id}.png", BytesIO(image))
        cropped_image_blob_url = upload_image_to_blob(blob_storage_name, f"{image_id}_cropped.png", BytesIO(cropped_image))

        # Create a table entry
        create_table_entry(user_id, image_id, location_taken, user_address, details, probability, image_blob_url, cropped_image_blob_url, ipfs_cid, image_classification)

        return {"status": "success", "message": "Image and metadata successfully uploaded to centralized storage."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
  
# Updated encrypt_image function
def encrypt_image(image_data_bytes, eth_public_key_hex):
    symmetric_key = Fernet.generate_key()
    cipher_suite = Fernet(symmetric_key)
    encrypted_image = cipher_suite.encrypt(image_data_bytes)
    encrypted_symmetric_key = encrypt(eth_public_key_hex, symmetric_key)
    
    return base64.b64encode(encrypted_symmetric_key).decode(), encrypted_image
  
async def upload_to_nft_storage(client, encrypted_image, image_classification):
    image_response = await client.post(
        'https://api.nft.storage/upload',
        files={'file': (image_classification, encrypted_image, 'application/octet-stream')},
        headers={'Authorization': f'Bearer {nft_storage_api_key}'}
    )
    if image_response.status_code == 200:
        image_cid = image_response.json().get('value', {}).get('cid')
        return image_cid
    else:
        raise HTTPException(status_code=image_response.status_code, detail="Failed to upload to NFT Storage")

def get_next_image_id():
    lock.acquire()
    try:
        # Read the current ID
        with open("next_id.txt", "r") as file:
            current_id = int(file.read().strip())

        # Increment and save the next ID
        with open("next_id.txt", "w") as file:
            file.write(str(current_id + 1))

        return str(current_id)
    finally:
        lock.release()
    
# Function to upload an image to blob storage
def upload_image_to_blob(container_name, blob_name, image_data):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    blob_client.upload_blob(image_data)
    return blob_client.url

# Function to create a table entry
def create_table_entry(user_id, image_id, location_taken, user_address, details, probability, image_blob_url, cropped_image_blob_url, ipfs_cid, image_classification):
    entity = TableEntity()
    entity['PartitionKey'] = user_id
    entity['RowKey'] = image_id
    entity['LocationTaken'] = location_taken
    entity['UserAddress'] = user_address
    entity['Details'] = details
    entity['Probability'] = probability
    entity['ImageBlobURL'] = image_blob_url
    entity['CroppedImageBlobURL'] = cropped_image_blob_url
    entity['IPFSCid'] = ipfs_cid
    entity['ImageClassification'] = image_classification
    pst = pytz.timezone('America/Los_Angeles')
    entity['DateAdded'] = datetime.datetime.now(pst).isoformat()
    table_client.create_entity(entity)
    
def url_to_blob(blob_url):
  parsed_url = urlparse(blob_url)
  path_parts = parsed_url.path.lstrip('/').split('/', 1)
  return path_parts[0], path_parts[1]

def hash_password(password: str) -> str:
    # Simple hashing for demonstration. Consider a stronger method for production.
    return hashlib.sha256(password.encode()).hexdigest()
  
async def is_valid_username(user_id: str) -> bool:
    try:
        # Query to check if the user exists
        filter_query = f"PartitionKey eq '{user_id}' and RowKey eq 'userinfo'"
        user_entities = list(users_table_client.query_entities(filter_query))

        return len(user_entities) > 0
    except Exception as e:
        # print(f"Error checking user validity: {e}")
        return False  # or raise an exception based on your error handling strategy

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

    # # Wait for transaction receipt (optional)
    # receipt = web3.eth.wait_for_transaction_receipt(txn_hash)
    # print(txn_hash)

    return {"transaction_hash": txn_hash, "status": "NFT Minted"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000, workers = 16)
