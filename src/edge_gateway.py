import os
import random
import hashlib
import logging
import zlib
import time
import re
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from legacy_device import LegacyDevice
from cloud_service import CloudService
from mlkem.ml_kem import ML_KEM
from mlkem.parameter_set import ML_KEM_768

# Ensure output directory exists for local logging
os.makedirs("Output_Components/gateway", exist_ok=True)

# Configure local logger for the gateway
gateway_logger = logging.getLogger("EdgeGateway")
gateway_logger.setLevel(logging.ERROR)
file_handler = logging.FileHandler("Output_Components/gateway/gateway_error.log")
file_handler.setFormatter(logging.Formatter('[%(asctime)s] ERROR: %(message)s'))
gateway_logger.addHandler(file_handler)

class EdgeGateway:
    def __init__(self):
        # Same pre-shared-key of the legacy_device for legacy communication
        self.pre_shared_key = b"this_is_a_32_byte_pre_shared_key"
        
        # Diffie-Hellman Schoolbook parameters (matching the CloudService)
        self.p = 0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF
        self.g = 2
        
        self.dh_private_key = None
        self.dh_public_key = None
        self.shared_secret = None
        
        # The AES key derived from DH to communicate with the Cloud
        self.cloud_aes_key = None

    def negotiateSession(self, cloud_service: CloudService) -> None:
        """
        Negotiate a session with the Cloud Service using a Hybrid DH + ML-KEM protocol.
        """
        # --- 1. DH Part ---
        self.dh_private_key = random.SystemRandom().randint(2, self.p - 2)
        self.dh_public_key = pow(self.g, self.dh_private_key, self.p)
        
        # --- 2. ML-KEM Part ---
        ml_kem = ML_KEM(parameters=ML_KEM_768)
        self.mlkem_ek, self.mlkem_dk = ml_kem.key_gen()
        
        # --- 3. Handshake ---
        cloud_dh_pub, mlkem_ciphertext = cloud_service.negotiate_session(self.dh_public_key, self.mlkem_ek)
        
        # --- 4. Derive Shared Secrets ---
        dh_shared_secret = pow(cloud_dh_pub, self.dh_private_key, self.p)
        mlkem_shared_secret = ml_kem.decaps(self.mlkem_dk, mlkem_ciphertext)
        
        # --- 5. Derive AES key (Mix DH + ML-KEM) ---
        self.shared_secret = str(dh_shared_secret).encode() + mlkem_shared_secret
        self.cloud_aes_key = hashlib.sha256(self.shared_secret).digest()

    def receiveData(self, legacy_device: LegacyDevice) -> bytes:
        """
        Must pop encryptedData from the legacy_device buffer
        """
        if not legacy_device.data_buffer:
          # print("[EdgeGateway] No data in legacy device buffer.")
            return None
        
        # Pop the oldest message from the buffer (FIFO)
        encryptedData = legacy_device.data_buffer.pop(0)
      # print(f"[EdgeGateway] Received encrypted data from buffer. Buffer remaining: {len(legacy_device.data_buffer)}")
        return encryptedData

    def decryptData(self, encryptedData: bytes) -> str:
        """
        Decrypt the received data. If it was corrupted in transit, catch the error.
        If decryption succeeds, perform semantic validation.
        """
        if not encryptedData:
            return None
            
        iv = encryptedData[:16]
        payload = encryptedData[16:]
        
        cipher = Cipher(algorithms.AES(self.pre_shared_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        # 1. Attempt Decryption (Catches Transit Corruption)
        try:
            padded_data = decryptor.update(payload) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()
            plaintext = data.decode('utf-8')
        except ValueError as e:
            gateway_logger.error(f"Dropped payload. Reason: Transit Corruption (Padding Error). Details: {e}")
            return None

        # 2. Semantic Validation (Catches Hardware Malfunction & mitigates Transit Corruption)
        try:
            parts = plaintext.split('|')
            if len(parts) != 2:
                raise ValueError("Invalid format string")
                
            temp_str = parts[0]
            timestamp_str = parts[1]
            
            # Use strict regex to ensure format wasn't subtly corrupted (e.g., non-digits slipping in)
            if not re.match(r'^-?\d+\.\d+$', temp_str):
                raise ValueError("Temperature format strictly violated")
            if not re.match(r'^\d{10}$', timestamp_str):
                raise ValueError("Timestamp format strictly violated")
            
            temperature = float(temp_str)
            timestamp = int(timestamp_str)
            
            # Check for physically realistic bounds
            if temperature < -30.0 or temperature > 50.0:
                 gateway_logger.error(f"Dropped payload. Reason: Hardware Malfunction. Value: {temperature}")
                 return None
            
            # Check for temporal realism (must not be from the future or too far in the past)
            current_time = int(time.time())
            if timestamp > current_time + 5 or timestamp < current_time - 15:
                gateway_logger.error(f"Dropped payload. Reason: Invalid Timestamp (likely corruption). Value: {timestamp}")
                return None
                 
        except Exception as e:
            gateway_logger.error(f"Dropped payload. Reason: Format Parsing Error. Details: {e}")
            return None
            
        # Data is perfectly healthy
        return plaintext

    def reEncryptData(self, plaintext: str) -> bytes:
        """
        Encrypts the healthy plaintext using AES-GCM for the Cloud.
        """
        if not plaintext:
            return None
            
        # AES-GCM typically uses a 12-byte (96-bit) IV
        iv = os.urandom(12)
        cipher = Cipher(algorithms.AES(self.cloud_aes_key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        encrypted_payload = encryptor.update(plaintext.encode('utf-8')) + encryptor.finalize()
        tag = encryptor.tag
        
        # Package: IV (12 bytes) + Tag (16 bytes) + Ciphertext
        return iv + tag + encrypted_payload

    def forwardData(self, cloud_service: CloudService, reEncryptedData: bytes, corruption_probability: float = 0.0):
        """
        Forward the re-encrypted data to the cloud service.
        Occasionally simulates transit corruption by altering a byte.
        """
        if reEncryptedData:
            if random.random() < corruption_probability:
                # Simulate transit corruption by flipping a bit in a random byte
                mutable_bytes = bytearray(reEncryptedData)
                corrupt_index = random.randint(0, len(mutable_bytes) - 1)
                mutable_bytes[corrupt_index] ^= 1
                reEncryptedData = bytes(mutable_bytes)
                
          # print("[EdgeGateway] Forwarding Data to Cloud...")
            cloud_service.receiveData(reEncryptedData)