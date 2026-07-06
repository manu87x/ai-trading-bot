import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import yfinance as yf
from textblob import TextBlob


TELEGRAM_BOT_TOKEN = os.getenv("8805383327:AAG1yWdfHgP-pEFeKhBqmbIAeinJxb_cXgk")
TELEGRAM_CHAT_ID = os.getenv("612977869")


TICKERS = [
    "AAPL", "KO", "PEP", "COST", "WMT", "MCD", "JPM", "V", "JNJ",
    "CAT", "HD", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL",
    "AMD", "PLTR", "SMCI", "ARM", "SOFI", "HOOD", "RIVN", "UPST",
    "MU", "AVGO", "QCOM", "INTC", "XOM", "CVX", "SPY", "QQQ",
    "AXP", "BAC", "OXY", "KHC", "MCO"
]


def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }

        response = requests.post(url, json=payload, timeout=10)

        print("TELEGRAM STATUS:", response.status_code)
        print("TELEGRAM RESPONSE:", response.text)

    except Exception as e:
        print(f"TELEGRAM ERROR: {e}")


def analyze_sentiment(text):
    polarity = TextBlob(text).sentiment.polarity

    if polarity > 0.1:
        return "POSITIVE"
    elif polarity < -0.1:
        return "NEGATIVE"

    return "NEUTRAL"


def calculate_rsi(df):
    delta = df["Close"].diff()

    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()

    rs = gain / loss

    df["RSI"] = 100 - (100 / (1 + rs))

    return df


def get_market_trend():
    try:
        spy = yf.Ticker("SPY")
        spy_df = spy.history(period="3mo")

        if len(spy_df) < 50:
            return False

        spy_df["EMA20"] = spy_df["Close"].ewm(span=20, adjust=False).mean()
        spy_df["EMA50"] = spy_df["Close"].ewm(span=50, adjust=False).mean()

        spy_last = spy_df.iloc[-1]

        return spy_last["EMA20"] > spy_last["EMA50"]

    except Exception as e:
        print(f"Market trend error: {e}")
        return False


def get_sentiment(stock, ticker):
    sentiment = "NEUTRAL"

    try:
        news = stock.news

        if len(news) > 0:
            headlines = []

            for n in news[:5]:
                if "title" in n:
                    headlines.append(n["title"])

            combined = " ".join(headlines)

            if combined.strip():
                sentiment = analyze_sentiment(combined)

    except Exception as e:
        print(f"News error on {ticker}: {e}")

    return sentiment


def calculate_fundamental_score(stock, ticker):
    score = 0

    data = {
        "pe": None,
        "roe": None,
        "profit_margin": None,
        "revenue_growth": None,
        "debt_to_equity": None,
        "free_cashflow": None
    }

    try:
        info = stock.info

        data["pe"] = info.get("trailingPE")
        data["roe"] = info.get("returnOnEquity")
        data["profit_margin"] = info.get("profitMargins")
        data["revenue_growth"] = info.get("revenueGrowth")
        data["debt_to_equity"] = info.get("debtToEquity")
        data["free_cashflow"] = info.get("freeCashflow")

        pe = data["pe"]
        roe = data["roe"]
        profit_margin = data["profit_margin"]
        revenue_growth = data["revenue_growth"]
        debt_to_equity = data["debt_to_equity"]
        free_cashflow = data["free_cashflow"]

        if pe is not None:
            if pe < 25:
                score += 2
            elif pe < 40:
                score += 1

        if roe is not None:
            if roe > 0.20:
                score += 2
            elif roe > 0.10:
                score += 1

        if profit_margin is not None:
            if profit_margin > 0.20:
                score += 2
            elif profit_margin > 0.10:
                score += 1

        if revenue_growth is not None:
            if revenue_growth > 0.10:
                score += 2
            elif revenue_growth > 0:
                score += 1

        if debt_to_equity is not None:
            if debt_to_equity < 50:
                score += 1

        if free_cashflow is not None:
            if free_cashflow > 0:
                score += 1

    except Exception as e:
        print(f"Fundamental error on {ticker}: {e}")

    return score, data


def format_percent(value):
    if value is None:
        return "N/A"

    try:
        return f"{round(value * 100, 2)}%"
    except Exception:
        return "N/A"


def format_number(value):
    if value is None:
        return "N/A"

    try:
        return round(value, 2)
    except Exception:
        return "N/A"


def analyze_ticker(ticker, market_bullish):
    stock = yf.Ticker(ticker)

    df = stock.history(period="6mo")

    if len(df) < 50:
        print(f"{ticker}: Not enough data")
        return

    df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()

    df = calculate_rsi(df)

    last = df.iloc[-1]

    price = round(last["Close"], 2)
    rsi = round(last["RSI"], 2)

    trend = "BULLISH" if last["EMA20"] > last["EMA50"] else "BEARISH"

    today_close = df["Close"].iloc[-1]
    yesterday_close = df["Close"].iloc[-2]

    reversal = (
        today_close > yesterday_close
        and today_close > last["EMA20"]
    )

    volume_avg = df["Volume"].rolling(20).mean().iloc[-1]
    volume_spike = last["Volume"] > volume_avg * 1.15

    recent_high = df["Close"].rolling(20).max().iloc[-2]

    pullback = last["Close"] < recent_high * 0.97

    distance_from_high = round(
        ((recent_high - last["Close"]) / recent_high) * 100,
        2
    )

    deep_pullback = distance_from_high > 30

    sentiment = get_sentiment(stock, ticker)

    fundamental_score, fundamentals = calculate_fundamental_score(stock, ticker)

    technical_score = 0

    if trend == "BULLISH":
        technical_score += 4

    if market_bullish:
        technical_score += 2

    if volume_spike:
        technical_score += 4

    if sentiment == "POSITIVE":
        technical_score += 3

    if pullback:
        technical_score += 3
    else:
        technical_score -= 2

    if rsi < 30:
        technical_score += 5
    elif rsi < 40:
        technical_score += 3
    elif rsi < 55:
        technical_score += 2
    elif rsi > 65:
        technical_score -= 3

    if reversal:
        technical_score += 3

    if deep_pullback:
        technical_score -= 3

    total_score = technical_score + fundamental_score

    print(
        f"{ticker} | Trend={trend} | RSI={rsi} | "
        f"Pullback={pullback} | Reversal={reversal} | "
        f"Technical={technical_score} | Fundamental={fundamental_score} | "
        f"Total={total_score}"
    )

    if trend != "BULLISH":
        return

    if total_score >= 18:
        telegram_message = f"""
🚀 STRONG BUY SIGNAL

Ticker: {ticker}
Price: ${price}

📈 TECHNICAL
Trend: {trend}
Market Bullish: {market_bullish}
RSI: {rsi}
Pullback: {pullback}
Reversal: {reversal}
Volume Spike: {volume_spike}
Deep Pullback: {deep_pullback}
Distance From High: {distance_from_high}%

🏢 FUNDAMENTALS
P/E: {format_number(fundamentals["pe"])}
ROE: {format_percent(fundamentals["roe"])}
Profit Margin: {format_percent(fundamentals["profit_margin"])}
Revenue Growth: {format_percent(fundamentals["revenue_growth"])}
Debt/Equity: {format_number(fundamentals["debt_to_equity"])}
Free Cash Flow: {format_number(fundamentals["free_cashflow"])}

🧠 SCORES
Technical Score: {technical_score}
Fundamental Score: {fundamental_score}/10
Total AI Score: {total_score}

News: {sentiment}
"""

        send_telegram(telegram_message)

        print(f"ALERT SENT: {ticker}")


while True:
    try:
        now = datetime.now(ZoneInfo("Europe/Rome"))
        current_hour = now.hour

        if now.weekday() >= 5:
            print("Weekend - Market closed")
            time.sleep(3600)
            continue

        print(f"Current hour: {current_hour}")

        if (
            current_hour < 15
            or (current_hour == 15 and now.minute < 30)
            or current_hour >= 22
        ):
            print("Market closed")
            time.sleep(1800)
            continue

        print("===================================")
        print("Scanning market...")
        print("===================================")

        market_bullish = get_market_trend()

        print(f"Market bullish: {market_bullish}")

        for ticker in TICKERS:
            try:
                print(f"Checking {ticker}...")
                analyze_ticker(ticker, market_bullish)

            except Exception as e:
                print(f"ERROR on {ticker}: {e}")

        print("Waiting 15 minutes...")
        time.sleep(900)

    except Exception as main_error:
        print(f"MAIN LOOP ERROR: {main_error}")
        time.sleep(60)

