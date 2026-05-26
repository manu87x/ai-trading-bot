import yfinance as yf
from textblob import TextBlob
import requests
import time

# ====================================
# TELEGRAM CONFIG
# ====================================

TELEGRAM_BOT_TOKEN = "8805383327:AAEnXgJl9d70ly8SMyPFWZPioJspaAb2bWs"
TELEGRAM_CHAT_ID = "612977869"

# ====================================
# STOCK LIST
# ====================================

TICKERS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "AMZN",
    "META",
    "GOOGL",
    "AMD",
    "PLTR",
    "SMCI",
    "ARM",
    "SOFI",
    "HOOD",
    "RIVN",
    "UPST",
    "MU",
    "AVGO",
    "QCOM",
    "INTC",
    "XOM",
    "CVX",
    "SPY",
    "QQQ"
]

# ====================================
# TELEGRAM FUNCTION
# ====================================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    requests.post(url, json=payload)

# ====================================
# SENTIMENT
# ====================================

def analyze_sentiment(text):
    score = TextBlob(text).sentiment.polarity
    if score > 0.1:
        return "POSITIVE"
    elif score < -0.1:
        return "NEGATIVE"
    return "NEUTRAL"

# ====================================
# MAIN LOOP
# ====================================

while True:
    print("Scanning market...")

    for ticker in TICKERS:
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="6mo")

            if len(df) < 50:
                continue

            # MOVING AVERAGES
            df["SMA20"] = df["Close"].rolling(20).mean()
            df["SMA50"] = df["Close"].rolling(50).mean()

            # RSI
            delta = df["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df["RSI"] = 100 - (100 / (1 + rs))

            last = df.iloc[-1]
            rsi = round(last["RSI"], 2)
            trend = "BULLISH" if last["SMA20"] > last["SMA50"] else "BEARISH"

            # VOLUME
            volume_avg = df["Volume"].rolling(20).mean().iloc[-1]
            volume_spike = last["Volume"] > volume_avg * 2

            # BREAKOUT
            recent_high = df["Close"].rolling(20).max().iloc[-2]
            breakout = last["Close"] > recent_high

            # NEWS
            sentiment = "NEUTRAL"
            try:
                news = stock.news
                if len(news) > 0:
                    headlines = [n["title"] for n in news[:5]]
                    combined = " ".join(headlines)
                    sentiment = analyze_sentiment(combined)
            except:
                pass

            # AI SCORE
            score = 0
            if trend == "BULLISH":
                score += 5
            if volume_spike:
                score += 4
            if sentiment == "POSITIVE":
                score += 3
            if breakout:
                score += 2
            if 55 < rsi < 70:
                score += 2

            # ALERT
            if score >= 10:
                telegram_message = f"""
🚀 STRONG BUY SIGNAL

Ticker: {ticker}
Price: ${round(last["Close"], 2)}
Trend: {trend}
RSI: {rsi}
Breakout: {breakout}
News: {sentiment}
AI Score: {score}
"""
                send_telegram(telegram_message)
                print(f"Alert sent for {ticker}")

        except Exception as e:
            print(f"Error on {ticker}: {e}")

    print("Waiting 5 minutes...")
    time.sleep(300)
