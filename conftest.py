def pytest_configure(config):
    config.addinivalue_line("markers", "bug: tests that reproduce bugs")
    config.addinivalue_line("markers", "slow: tests that take long time to run")