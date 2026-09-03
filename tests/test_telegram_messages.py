import pandas as pd
import pytest

from strategies import StrategySignal
from telegram import DASHBOARD_URL, TelegramTemplateError, msg_start, render_signal_message


def _signal(direction: str) -> StrategySignal:
    return StrategySignal(
        strategy="TrendPulse",
        signal=direction,
        timestamp=pd.Timestamp("2026-08-31 10:15:00+05:30"),
        reason="TEST",
        entry=100.0,
        atr=2.0,
    )


def test_trendpulse_buy_message_contract():
    message = render_signal_message(
        _signal("BUY"),
        symbol="RELIANCE.NS",
        asset="Reliance",
        market="NSE",
        timeframe="1H",
        entry=100.0,
        stop_loss=97.0,
        take_profit=106.0,
        quantity=10.0,
        risk=30.0,
        account="nifty",
        freshness="FRESH",
        age_str="30 min ago",
    )

    expected = (
        "🟢 *TrendPulse · Reliance* · ✅\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🪙 *Asset:* `Reliance` (`RELIANCE.NS`)\n"
        "🌐 *Market:* NSE\n"
        "📊 *Direction:* LONG 📈\n"
        "⏱ *Timeframe:* 1H\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⏳ *Signal Status:* `FRESH` (30 min ago)\n"
        "⏰ *Candle Closed:* `31-Aug-2026 10:15 IST`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💼 *PAPER TRADE EXECUTED*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏢 *Account:* `NIFTY`\n"
        "📍 *Entry:* `₹100.00`\n"
        "🛑 *Stop Loss:* `₹97.00`\n"
        "🎯 *Take Profit:* `₹106.00`\n"
        "📦 *Quantity:* `10.0000`\n"
        "💸 *Risk:* `₹30.00`\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "ℹ️ _✅ FRESH = Closed ≤1h ago | ⚠️ STALE = Closed >1h ago_\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    assert message.text == expected


def test_trendpulse_sell_message_contract():
    message = render_signal_message(
        _signal("SELL"),
        symbol="TCS.NS",
        asset="TCS",
        market="NSE",
        timeframe="1H",
        entry=100.0,
        stop_loss=103.0,
        take_profit=94.0,
        quantity=10.0,
        risk=30.0,
        account="nifty",
        freshness="FRESH",
        age_str="5 min ago",
    )

    assert "📊 *Direction:* SHORT 📉" in message.text
    assert "*TrendPulse · TCS*" in message.text
    assert "`₹103.00`" in message.text
    assert "`₹94.00`" in message.text


def test_neutral_signal_fails_closed():
    with pytest.raises(TelegramTemplateError):
        render_signal_message(
            StrategySignal(
                strategy="TrendPulse",
                signal="NEUTRAL",
                timestamp=pd.Timestamp("2026-08-31 10:15:00+05:30"),
                reason="TEST",
            ),
            symbol="RELIANCE.NS",
        )


def test_start_message_uses_multibot2_dashboard_not_leadhunter():
    message = msg_start()
    assert DASHBOARD_URL == "https://multibot2-t74l.onrender.com/dashboard"
    assert "https://multibot2-t74l.onrender.com/dashboard" in message
    assert "lead-generator-zzty.onrender.com" not in message
