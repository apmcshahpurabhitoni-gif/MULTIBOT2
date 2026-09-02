
from config import (
    ACCOUNT_NAMES, ACCOUNT_SIZE_INR, ACCOUNT_TRADE_LIMITS, BITCOIN_SYMBOL,
    DEFAULT_TIMEFRAME, GOLD_SYMBOL, IST_TIMEZONE, LEVERAGE, LIVE_ASSETS,
    LIVE_SYMBOLS, NIFTY_SYMBOLS, NSE_15_SYMBOLS, RISK_PER_TRADE_INR,
    SIGNAL_FRESHNESS_HOURS, validate_configuration,
)

def test_nse_universe_is_exactly_15():
    assert len(NSE_15_SYMBOLS) == 15
    assert len(set(NSE_15_SYMBOLS)) == 15

def test_live_universe_is_exactly_19():
    assert len(LIVE_ASSETS) == 19
    assert len(set(LIVE_SYMBOLS)) == 19
    assert set(NIFTY_SYMBOLS) == {"^NSEI", "^NSEBANK"}
    assert GOLD_SYMBOL in LIVE_SYMBOLS
    assert BITCOIN_SYMBOL in LIVE_SYMBOLS

def test_expected_nse_stocks():
    assert NSE_15_SYMBOLS == (
        "RELIANCE","BHARTIARTL","HDFCBANK","ICICIBANK","SBIN","TCS",
        "BAJFINANCE","LT","LICI","SUNPHARMA","HINDUNILVR","INFY",
        "TITAN","MARUTI","KOTAKBANK",
    )

def test_asset_metadata_is_consistent():
    for asset in LIVE_ASSETS:
        assert asset.yahoo_symbol
        assert asset.market
        assert asset.group
        assert asset.trendpulse_signal_timeframe == "1H"
        assert asset.trendpulse_filter_timeframe == "4H"
    assert next(a for a in LIVE_ASSETS if a.symbol == "^NSEI").sweep_timeframe == "1H"
    assert next(a for a in LIVE_ASSETS if a.symbol == "^NSEBANK").sweep_timeframe == "1H"

def test_locked_risk_and_accounts():
    assert ACCOUNT_SIZE_INR == 100_000
    assert RISK_PER_TRADE_INR == 2_000
    assert LEVERAGE == 1.0
    assert ACCOUNT_TRADE_LIMITS == {"macro":20,"nifty":5,"ny_session":3,"sweep_4h":3}
    assert ACCOUNT_NAMES == ("macro","nifty","ny_session","sweep_4h")

def test_locked_runtime_settings():
    assert IST_TIMEZONE == "Asia/Kolkata"
    assert DEFAULT_TIMEFRAME == "1h"
    assert SIGNAL_FRESHNESS_HOURS == 1
    validate_configuration()
