from fastapi import FastAPI, File, UploadFile, HTTPException, Form, status
from typing import Optional
from cryptography.fernet import Fernet
import base64
import json
import os
from httpx import AsyncClient
from parse_public import eth_address_to_pub_key
from ecies import encrypt, decrypt
from io import BytesIO
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.data.tables import TableServiceClient, TableEntity
import threading
from typing import List
from urllib.parse import urlparse
import hashlib
from dotenv import load_dotenv
import datetime

lock = threading.Lock()

load_dotenv()

app = FastAPI()

ITEMS_PER_PAGE = 1000  # Define how many items you want per page

# Set your NFT.storage API key in environment variable
nft_storage_api_key = os.environ.get('NFT_STORAGE_API_KEY')
# Set Etherscan API Key
etherscan_api_key = os.environ.get('ETHERSCAN_API_KEY')
# Set Web3 Provider
web3provider = os.environ.get('WEB3_PROVIDER')

# Azure storage account details
account_name = "worlddexstorage"
account_key = os.environ.get("BLOB_ACCOUNT_KEY")
connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"

# Initialize Azure Blob Service Client
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Initialize Azure Table Service Client
table_service_client = TableServiceClient.from_connection_string(connection_string)
table_client = table_service_client.get_table_client(table_name="dextablestorage")
users_table_client = table_service_client.get_table_client(table_name="users")

@app.get("/userData")
async def user_data(username: str):
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    try:
        # Check if user exists
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
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
      
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


@app.get("/getSpecificImage")
async def get_image(image_id: str):
    # try:
        # Query the table to find the entity with the given row_key
        filter_query = f"RowKey eq '{image_id}'"
        entities = list(table_client.query_entities(filter_query))

        if not entities:
            raise HTTPException(status_code=404, detail="Image not found")

        # Assuming the first matching entity contains the image URL
        blob_url = entities[0].get('ImageBlobURL')

        # Create a blob client using the blob's URL
        container_name, blob_name = url_to_blob(blob_url)  # Assuming you have this function defined
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # Download the blob contents
        download_stream = blob_client.download_blob()
        image_bytes = download_stream.readall()

        # Convert bytes to base64 encoded string
        base64_encoded = base64.b64encode(image_bytes).decode('utf-8')

        return {"image_data": base64_encoded}
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Error retrieving image: {str(e)}")


@app.get("/getUserImages")
async def get_user_images(user_id: str):
    try:
        # Query to retrieve images belonging to user_id
        filter_query = f"PartitionKey eq '{user_id}'"
        queried_entities = table_client.query_entities(filter_query)

        # Fetching Images
        result = []
        for entity in queried_entities:
            image_info = {
                "image_id": entity['RowKey'],
                "user_id": entity['PartitionKey'],
                "ipfs_cid": entity.get('IPFSCid', ''),
                "date_added": entity.get('DateAdded', ''),
                "location_taken": entity.get('LocationTaken', ''),
                "cropped_image": "",
                "image": "",  # Placeholder for base64 encoded image
                "details": entity.get('Details', ''),
                "probability": entity.get('Probability', ''),
                "image_classification": entity.get('ImageClassification', '')
            }

            # Fetch and encode the image from the Blob URL
            cropped_blob_url = entity.get('CroppedImageBlobURL')
            container_name, blob_name = url_to_blob(cropped_blob_url)  # Assuming you have this function defined
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            download_stream = blob_client.download_blob()
            image_bytes = download_stream.readall()
            image_info['cropped_image'] = base64.b64encode(image_bytes).decode('utf-8')
            
            normal_blob_url = entity.get('ImageBlobURL')
            container_name, blob_name = url_to_blob(normal_blob_url)  # Assuming you have this function defined
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            download_stream = blob_client.download_blob()
            image_bytes = download_stream.readall()
            image_info['image'] = base64.b64encode(image_bytes).decode('utf-8')

            result.append(image_info)

        return {"images": result}

    except Exception as e:
        print(f"Error retrieving data: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return {"images": result}


@app.get("/excludeUserImages")
async def exclude_user_images(user_id: str, page: int = 1):
    try:
      # Calculate the range of items for the requested page
      start_index = (page - 1) * ITEMS_PER_PAGE
      end_index = start_index + ITEMS_PER_PAGE

      # Create a TableClient
      # Query to retrieve images not belonging to user_id
      filter_query = f"PartitionKey ne '{user_id}'"
      queried_entities = table_client.query_entities(filter_query)

      # Implementing Pagination and Image Fetching
      result = []
      for i, entity in enumerate(queried_entities):
          if start_index <= i < end_index:
              # Fetch and encode the image
              image_info = {
                "image_id": entity['RowKey'],
                "user_id": entity['PartitionKey'],
                "location_taken": entity.get('LocationTaken', ''),
                "user_address": entity.get('UserAddress', ''),
                "details": entity.get('Details', ''),
                "probability": entity.get('Probability', ''),
                "ipfs_cid": entity.get('IPFSCid', ''),
                "image_classification": entity.get('ImageClassification', ''),
                "date_added": entity.get('DateAdded', ''),
                "image": "",  # Placeholder for base64 encoded image
              }
              
              cropped_blob_url = entity.get('CroppedImageBlobURL')
              container_name, blob_name = url_to_blob(cropped_blob_url)  # Assuming you have this function defined
              blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
              download_stream = blob_client.download_blob()
              image_bytes = download_stream.readall()
              image_info['cropped_image'] = base64.b64encode(image_bytes).decode('utf-8')
              
              normal_blob_url = entity.get('ImageBlobURL')
              container_name, blob_name = url_to_blob(normal_blob_url)  # Assuming you have this function defined
              blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
              download_stream = blob_client.download_blob()
              image_bytes = download_stream.readall()
              image_info['image'] = base64.b64encode(image_bytes).decode('utf-8')

              result.append(image_info)
          elif i >= end_index:
              break

      return {"images": result}

    except Exception as e:
        print(f"Error retrieving data: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

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
    if not await is_valid_username(user_id):
      raise HTTPException(status_code=400, detail="Invalid user ID")
    
    decentralize_storage_bool = decentralize_storage.lower() in ["true", "1", "yes"]
        
    # Convert base64 images back to bytes for decentralized upload
    cropped_image_content = base64.b64decode(cropped_image_base64)
    decentralized_upload_successful = False
    metadata_cid = None
    metadata_url = ""
    
    if decentralize_storage_bool:
      print(f'eth address: {eth_address}\n')
      public_key, _ = eth_address_to_pub_key(eth_address, etherscan_api_key, "SEP", web3provider)
      public_key_hex = public_key.to_hex()
      encrypted_key, encrypted_image = encrypt_image(cropped_image_content, public_key_hex)

      # NFT Storage Upload
      async with AsyncClient() as client:
        image_cid = await upload_to_nft_storage(client, encrypted_image, image_classification)

        # Prepare metadata
        metadata = {
            "name": "Encrypted Image",
            "description": "An encrypted image with its encrypted symmetric key",
            "image": f"ipfs://{image_cid}",
            "properties": {"encrypted_key": encrypted_key}
        }

        metadata_cid = await upload_metadata_to_nft_storage(client, metadata, image_cid)
        metadata_url = f"https://{metadata_cid}.ipfs.nftstorage.link"
        decentralized_upload_successful = True


    # Centralized upload logic
    image_id = get_next_image_id()  # Get a unique image identifier

    # Call to centralized upload function
    centralized_upload_response = await centralized_upload(
        image_base64=image_base64,
        cropped_image_base64=cropped_image_base64,
        user_id=user_id,
        image_id=image_id,
        location_taken=location_taken,
        user_address=eth_address,
        details=details,
        probability=probability,
        image_classification=image_classification,
        ipfs_cid=metadata_cid or "N/A"
    )
        
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
async def centralized_upload(image_base64: str = Form(...), cropped_image_base64: str = Form(...), user_id: str = Form(...), image_id: str = Form(...), location_taken: str = Form(...), user_address: str = Form(...), details: str = Form(...), probability: str = Form(...), ipfs_cid: str = Form(...), image_classification: str = Form(...)):
    try:
        # Convert base64 image to bytes
        image_data = base64.b64decode(image_base64)
        cropped_image_data = base64.b64decode(cropped_image_base64)

        # Upload images to blob storage
        image_blob_url = upload_image_to_blob("dex-images", f"{image_id}.png", BytesIO(image_data))
        cropped_image_blob_url = upload_image_to_blob("dex-images", f"{image_id}_cropped.png", BytesIO(cropped_image_data))

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
    entity['DateAdded'] = datetime.datetime.now().isoformat()
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
        print(f"Error checking user validity: {e}")
        return False  # or raise an exception based on your error handling strategy



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)