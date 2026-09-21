import pytest
import time
import sys
import os

# Add src to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from legacy_device import LegacyDevice
from edge_gateway import EdgeGateway
from cloud_service import CloudService

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