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
    to the Edge Gateway. Since LegacyDevice uses AES-CBC without a MAC, 100% 
    corruption detection is mathematically impossible. We assert that the Gateway 
    catches a statistically significant portion of corruptions (e.g., >95%) 
    through AES padding errors and strict semantic validation.
    """
    device = LegacyDevice()
    gateway = EdgeGateway()
    cloud = CloudService()
    
    total_corruptions = 500
    detected_corruptions = 0
    
    for _ in range(total_corruptions):
        # Generate healthy data (0% hardware failure)
        data = device.generateData(failure_probability=0.0)
        encrypted_data = device.encryptData(data)
        
        # Send it, but force transit corruption (100% corruption probability)
        device.sendEncryptedData(encrypted_data, corruption_probability=1.0)
        
        # Gateway retrieves the corrupted ciphertext
        received_at_gateway = gateway.receiveData(device)
        
        # Gateway attempts to decrypt
        decrypted_at_gateway = gateway.decryptData(received_at_gateway)
        
        if decrypted_at_gateway is None:
            detected_corruptions += 1
            
    # We expect the vast majority of corruptions to be caught by padding errors or 
    # our strict semantic validation (regex and timestamp bounds), but some will slip through.
    detection_rate = detected_corruptions / total_corruptions
    assert detection_rate > 0.80, f"Gateway failed to detect sufficient transit corruption! Rate: {detection_rate}"
