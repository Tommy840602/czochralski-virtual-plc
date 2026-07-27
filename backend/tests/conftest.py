import os
import tempfile

os.environ["PLC_ENVIRONMENT"] = "test"
os.environ["PLC_DATA_ROOT"] = tempfile.mkdtemp(prefix="plc-health-test-")
os.environ["PLC_AUTH_USERNAME"] = "test.operator"
os.environ["PLC_AUTH_PASSWORD"] = "test-password-strong"
os.environ["PLC_AUTH_SECRET"] = "test-signing-secret-at-least-32-characters"
