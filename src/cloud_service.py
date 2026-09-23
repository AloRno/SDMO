import os
import hashlib
import random
import zlib
import time
import sqlite3
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.exceptions import InvalidTag
from mlkem.ml_kem import ML_KEM
from mlkem.parameter_set import ML_KEM_768

class CloudService:
    def __init__(self, db_path: str = "Output_Components/cloud/cloud_messages.db"):
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
        
        # SQLite Database storage
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database table for storing messages."""
        if self.db_path != ":memory:" and os.path.dirname(self.db_path):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        temperature REAL,
                        timestamp INTEGER,
                        raw_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
        finally:
            conn.close()

    def save_message(self, temperature: float, timestamp: int, raw_message: str) -> bool:
        """
        Saves a validated message to the SQLite database.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            try:
                with conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO messages (temperature, timestamp, raw_message) VALUES (?, ?, ?)",
                        (temperature, timestamp, raw_message)
                    )
            finally:
                conn.close()
            return True
        except Exception as e:
            print(f"[CloudService] ❌ Failed to save message to SQLite database: {e}")
            return False

    def negotiate_session(self, gateway_dh_pub: int, gateway_mlkem_ek: bytes) -> tuple[int, bytes]:
        """
        Completes the Hybrid DH + ML-KEM handshake.
        """
        # --- 1. DH Part ---
        self.dh_private_key = random.SystemRandom().randint(2, self.p - 2)
        self.dh_public_key = pow(self.g, self.dh_private_key, self.p)
        dh_shared_secret = pow(gateway_dh_pub, self.dh_private_key, self.p)
        
        # --- 2. ML-KEM Part ---
        ml_kem = ML_KEM(parameters=ML_KEM_768)
        mlkem_shared_secret, self.mlkem_ciphertext = ml_kem.encaps(gateway_mlkem_ek)
        
        # --- 3. Hybrid Master Secret ---
        # Best practice: Mix both secrets to derive the AES key
        self.shared_secret = str(dh_shared_secret).encode() + mlkem_shared_secret
        self.aes_key = hashlib.sha256(self.shared_secret).digest()
        
        return self.dh_public_key, self.mlkem_ciphertext

    def receiveData(self, encrypted_data: bytes):
        """
        Receives encrypted data from the Gateway (Simulates TCP reception).
        """
        self.incoming_buffer.append(encrypted_data)
      # print(f"[CloudService] Received data in buffer. Buffer size: {len(self.incoming_buffer)}")

    def processData(self):
        """
        Pops the data from the buffer and decrypts it using the AES-GCM key derived from DH.
        AES-GCM automatically guarantees transit integrity via its Authentication Tag.
        """
        if not self.incoming_buffer:
            return None

        encrypted_data = self.incoming_buffer.pop(0)
        
        # Package: IV (12 bytes) + Tag (16 bytes) + Ciphertext
        if len(encrypted_data) < 28:
            print("[CloudService] [ERROR] Transit Corruption Detected! Payload too short.")
            return None
            
        iv = encrypted_data[:12]
        tag = encrypted_data[12:28]
        payload = encrypted_data[28:]
        
        cipher = Cipher(algorithms.AES(self.aes_key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        
        try:
            # decryptor.update() and finalize() will automatically verify the tag
            data = decryptor.update(payload) + decryptor.finalize()
            expected_plaintext = data.decode('utf-8')
        except InvalidTag as e:
            print(f"[CloudService] [ERROR] Transit Corruption Detected! AES-GCM Tag mismatch: {e}")
            return None
        except ValueError as e:
            print(f"[CloudService] [ERROR] Transit Corruption Detected! Decryption failed: {e}")
            return None

        # Expected Format from Gateway: <temperature>|<timestamp>
        try:
            parts = expected_plaintext.split('|')
            if len(parts) != 2:
                print(f"[CloudService] [ERROR] Transit Corruption Detected! Missing delimiters.")
                return None
                
            # If everything is perfect, process the data, save to DB, and update the heartbeat
            # print(f"[CloudService] [SUCCESS] Successfully Decrypted and Validated Data: {expected_plaintext}")
            
            temperature = float(parts[0])
            timestamp = int(parts[1])
            
            self.last_healthy_reading_time = time.time()
            #Saving the entry to the SQLite DB
            self.save_message(temperature, timestamp, expected_plaintext)
            return expected_plaintext
            
        except Exception as e:
            print(f"[CloudService] [ERROR] Unexpected validation error: {e}")
            return None

    def check_sensor_health(self, timeout_seconds: int = 30):
        """
        Deadman's Switch method. Checks if the Cloud Service has received healthy 
        data within the expected timeout window.
        """
        time_since_last = time.time() - self.last_healthy_reading_time
        if time_since_last > timeout_seconds:
            print(f"\n[CloudService] [CRITICAL ALARM]: No healthy data received from sensor for {int(time_since_last)} seconds!")
            print("[CloudService] Sensor may be malfunctioning or Edge Gateway dropped corrupted payloads. Please check Gateway logs.")
            return False
        return True
