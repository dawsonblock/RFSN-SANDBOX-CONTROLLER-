"""Network-test gating utilities for pytest."""

def require_network() -> None:
    """
    Skip the current test unless network tests are enabled.
    """
    if os.environ.get("RFSN_ENABLE_NETWORK_TESTS", "").strip() == "1":
        return
    pytest.skip("network tests disabled (set RFSN_ENABLE_NETWORK_TESTS=1 to enable)")

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
