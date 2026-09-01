from config import (
    ACCOUNT_NAMES,
    ACCOUNT_SIZE_INR,
    DEFAULT_TIMEFRAME,
    IST_TIMEZONE,
    LEVERAGE,
    MAX_DAILY_PLANNED_RISK_INR,
    MAX_TRADES_PER_DAY,
    NSE_15_SYMBOLS,
    RISK_PER_TRADE_INR,
    SIGNAL_FRESHNESS_HOURS,
    validate_configuration,
)


def test_nse_universe_contains_exactly_15_symbols():
    assert len(NSE_15_SYMBOLS) == 15
    assert len(set(NSE_15_SYMBOLS)) == 15


def test_nse_universe_is_fixed_expected_list():
    assert NSE_15_SYMBOLS == (
        "RELIANCE",
        "BHARTIARTL",
        "HDFCBANK",
        "ICICIBANK",
        "SBIN",
        "TCS",
        "BAJFINANCE",
        "LT",
        "LICI",
        "SUNPHARMA",
        "HINDUNILVR",
        "INFY",
        "TITAN",
        "MARUTI",
        "KOTAKBANK",
    )


def test_account_size():
    assert ACCOUNT_SIZE_INR == 100_000


def test_risk_per_trade():
    assert RISK_PER_TRADE_INR == 2_000


def test_max_trades_per_day():
    assert MAX_TRADES_PER_DAY == 3


def test_daily_planned_risk():
    assert (
        MAX_DAILY_PLANNED_RISK_INR
        == 6_000
    )


def test_leverage_is_one_x():
    assert LEVERAGE == 1.0


def test_four_accounts_are_configured():
    assert len(ACCOUNT_NAMES) == 4


def test_expected_account_names():
    assert ACCOUNT_NAMES == (
        "macro",
        "nifty",
        "ny_session",
        "sweep_4h",
    )


def test_timezone_is_ist():
    assert IST_TIMEZONE == "Asia/Kolkata"


def test_primary_timeframe_is_one_hour():
    assert DEFAULT_TIMEFRAME == "1h"


def test_signal_freshness_is_one_hour():
    assert SIGNAL_FRESHNESS_HOURS == 1


def test_complete_configuration_is_valid():
    validate_configuration()
