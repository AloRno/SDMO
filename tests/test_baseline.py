import pytest
import time
import sys
import os

# Add src to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from legacy_device import LegacyDevice
from edge_gateway import EdgeGateway
from cloud_service import CloudService

def test_cryptography_unit():
    """
    Verify that data encrypted by the Legacy Sensor using the hard-coded AES-CBC 
    key can be successfully and deterministically decrypted by the Edge Gateway.
    """
    device = LegacyDevice()
    gateway = EdgeGateway()
    
    # 1. Device generates and encrypts data
    data = device.generateData(0.0)
    encrypted_data = device.encryptData(data)
    
    # 2. Simulate sending over network by putting in buffer
    device.sendEncryptedData(encrypted_data, 0.0)
    
    # 3. Gateway retrieves data
    received_data = gateway.receiveData(device)
    
    # 4. Gateway decrypts data
    decrypted_data = gateway.decryptData(received_data)
    
    assert data == decrypted_data, "Gateway failed to decrypt the data correctly from the sensor."

def test_handshake_math_correctness():
    """
    Verify the mathematical correctness of the Edge Gateway and Cloud Service handshake.
    Asserts that both parties independently derive the exact same shared secret 
    and AES session key without transmitting it over the network.
    """
    cloud = CloudService()
    gateway = EdgeGateway()
    
    # Perform handshake
    gateway.negotiateSession(cloud)
    
    # Verify shared secrets and derived AES keys match
    assert gateway.shared_secret is not None
    assert cloud.shared_secret is not None
    assert gateway.shared_secret == cloud.shared_secret, "Shared secrets do not match!"
    assert gateway.cloud_aes_key == cloud.aes_key, "Derived AES keys do not match!"

def test_end_to_end_integration():
    """
    End-To-End Integration Test simulating the entire operational flow.
    Asserts that a randomly generated string on the Legacy Sensor can traverse 
    the gateway and be successfully retrieved in plaintext by the Cloud Service.
    Also extracts performance metrics.
    """
    device = LegacyDevice()
    gateway = EdgeGateway()
    cloud = CloudService()
    
    # === Handshake Latency Measurement ===
    start_time = time.perf_counter()
    gateway.negotiateSession(cloud)
    handshake_latency_ms = (time.perf_counter() - start_time) * 1000
    
    # === Public Key Size Measurement ===
    pk_size_bytes = (gateway.dh_public_key.bit_length() + 7) // 8
    cloud_pk_size_bytes = (cloud.dh_public_key.bit_length() + 7) // 8
    
    # === End-to-End Latency Measurement ===
    start_e2e = time.perf_counter()
    
    # Legacy Sensor operations
    data = device.generateData(0.0)
    encrypted_data = device.encryptData(data)
    ciphertext_size_bytes = len(encrypted_data)
    
    device.sendEncryptedData(encrypted_data, 0.0)
    
    # Gateway operations
    received_at_gateway = gateway.receiveData(device)
    decrypted_at_gateway = gateway.decryptData(received_at_gateway)
    reencrypted_data = gateway.reEncryptData(decrypted_at_gateway)
    
    reencrypted_ciphertext_size_bytes = len(reencrypted_data)
    
    gateway.forwardData(cloud, reencrypted_data)
    
    # Cloud operations
    final_data = cloud.processData()
    end_e2e = time.perf_counter()
    
    e2e_latency_ms = (end_e2e - start_e2e) * 1000
    
    assert data == final_data, "End-to-End integration failed to retrieve the original data."
    
    # Write metrics to a file or stdout
    metrics = {
        "Handshake Latency (ms)": handshake_latency_ms,
        "End-to-End Latency (ms)": e2e_latency_ms,
        "Gateway Public Key Size (Bytes)": pk_size_bytes,
        "Cloud Public Key Size (Bytes)": cloud_pk_size_bytes,
        "Ciphertext Size (Bytes)": ciphertext_size_bytes,
        "Re-Encrypted Ciphertext Size (Bytes)": reencrypted_ciphertext_size_bytes
    }
    
    # Format as a fancy human-readable table
    metrics_output = "\n+----------------------------------------+-------------------+\n"
    metrics_output += f"| {'Metric':<38} | {'Value':<17} |\n"
    metrics_output += "+========================================+===================+\n"
    for k, v in metrics.items():
        v_str = f"{v:.4f}" if isinstance(v, float) else str(v)
        metrics_output += f"| {k:<38} | {v_str:<17} |\n"
    metrics_output += "+----------------------------------------+-------------------+\n"
        
    print(metrics_output)
    
    # Save to a file for extraction if needed
    with open("tests/baseline_metrics.txt", "w") as f:
        f.write(metrics_output)

def test_edge_cases_and_errors():
    """
    Test edge cases and error handling for 100% coverage on core files.
    """
    device = LegacyDevice()
    gateway = EdgeGateway()
    cloud = CloudService()
    
    # Gateway empty buffer handling
    assert gateway.receiveData(device) is None
    
    # Gateway none inputs handling
    assert gateway.decryptData(None) is None
    assert gateway.reEncryptData(None) is None
    
    # Cloud service empty buffer handling
    assert cloud.processData() is None
    
    # Cloud service invalid padding / corrupted data
    gateway.negotiateSession(cloud)
    
    # Put some garbage data to simulate corrupted encrypted data
    import os
    garbage_data = os.urandom(32)
    cloud.receiveData(garbage_data)
    assert cloud.processData() is None

def test_cloud_database_persistence():
    """
    Verify that valid telemetry messages processed by the CloudService
    are successfully stored in the SQLite database with correct schema and types.
    """
    import sqlite3
    test_db = "tests/test_messages.db"
    if os.path.exists(test_db):
        os.remove(test_db)
        
    try:
        cloud = CloudService(db_path=test_db)
        
        # 1. Direct save_message testing
        assert cloud.save_message("23.5|1726759200") is True
        assert cloud.save_message("invalid_message") is False
        assert cloud.save_message(None) is False
        
        # 2. Verify record in SQLite table
        conn = sqlite3.connect(test_db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, temperature, timestamp, raw_message FROM messages")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][1] == 23.5
            assert rows[0][2] == 1726759200
            assert rows[0][3] == "23.5|1726759200"
        finally:
            conn.close()
            
        # 3. Verify processData() end-to-end persists healthy data
        gateway = EdgeGateway()
        gateway.negotiateSession(cloud)
        
        payload = "18.2|1726759210"
        encrypted = gateway.reEncryptData(payload)
        cloud.receiveData(encrypted)
        result = cloud.processData()
        assert result == payload
        
        conn = sqlite3.connect(test_db)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT temperature, timestamp, raw_message FROM messages ORDER BY id DESC LIMIT 1")
            last_row = cursor.fetchone()
            assert last_row == (18.2, 1726759210, "18.2|1726759210")
        finally:
            conn.close()
            
    finally:
        if os.path.exists(test_db):
            os.remove(test_db)

