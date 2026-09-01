"""Central configuration for MULTIBOT2. Frozen project rules; credentials are environment-only."""
from __future__ import annotations
import os
from dataclasses import dataclass
IST_TIMEZONE="Asia/Kolkata"
DEFAULT_TIMEFRAME="1h"
SIGNAL_FRESHNESS_HOURS=1
NSE_MARKET_OPEN="09:15"
NSE_MARKET_CLOSE="15:30"
MARKET_DATA_PROVIDER="yahoo"
NSE_15_SYMBOLS=("RELIANCE","BHARTIARTL","HDFCBANK","ICICIBANK","SBIN","TCS","BAJFINANCE","LT","LICI","SUNPHARMA","HINDUNILVR","INFY","TITAN","MARUTI","KOTAKBANK")
ACCOUNT_SIZE_INR=100_000
RISK_PER_TRADE_INR=2_000
ACCOUNT_TRADE_LIMITS={"macro":20,"nifty":5,"ny_session":3,"sweep_4h":3}
ACCOUNT_NAMES=("macro","nifty","ny_session","sweep_4h")
LEVERAGE=1.0
MAX_TRADES_PER_DAY=3
MAX_DAILY_PLANNED_RISK_INR=RISK_PER_TRADE_INR*MAX_TRADES_PER_DAY
@dataclass(frozen=True)
class Settings:
    timezone:str=IST_TIMEZONE
    timeframe:str=DEFAULT_TIMEFRAME
    freshness_hours:int=SIGNAL_FRESHNESS_HOURS
    market_data_provider:str=MARKET_DATA_PROVIDER
    telegram_bot_token:str|None=None
    telegram_chat_id:str|None=None
    dashboard_api_url:str="/api/dashboard"
    @classmethod
    def from_env(cls)->"Settings":
        timezone=os.getenv("TIMEZONE",IST_TIMEZONE)
        timeframe=os.getenv("TIMEFRAME",DEFAULT_TIMEFRAME)
        provider=os.getenv("MARKET_DATA_PROVIDER",MARKET_DATA_PROVIDER).strip().lower()
        if timezone!=IST_TIMEZONE: raise ValueError("TIMEZONE must be Asia/Kolkata")
        if timeframe!=DEFAULT_TIMEFRAME: raise ValueError("TIMEFRAME must be 1h")
        if provider!=MARKET_DATA_PROVIDER: raise ValueError("MARKET_DATA_PROVIDER must be yahoo")
        return cls(timezone,timeframe,SIGNAL_FRESHNESS_HOURS,provider,os.getenv("TELEGRAM_BOT_TOKEN"),os.getenv("TELEGRAM_CHAT_ID"),os.getenv("DASHBOARD_API_URL","/api/dashboard"))
settings=Settings.from_env()
def validate_configuration()->None:
    if MARKET_DATA_PROVIDER!="yahoo" or settings.market_data_provider!="yahoo": raise ValueError("MULTIBOT2 market-data provider must be Yahoo Finance")
    if len(NSE_15_SYMBOLS)!=15 or len(set(NSE_15_SYMBOLS))!=15: raise ValueError("NSE universe must contain exactly 15 unique symbols")
    if ACCOUNT_SIZE_INR<=0 or RISK_PER_TRADE_INR<=0: raise ValueError("Account size and risk must be positive")
    if settings.freshness_hours!=SIGNAL_FRESHNESS_HOURS: raise ValueError("Signal freshness must remain locked at 1 hour")
    if set(ACCOUNT_TRADE_LIMITS)!=set(ACCOUNT_NAMES) or any(v<=0 for v in ACCOUNT_TRADE_LIMITS.values()): raise ValueError("Per-account trade limits are invalid")
    if LEVERAGE!=1.0: raise ValueError("MULTIBOT2 uses 1x / no leverage")
validate_configuration()
