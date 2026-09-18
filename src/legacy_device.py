import time
import os
import random
import string
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

class LegacyDevice:
    def __init__(self):
        # Hardcoded 256-bit (32 bytes) pre-shared key for AES
        self.pre_shared_key = b"this_is_a_32_byte_pre_shared_key"
        # Buffer to act as a simple way to "send" encrypted data
        self.data_buffer = []

    def generateData(self, failure_probability: float = 0.1) -> str:
        """
        Generates sensor data in the format: T:<temperature>|TS:<TimeStamp>
        Occasionally simulates a hardware malfunction based on failure_probability. 
        """
        timestamp = str(int(time.time()))
        
        # Probabilistic approach: Check if sensor hardware is malfunctioning
        if random.random() < failure_probability:
            # Simulate a broken sensor returning erratic/impossible temperatures
            temperature = round(random.uniform(-999.0, 999.0), 1)
        else:
            # Generate a realistic temperature (e.g., between 10.0 and 30.0 degrees Celsius)
            temperature = round(random.uniform(10.0, 30.0), 1)
            
        data = f"{temperature}|{timestamp}"
        return data

    def encryptData(self, data: str) -> bytes:
        """
        Encrypts the given string using true AES (AES-CBC) with the pre_shared_key.
        """
        # AES block size is 128 bits (16 bytes)
        # Pad the data to be a multiple of the block size
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data.encode('utf-8')) + padder.finalize()

        # Generate a random 16-byte Initialization Vector (IV)
        iv = os.urandom(16)

        # Create AES cipher using CBC mode
        cipher = Cipher(algorithms.AES(self.pre_shared_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Encrypt the data
        encrypted_payload = encryptor.update(padded_data) + encryptor.finalize()

        # Prepend IV to the payload so it can be decrypted later
        final_encrypted_data = iv + encrypted_payload
        
      # print(f"[LegacyDevice] Encrypted Data (hex): {final_encrypted_data.hex()}")
        return final_encrypted_data

    def sendEncryptedData(self, encrypted_data: bytes):
        """
        Puts the generated and encrypted data into a buffer (a simple list).
        """
        self.data_buffer.append(encrypted_data)
      # print(f"[LegacyDevice] Sent data to buffer. Buffer size: {len(self.data_buffer)}")

"""
Quick test to see if the above class runs

if __name__ == "__main__":
    device = LegacyDevice()
    data = device.generateData()
    encrypted = device.encryptData(data)
    device.sendEncryptedData(encrypted)

"""
