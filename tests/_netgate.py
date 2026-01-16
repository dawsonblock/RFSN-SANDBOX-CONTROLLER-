# This file should be removed.
# The following logic should be placed in a new 'tests/conftest.py' file.

import os
import pytest

def pytest_collection_modifyitems(config, items):
    """
    Skip tests marked with 'network' if network tests are not enabled.
    """
    if os.environ.get("RFSN_ENABLE_NETWORK_TESTS", "").strip() == "1":
        return

    skip_network = pytest.mark.skip(reason="network tests disabled (set RFSN_ENABLE_NETWORK_TESTS=1 to enable)")
    for item in items:
        if "network" in item.keywords:
            item.add_marker(skip_network)
