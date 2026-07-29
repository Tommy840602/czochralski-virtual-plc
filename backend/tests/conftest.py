import os
import tempfile
import uuid

os.environ["PLC_ENVIRONMENT"] = "test"
os.environ["PLC_DATA_ROOT"] = tempfile.mkdtemp(prefix="plc-health-test-")
os.environ["PLC_DATABASE_URL"] = os.environ.get(
    "PLC_TEST_DATABASE_URL",
    "postgresql://plc:plc@127.0.0.1:5434/plc",
)
os.environ["PLC_DATABASE_SCHEMA"] = f"plc_test_{uuid.uuid4().hex}"
os.environ["PLC_AUTH_USERNAME"] = "test.operator"
os.environ["PLC_AUTH_PASSWORD"] = "test-password-strong"
os.environ["PLC_AUTH_SECRET"] = "test-signing-secret-at-least-32-characters"
