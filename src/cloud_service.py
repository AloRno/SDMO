import os
import hashlib
import random
import zlib
import time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding

class CloudService:
    def __init__(self):
        # Diffie-Hellman Schoolbook parameters (Small/demo safe prime for illustration)
        self.p = 0xFFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9ED529077096966D670C354E4ABC9804F1746C08CA18217C32905E462E36CE3BE39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9DE2BCBF6955817183995497CEA956AE515D2261898FA051015728E5A8AACAA68FFFFFFFFFFFFFFFF
        self.g = 2
        
        self.dh_private_key = None
        self.dh_public_key = None
        self.shared_secret = None
        self.aes_key = None
        
        self.incoming_buffer = []
        
        # Deadman's switch / Heartbeat property
        self.last_healthy_reading_time = time.time()

    def negotiate_dh(self, gateway_public_key: int) -> int:
        """
        Completes the Schoolbook DH handshake.
        Generates own keys, derives shared secret, and returns own public key.
        """
        # 1. Generate private key 'b'
        self.dh_private_key = random.SystemRandom().randint(2, self.p - 2)
        
        # 2. Compute public key 'B = g^b mod p'
        self.dh_public_key = pow(self.g, self.dh_private_key, self.p)
      # print(f"[CloudService] Generated DH Public Key: {str(self.dh_public_key)[:20]}...")
        
        # 3. Compute shared secret 's = A^b mod p'
        self.shared_secret = pow(gateway_public_key, self.dh_private_key, self.p)
        
        # 4. Derive AES key (SHA-256 hash of the shared secret provides exactly 32 bytes)
        self.aes_key = hashlib.sha256(str(self.shared_secret).encode()).digest()
      # print(f"[CloudService] Established AES Key from DH Secret: {self.aes_key.hex()}")
        
        return self.dh_public_key

    def receiveData(self, encrypted_data: bytes):
        """
        Receives encrypted data from the Gateway (Simulates TCP reception).
        """
        self.incoming_buffer.append(encrypted_data)
      # print(f"[CloudService] Received data in buffer. Buffer size: {len(self.incoming_buffer)}")

    def processData(self):
        """
        Pops the data from the buffer and decrypts it using the AES key derived from DH.
        Validates the CRC32 checksum to guarantee transit integrity.
        """
        if not self.incoming_buffer:
            return None

        encrypted_data = self.incoming_buffer.pop(0)
        
        iv = encrypted_data[:16]
        payload = encrypted_data[16:]
        
        cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        
        try:
            padded_data = decryptor.update(payload) + decryptor.finalize()
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()
            decrypted_str = data.decode('utf-8')
        except ValueError as e:
            print(f"[CloudService] ❌ Transit Corruption Detected! Decryption failed: {e}")
            return None

        # Expected Format from Gateway: <temperature>|<timestamp>|<crc32_hex>
        try:
            parts = decrypted_str.split('|')
            if len(parts) != 3:
                print(f"[CloudService] ❌ Transit Corruption Detected! Missing delimiters.")
                return None
                
            temp_str, ts_str, received_crc_hex = parts[0], parts[1], parts[2]
            
            # Reconstruct the original plaintext that the CRC was based on
            expected_plaintext = f"{temp_str}|{ts_str}"
            
            # Verify CRC32 Checksum
            calculated_crc_val = zlib.crc32(expected_plaintext.encode('utf-8')) & 0xFFFFFFFF
            calculated_crc_hex = f"{calculated_crc_val:08x}"
            
            if calculated_crc_hex != received_crc_hex:
                print(f"[CloudService] ❌ Transit Corruption Detected! Checksum mismatch.")
                return None
                
            # If everything is perfect, process the data and update the heartbeat
            # print(f"[CloudService] ✅ Successfully Decrypted and Validated Data: {expected_plaintext}")
            self.last_healthy_reading_time = time.time()
            return expected_plaintext
            
        except Exception as e:
            print(f"[CloudService] ❌ Unexpected validation error: {e}")
            return None

    def check_sensor_health(self, timeout_seconds: int = 30):
        """
        Deadman's Switch method. Checks if the Cloud Service has received healthy 
        data within the expected timeout window.
        """
        time_since_last = time.time() - self.last_healthy_reading_time
        if time_since_last > timeout_seconds:
            print(f"\n[CloudService] 🚨 CRITICAL ALARM 🚨: No healthy data received from sensor for {int(time_since_last)} seconds!")
            print("[CloudService] Sensor may be malfunctioning or Edge Gateway dropped corrupted payloads. Please check Gateway logs.")
            return False
        return True
