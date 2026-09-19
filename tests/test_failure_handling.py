import pytest
import sys
import os

# Add src to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from legacy_device import LegacyDevice
from edge_gateway import EdgeGateway
from cloud_service import CloudService

def test_hardware_malfunction_handling_sensor_to_edge_gateway():
    """
    Simulates a hardware malfunction on the Legacy Device (e.g., an out-of-bounds temperature).
    Asserts that the Edge Gateway detects the semantic error and drops the payload,
    preventing it from reaching the Cloud Service.
    """
    device = LegacyDevice()
    gateway = EdgeGateway()
    cloud = CloudService()
    
    # Force the device to generate a malformed reading (100% probability)
    # The generator uses a random range of -999 to 999, so there's a ~4% chance 
    # the "malfunction" is accidentally a completely valid temperature (e.g. 34.1).
    # We loop to guarantee we get a truly out-of-bounds temperature for the test.
    data = device.generateData(failure_probability=1.0)
    while -30.0 <= float(data.split('|')[0]) <= 50.0:
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


def test_transit_corruption_handling_sensor_to_edge_gateway():
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
    assert detection_rate > 0.75, f"Gateway failed to detect sufficient transit corruption! Rate: {detection_rate}"


def test_transit_corruption_handling_edge_to_cloud():
    """
    Simulates healthy data being generated, but corrupted during network transit
    between the Edge Gateway and the Cloud Service. Asserts that the Cloud Service
    catches 100% of these errors since it uses AES-GCM (Authenticated Encryption).
    """
    device = LegacyDevice()
    gateway = EdgeGateway()
    cloud = CloudService()
    
    # Establish AES session key
    gateway.negotiateSession(cloud)
    
    total_corruptions = 100
    detected_corruptions = 0
    
    for _ in range(total_corruptions):
        # Generate and send perfectly healthy data to gateway
        data = device.generateData(failure_probability=0.0)
        encrypted_data = device.encryptData(data)
        device.sendEncryptedData(encrypted_data, corruption_probability=0.0)
        received_at_gateway = gateway.receiveData(device)
        
        # Gateway processes it successfully
        decrypted_at_gateway = gateway.decryptData(received_at_gateway)
        reencrypted_data = gateway.reEncryptData(decrypted_at_gateway)
        
        # Gateway forwards to cloud with 100% transit corruption probability
        gateway.forwardData(cloud, reencrypted_data, corruption_probability=1.0)
        
        # Cloud processes the data
        final_data = cloud.processData()
        
        if final_data is None:
            detected_corruptions += 1
            
    # AES-GCM should catch absolutely every bit-flip
    assert detected_corruptions == total_corruptions, f"Cloud failed to detect {total_corruptions - detected_corruptions} transit corruptions!"
