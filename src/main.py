import sqlite3
from legacy_device import LegacyDevice
from edge_gateway import EdgeGateway
from cloud_service import CloudService

def short_hex(data) -> str:
    """Returns a short hex preview of bytes or an integer."""
    if isinstance(data, int):
        data = data.to_bytes((data.bit_length() + 7) // 8, 'big')
    return data.hex()[:16] + "..."

def main():
    device = LegacyDevice()
    gateway = EdgeGateway()
    cloud = CloudService()

    SEP = "=" * 60

    print(f"\n{SEP}")
    print("           SDMO — Full Pipeline Demo")
    print(f"{SEP}\n")

    # ------------------------------------------------------------------ #
    # STEP 1: Session Negotiation
    # ------------------------------------------------------------------ #
    print("[1/3] SESSION NEGOTIATION (Hybrid DH + ML-KEM)")
    gateway.negotiateSession(cloud)

    gw_dh_size  = (gateway.dh_public_key.bit_length() + 7) // 8
    gw_ek_size  = len(gateway.mlkem_ek)
    cl_dh_size  = (cloud.dh_public_key.bit_length() + 7) // 8
    cl_ct_size  = len(cloud.mlkem_ciphertext)
    keys_match  = gateway.cloud_aes_key == cloud.aes_key

    print(f"  [Gateway]  DH Public Key      : {short_hex(gateway.dh_public_key)} ({gw_dh_size} bytes)")
    print(f"  [Gateway]  ML-KEM Encap. Key  : {short_hex(gateway.mlkem_ek)} ({gw_ek_size} bytes)")
    print(f"  [Cloud]    DH Public Key      : {short_hex(cloud.dh_public_key)} ({cl_dh_size} bytes)")
    print(f"  [Cloud]    ML-KEM Ciphertext  : {short_hex(cloud.mlkem_ciphertext)} ({cl_ct_size} bytes)")
    print(f"  [Both]     Hybrid AES-256 Key : {gateway.cloud_aes_key.hex()[:16]}... ", end="")
    print("[MATCH]" if keys_match else "[MISMATCH - ERROR]")

    print()

    # ------------------------------------------------------------------ #
    # STEP 2: Full data pipeline
    # ------------------------------------------------------------------ #
    print("[2/3] SENSOR -> GATEWAY -> CLOUD")

    # Device
    raw_data      = device.generateData(failure_probability=0.0)
    encrypted_cbc = device.encryptData(raw_data)
    device.sendEncryptedData(encrypted_cbc, corruption_probability=0.0)
    temp_raw, ts_raw = raw_data.split("|")
    print(f"  [Device]   Raw plaintext      : temp={temp_raw}C, ts={ts_raw}")
    print(f"  [Device]   AES-CBC ciphertext : {short_hex(encrypted_cbc)} ({len(encrypted_cbc)} bytes)")

    # Gateway
    received  = gateway.receiveData(device)
    plaintext = gateway.decryptData(received)
    if plaintext is None:
        print("  [Gateway]  Payload DROPPED (invalid or corrupted)")
        return
    temp, ts = plaintext.split("|")
    print(f"  [Gateway]  Decrypted          : temp={temp}C, ts={ts}")
    print(f"  [Gateway]  Validation         : PASS (temp={temp}C, timestamp OK)")

    reencrypted = gateway.reEncryptData(plaintext)
    gateway.forwardData(cloud, reencrypted)
    print(f"  [Gateway]  AES-GCM ciphertext : {short_hex(reencrypted)} ({len(reencrypted)} bytes)")

    # Cloud
    result = cloud.processData()
    if result is None:
        print("  [Cloud]    Payload DROPPED (decryption or validation failed)")
        return
    res_temp, res_ts = result.split("|")
    print(f"  [Cloud]    Decrypted          : temp={res_temp}C, ts={res_ts}")

    # Show what was saved to SQLite
    conn = sqlite3.connect(cloud.db_path)
    try:
        row = conn.execute("SELECT id, temperature, timestamp FROM messages ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    if row:
        print(f"  [Cloud]    Saved to SQLite    : id={row[0]}, temp={row[1]}, ts={row[2]}")

    print()

    # ------------------------------------------------------------------ #
    # STEP 3: Sensor health check
    # ------------------------------------------------------------------ #
    print("[3/3] SENSOR HEALTH CHECK")
    healthy = cloud.check_sensor_health(timeout_seconds=30)
    print(f"  [Cloud]    Status             : {'OK' if healthy else 'ALARM'}")

    print(f"\n{SEP}\n")

if __name__ == "__main__":
    main()