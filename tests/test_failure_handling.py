import pytest
import sys
import os

# Add src to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from legacy_device import LegacyDevice
from edge_gateway import EdgeGateway
from cloud_service import CloudService

def test_hardware_malfunction_handling():
    """
    Simulates a hardware malfunction on the Legacy Device (e.g., an out-of-bounds temperature).
    Asserts that the Edge Gateway detects the semantic error and drops the payload,
    preventing it from reaching the Cloud Service.
    """
    device = LegacyDevice()
    gateway = EdgeGateway()
    cloud = CloudService()
    
    # Force the device to generate a malformed reading (100% probability)
    data = device.generateData(failure_probability=1.0)
    encrypted_data = device.encryptData(data)
    
    # Send it successfully over the network (0% transit corruption)
    device.sendEncryptedData(encrypted_data, corruption_probability=0.0)
    
    # Gateway retrieves and attempts to decrypt/validate
    received_at_gateway = gateway.receiveData(device)
    
    # Validation should fail, resulting in None
    decrypted_at_gateway = gateway.decryptData(received_at_gateway)
    assert decrypted_at_gateway is None, "Gateway failed to drop the semantically invalid payload!"
    
    # Re-encryption should also return None for empty input
    reencrypted_data = gateway.reEncryptData(decrypted_at_gateway)
    assert reencrypted_data is None
    
    # Gateway attempts to forward (which does nothing if None)
    gateway.forwardData(cloud, reencrypted_data)
    
    # Cloud service should have an empty buffer
    final_data = cloud.processData()
    assert final_data is None, "Corrupted data accidentally reached the Cloud Service!"


def test_transit_corruption_handling():
    """
    Simulates healthy data being generated, but corrupted during network transit
    to the Edge Gateway. Asserts that the Gateway catches the AES padding/parsing
    error and drops the payload.
    """
    device = LegacyDevice()
    gateway = EdgeGateway()
    cloud = CloudService()
    
    # Generate healthy data (0% hardware failure)
    data = device.generateData(failure_probability=0.0)
    encrypted_data = device.encryptData(data)
    
    # Send it, but force transit corruption (100% corruption probability)
    device.sendEncryptedData(encrypted_data, corruption_probability=1.0)
    
    # Gateway retrieves the corrupted ciphertext
    received_at_gateway = gateway.receiveData(device)
    
    # Decryption should fail due to AES block corruption/padding errors
    decrypted_at_gateway = gateway.decryptData(received_at_gateway)
    assert decrypted_at_gateway is None, "Gateway failed to detect the transit corruption!"
    
    # The rest of the pipeline should gracefully stop
    reencrypted_data = gateway.reEncryptData(decrypted_at_gateway)
    gateway.forwardData(cloud, reencrypted_data)
    
    final_data = cloud.processData()
    assert final_data is None, "Corrupted data accidentally reached the Cloud Service!"
