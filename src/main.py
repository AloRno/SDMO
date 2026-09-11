from legacy_device import LegacyDevice
from edge_gateway import EdgeGateway
from cloud_service import CloudService

def main():
    print("=== System Initialization ===")
    legacy = LegacyDevice()
    gateway = EdgeGateway()
    cloud = CloudService()

    print("\n=== Phase 1: Handshake ===")
    gateway.negotiateSession(cloud)

    print("\n=== Phase 2: Legacy Data Generation ===")
    data = legacy.generateData()
    encrypted_legacy = legacy.encryptData(data)
    legacy.sendEncryptedData(encrypted_legacy)

    print("\n=== Phase 3: Edge Gateway Processing ===")
    received_from_legacy = gateway.receiveData(legacy)
    if received_from_legacy:
        decrypted_plaintext = gateway.decryptData(received_from_legacy)
        re_encrypted = gateway.reEncryptData(decrypted_plaintext)
        gateway.forwardData(cloud, re_encrypted)

    print("\n=== Phase 4: Cloud Service Processing ===")
    cloud.processData()

    print("\n=== Pipeline Complete ===")

if __name__ == "__main__":
    main()