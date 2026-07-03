import yfinance as yf
from textblob import TextBlob
import requests
import time
from datetime import datetime
from zoneinfo import ZoneInfo

# ====================================
# TELEGRAM CONFIG
# ====================================

TELEGRAM_BOT_TOKEN = "8805383327:AAG1yWdfHgP-pEFeKhBqmbIAeinJxb_cXgk"
TELEGRAM_CHAT_ID = "612977869"

# ====================================
# STOCK LIST
# ====================================

TICKERS = [
    "AAPL",
    "KO",
    "PEP",
    "COST",
    "WMT",
    "MCD",
    "JPM",
    "V",
    "JNJ",
    "CAT",
    "HD",
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
    "QQQ",
    "AXP",
    "BAC",
    "OXY",
    "KHC",
    "MCO",
]

# ====================================
# TELEGRAM FUNCTION
# ====================================

def send_telegram(message):

    try:

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }

        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        print("TELEGRAM STATUS:")
        print(response.status_code)

        print("TELEGRAM RESPONSE:")
        print(response.text)

    except Exception as e:

        print(f"TELEGRAM ERROR: {e}")

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

    try:
        
        now = datetime.now(
            ZoneInfo("Europe/Rome")
        )

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

        # ====================================
        # MARKET TREND
        # ====================================

        spy = yf.Ticker("SPY")
        spy_df = spy.history(period="3mo")

        spy_df["EMA20"] = spy_df["Close"].ewm(span=20, adjust=False).mean()
        spy_df["EMA50"] = spy_df["Close"].ewm(span=50, adjust=False).mean()

        spy_last = spy_df.iloc[-1]

        market_bullish = spy_last["EMA20"] > spy_last["EMA50"]

        print(f"Market bullish: {market_bullish}")
        
        for ticker in TICKERS:

            try:
               
                print(f"Checking {ticker}...")

                stock = yf.Ticker(ticker)

                df = stock.history(period="6mo")

                if len(df) < 50:
                    print(f"{ticker}: Not enough data")
                    continue

                # ====================================
                # MOVING AVERAGES
                # ====================================

                df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
                df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
                
                # ====================================
                # RSI
                # ====================================

                delta = df["Close"].diff()

                gain = (delta.where(delta > 0, 0)).rolling(14).mean()

                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()

                rs = gain / loss

                df["RSI"] = 100 - (100 / (1 + rs))

                last = df.iloc[-1]

                rsi = round(last["RSI"], 2)

                trend = "BULLISH" if last["EMA20"] > last["EMA50"] else "BEARISH"

                today_close = df["Close"].iloc[-1]
                yesterday_close = df["Close"].iloc[-2]

                reversal = (
                    today_close > yesterday_close
                    and today_close > last["EMA20"]
                )
                
                # ====================================
                # VOLUME
                # ====================================

                volume_avg = df["Volume"].rolling(20).mean().iloc[-1]

                volume_spike = last["Volume"] > volume_avg * 1.15

                # ====================================
                # PULLBACK ANALYSIS
                # ====================================

                recent_high = df["Close"].rolling(20).max().iloc[-2]

                pullback = last["Close"] < recent_high * 0.97

                distance_from_high = round(
                    ((recent_high - last["Close"]) / recent_high) * 100,
                    2
                )

                # Penalizza pullback troppo profondi
                if distance_from_high > 30:
                    deep_pullback = True
                else:
                    deep_pullback = False
                
                # ====================================
                # NEWS SENTIMENT
                # ====================================

                sentiment = "NEUTRAL"

                try:

                    news = stock.news

                    if len(news) > 0:

                        headlines = []

                        for n in news[:5]:

                            if "title" in n:
                                headlines.append(n["title"])

                        combined = " ".join(headlines)

                        sentiment = analyze_sentiment(combined)

                except Exception as news_error:

                    print(f"News error on {ticker}: {news_error}")

                # ====================================
                # AI SCORE
                # ====================================

                score = 0

                # Trend principale
                if trend == "BULLISH":
                  score += 4

                # Mercato generale
                if market_bullish:
                  score += 2

                # Volume
                if volume_spike:
                  score += 4

                # Sentiment
                if sentiment == "POSITIVE":
                  score += 3

                # Pullback
                if pullback:
                  score += 3
                else:
                  score -= 2

                # RSI
                if rsi < 30:
                  score += 5

                elif rsi < 40:
                    score += 3

                elif rsi < 55:
                    score += 2

                elif rsi > 65:
                    score -= 3

                # Primo segnale di inversione
                if reversal:
                  score += 3

                # Penalità se il titolo è crollato troppo
                if deep_pullback:
                  score -= 3

                print(f"{ticker} score: {score}")
               
                # Scarta tutti i titoli ancora in trend ribassista
                if trend != "BULLISH":
                    continue
                
                # ====================================
                # ALERT
                # ====================================

                if score >= 13 and trend == "BULLISH":
                    
                    print("TRYING TELEGRAM...")
                    
                    telegram_message = f"""
🚀 STRONG BUY SIGNAL

Ticker: {ticker}
Price: ${round(last['Close'], 2)}
Trend: {trend}
RSI: {rsi}
Pullback: {pullback}
Reversal: {reversal}
Volume Spike: {volume_spike}
Distance From High: {distance_from_high}%
News: {sentiment}
AI Score: {score}
"""

                    send_telegram(telegram_message)

                    print(f"ALERT SENT: {ticker}")

            except Exception as e:

                print(f"ERROR on {ticker}: {e}")

        print("Waiting 15 minutes...")
        time.sleep(900)

    except Exception as main_error:

        print(f"MAIN LOOP ERROR: {main_error}")

        time.sleep(60)
