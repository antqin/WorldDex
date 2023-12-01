from hexbytes import HexBytes
from coincurve import PublicKey as CCPublicKey
from eth_account._utils.signing import to_standard_v
from eth_account._utils.legacy_transactions import serializable_unsigned_transaction_from_dict
from eth_keys.datatypes import Signature
from eth_rlp import HashableRLP
from web3 import Web3
import requests
import base64
from base64 import b64encode
from ecies import encrypt, decrypt
from ecies.utils import generate_eth_key
from cryptography.fernet import Fernet
import os

def encrypt_image(image_data_bytes, eth_public_key_hex, output_encrypted_image_path='encrypted_image.enc'):
    """
    Encrypts an image using a symmetric key and then encrypts the key using an Ethereum public key.

    Args:
        image_data_bytes (bytes): Image data in bytes.
        eth_public_key_hex (str): Ethereum public key in hex.
        output_encrypted_image_path (str): Path to save the encrypted image.

    Returns:
        str: Hexadecimal representation of the encrypted symmetric key.
    """
    # Generate a symmetric key for Fernet encryption
    symmetric_key = Fernet.generate_key()
    cipher_suite = Fernet(symmetric_key)

    # Encrypt the image
    encrypted_image = cipher_suite.encrypt(image_data_bytes)

    # Save the encrypted image to a file
    with open(output_encrypted_image_path, 'wb') as encrypted_image_file:
        encrypted_image_file.write(encrypted_image)

    # Encrypt the symmetric key using the Ethereum public key
    encrypted_symmetric_key = encrypt(eth_public_key_hex, symmetric_key)

    return encrypted_symmetric_key.hex()


def get_most_recent_txid(eth_address, api_key, chain):
    """Fetches the most recent transaction ID for a given Ethereum address.

    Args:
        eth_address (str): The Ethereum address.
        api_key (str): The API key for Etherscan.

    Returns:
        str: The transaction ID of the most recent transaction.
    """
    if chain == "SEP":
      etherscan_api_url = "https://api-sepolia.etherscan.io/api"
    else:
      etherscan_api_url = "https://api.etherscan.io/api"
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': eth_address,
        'startblock': 0,
        'endblock': 99999999,
        'page': 1,
        'offset': 1,
        'sort': 'desc',
        'apikey': api_key
    }

    response = requests.get(etherscan_api_url, params=params)
    data = response.json()

    if data['status'] == '1' and data['message'] == 'OK' and len(data['result']) > 0:
        return data['result'][0]['hash']
    else:
        raise Exception("No transactions found for this address or error in API call.")

def pub_key_from_tx_eth(txid, chain, web3provider):
    w3test = Web3(Web3.HTTPProvider(web3provider))
    transaction = w3test.eth.get_transaction(txid)
    chain_id = "0xAA36A7" if chain == "SEP" else "0x01"  # Use integer value for chain ID

    # Determine if it's an EIP-1559 transaction
    if 'maxFeePerGas' in transaction and 'maxPriorityFeePerGas' in transaction:
        tx_dict = {
            'nonce': transaction['nonce'],
            'maxPriorityFeePerGas': transaction['maxPriorityFeePerGas'],
            'maxFeePerGas': transaction['maxFeePerGas'],
            'gas': transaction['gas'],
            'to': transaction['to'],
            'value': transaction['value'],
            'data': transaction.get('input', ''),
            'chainId': chain_id,
            'type': transaction['type']  # Ensure to include the type field for EIP-1559 transactions
        }
    else:
        # Handle as a legacy transaction
        tx_dict = {
            'nonce': transaction['nonce'],
            'gasPrice': transaction['gasPrice'],
            'gas': transaction['gas'],
            'to': transaction['to'],
            'value': transaction['value'],
            'data': transaction.get('input', ''),
            'chainId': chain_id
        }

    # Create a serializable unsigned transaction
    serialized_tx = serializable_unsigned_transaction_from_dict(tx_dict)

    # Recover the public key
    vrs = (to_standard_v(transaction['v']),
           int.from_bytes(transaction['r'], "big"),
           int.from_bytes(transaction['s'], "big"))
    signature = Signature(vrs=vrs)
    rec_pub = signature.recover_public_key_from_msg_hash(serialized_tx.hash())
    

    # Verify the recovered address
    if rec_pub.to_checksum_address() != transaction['from']:
        raise ValueError("Unable to obtain public key from transaction: " + txid)

    return rec_pub, rec_pub.to_checksum_address()
  
def eth_address_to_pub_key(eth_address, api_key, chain, web3provider):
    """
    Converts a Sepolia Ethereum address into a public key by finding the most recent transaction ID
    and then using it to obtain the public key.

    Args:
        eth_address (str): The Ethereum address.
        api_key (str): The API key for Etherscan.
        chain (str): The blockchain network (e.g., 'SEP' for Sepolia).

    Returns:
        tuple: A tuple containing the public key and the corresponding Ethereum address.
    """
    try:
        # Get the most recent transaction ID for the given Ethereum address
        txid = get_most_recent_txid(eth_address, api_key, chain)

        # Obtain the public key from the Ethereum transaction
        public_key, derived_address = pub_key_from_tx_eth(txid, chain, web3provider)

        return public_key, derived_address
    except Exception as e:
        raise Exception(f"Error in processing: {e}")
      
def encrypt_image_with_eth_address(eth_address, api_key, chain, image_data_bytes, web3provider, output_encrypted_image_path='encrypted_image.enc'):
    """
    Encrypts an image using a public key derived from an Ethereum address.

    Args:
        eth_address (str): The Ethereum address.
        api_key (str): The API key for Etherscan.
        chain (str): The blockchain network (e.g., 'SEP' for Sepolia).
        image_path (str): Path to the image to be encrypted.
        output_encrypted_image_path (str): Path to save the encrypted image.

    Returns:
        str: Hexadecimal representation of the encrypted symmetric key.
    """
    try:
        # Get the public key from the Ethereum address
        public_key, _ = eth_address_to_pub_key(eth_address, api_key, chain, web3provider)
        public_key_hex = public_key.to_hex()

        # Encrypt the image using the retrieved public key
        encrypted_symmetric_key_hex = encrypt_image(image_data_bytes, public_key_hex, output_encrypted_image_path)

        print("Encrypted symmetric key:", encrypted_symmetric_key_hex)
        return encrypted_symmetric_key_hex
    except Exception as e:
        raise Exception(f"Error in processing: {e}")
      
def decrypt_image(eth_private_key_hex, encrypted_symmetric_key_b64, encrypted_image_path, output_decrypted_image_path='decrypted_image.png'):
    # Base64 Decode the encrypted symmetric key
    encrypted_symmetric_key = base64.b64decode(encrypted_symmetric_key_b64)

    # Decrypt the symmetric key with the Ethereum private key
    decrypted_symmetric_key = decrypt(eth_private_key_hex, encrypted_symmetric_key)

    # Read the encrypted image
    with open(encrypted_image_path, 'rb') as encrypted_image_file:
        encrypted_image_data = encrypted_image_file.read()

    # Decrypt the image with the symmetric key
    cipher_suite = Fernet(decrypted_symmetric_key)
    decrypted_image_data = cipher_suite.decrypt(encrypted_image_data)

    # Save the decrypted image back to a file
    with open(output_decrypted_image_path, 'wb') as decrypted_image_file:
        decrypted_image_file.write(decrypted_image_data)