from main import (
    build_market_data_provider,
    validate_runtime_configuration,
)
from yahoo_provider import YahooProvider


def test_runtime_configuration_is_valid():
    validate_runtime_configuration()


def test_market_data_provider_is_yahoo():
    provider = build_market_data_provider()

    assert isinstance(provider, YahooProvider)
