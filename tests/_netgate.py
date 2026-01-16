import os
import pytest

def require_network():
    """
    Skip tests that need outbound network (git clone, pip install from internet, etc.)
    Enabled only when RFSN_ENABLE_NETWORK_TESTS=1.
    """
    if os.environ.get("RFSN_ENABLE_NETWORK_TESTS", "").strip() != "1":
        pytest.skip("network tests disabled (set RFSN_ENABLE_NETWORK_TESTS=1 to enable)")
