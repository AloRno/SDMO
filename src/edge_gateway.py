import os
import random
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from legacy_device import LegacyDevice
from cloud_service import CloudService

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
        Negotiate a session with the Cloud Service using Diffie-Hellman
        """
        # 1. Generate private key 'a'
        self.dh_private_key = random.SystemRandom().randint(2, self.p - 2)
        
        # 2. Compute public key 'A = g^a mod p'
        self.dh_public_key = pow(self.g, self.dh_private_key, self.p)
      # print(f"[EdgeGateway] Generated DH Public Key: {str(self.dh_public_key)[:20]}...")
        
        # 3. Exchange keys (Simulating the network handshake)
      # print("[EdgeGateway] Initiating DH Handshake with Cloud...")
        cloud_public_key = cloud_service.negotiate_dh(self.dh_public_key)
        
        # 4. Compute shared secret 's = B^a mod p'
        self.shared_secret = pow(cloud_public_key, self.dh_private_key, self.p)
        
        # 5. Derive AES key (SHA-256 hash of the shared secret)
        self.cloud_aes_key = hashlib.sha256(str(self.shared_secret).encode()).digest()
      # print(f"[EdgeGateway] Established AES Key from DH Secret: {self.cloud_aes_key.hex()}")

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
        Decrypt the received data from the legacy buffer (using pre_shared_key)
        """
        if not encryptedData:
            return None
            
        # The IV is the first 16 bytes
        iv = encryptedData[:16]
        payload = encryptedData[16:]
        
        cipher = Cipher(algorithms.AES(self.pre_shared_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        padded_data = decryptor.update(payload) + decryptor.finalize()
        
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        plaintext = data.decode('utf-8')
      # print(f"[EdgeGateway] Decrypted Data: {plaintext}")
        return plaintext

    def reEncryptData(self, plaintext: str) -> bytes:
        """
        reEncrypt with the AES key derived from DH negotiation
        """
        if not plaintext:
            return None
            
        # AES block size is 128 bits (16 bytes)
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode('utf-8')) + padder.finalize()

        # Generate a random 16-byte Initialization Vector (IV)
        iv = os.urandom(16)

        # Create AES cipher using CBC mode and the negotiated DH AES key
        cipher = Cipher(algorithms.AES(self.cloud_aes_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Encrypt the data
        encrypted_payload = encryptor.update(padded_data) + encryptor.finalize()

        # Prepend IV to the payload
        final_encrypted_data = iv + encrypted_payload
        
        # print(f"[EdgeGateway] Re-Encrypted Data (AES): {final_encrypted_data.hex()}")
        return final_encrypted_data

    def forwardData(self, cloud_service: CloudService, reEncryptedData: bytes):
        """
        Forward the re-encrypted data to the cloud service.
        """
        if reEncryptedData:
          # print("[EdgeGateway] Forwarding Data to Cloud...")
            cloud_service.receiveData(reEncryptedData)