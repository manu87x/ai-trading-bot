import streamlit as st
import yfinance as yf
import pandas as pd
from textblob import TextBlob
import plotly.graph_objects as go
import requests

# ====================================
# PAGE CONFIG
# ====================================

st.set_page_config(
    page_title="AI Trading Scanner",
    layout="wide"
)

st.title("🚀 AI Trading Scanner")

# ====================================
# TELEGRAM CONFIG
# ====================================

TELEGRAM_BOT_TOKEN = "8805383327:AAEnXgJl9d70ly8SMyPFWZPioJspaAb2bWs"
TELEGRAM_CHAT_ID = "612977869"

# ====================================
# STOCK LIST
# ====================================

TICKERS = [

    # BIG TECH
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "AMZN",
    "META",
    "GOOGL",

    # AI STOCKS
    "AMD",
    "PLTR",
    "SMCI",
    "ARM",

    # MOMENTUM
    "SOFI",
    "HOOD",
    "RIVN",
    "UPST",

    # SEMICONDUCTORS
    "MU",
    "AVGO",
    "QCOM",
    "INTC",

    # ENERGY
    "XOM",
    "CVX",

    # ETFs
    "SPY",
    "QQQ"
]

results = []

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
# SENTIMENT FUNCTION
# ====================================

def analyze_sentiment(text):

    score = TextBlob(text).sentiment.polarity

    if score > 0.1:
        return "POSITIVE"

    elif score < -0.1:
        return "NEGATIVE"

    return "NEUTRAL"

# ====================================
# MAIN SCANNER
# ====================================

for ticker in TICKERS:

    try:

        stock = yf.Ticker(ticker)

        df = stock.history(period="6mo")

        if len(df) < 50:
            continue

        # =========================
        # MOVING AVERAGES
        # =========================

        df["SMA20"] = df["Close"].rolling(20).mean()
        df["SMA50"] = df["Close"].rolling(50).mean()

        # =========================
        # RSI
        # =========================

        delta = df["Close"].diff()

        gain = (delta.where(delta > 0, 0)).rolling(14).mean()

        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()

        rs = gain / loss

        df["RSI"] = 100 - (100 / (1 + rs))

        # =========================
        # LAST DATA
        # =========================

        last = df.iloc[-1]

        rsi = round(last["RSI"], 2)

        trend = (
            "BULLISH"
            if last["SMA20"] > last["SMA50"]
            else "BEARISH"
        )

        # =========================
        # VOLUME SPIKE
        # =========================

        volume_avg = df["Volume"].rolling(20).mean().iloc[-1]

        volume_spike = last["Volume"] > volume_avg

        # =========================
        # BREAKOUT
        # =========================

        recent_high = df["Close"].rolling(20).max().iloc[-2]

        breakout = last["Close"] > recent_high

        # =========================
        # NEWS SENTIMENT
        # =========================

        sentiment = "NEUTRAL"

        try:

            news = stock.news

            if len(news) > 0:

                headlines = []

                for n in news[:5]:
                    headlines.append(n["title"])

                combined = " ".join(headlines)

                sentiment = analyze_sentiment(combined)

        except:
            pass

        # =========================
        # AI SCORE
        # =========================

        score = 0

        if trend == "BULLISH":
            score += 5

        if volume_spike:
            score += 4

        if sentiment == "POSITIVE":
            score += 3

        if breakout:
            score += 2

        # =========================
        # SAVE RESULTS
        # =========================

        results.append({
            "Ticker": ticker,
            "Price": round(last["Close"], 2),
            "Trend": trend,
            "RSI": rsi,
            "Breakout": breakout,
            "News": sentiment,
            "AI Score": score
        })

        # =========================
        # TELEGRAM ALERT
        # =========================

        if score >= 7:

            telegram_message = f"""
🚀 BUY SIGNAL

Ticker: {ticker}
Price: ${round(last["Close"], 2)}
Trend: {trend}
RSI: {rsi}
Breakout: {breakout}
News: {sentiment}
AI Score: {score}
"""

            send_telegram(telegram_message)

    except Exception as e:

        st.write(f"Error on {ticker}: {e}")

# ====================================
# RESULTS TABLE
# ====================================

results_df = pd.DataFrame(results)

if not results_df.empty:

    results_df = results_df.sort_values(
        by="AI Score",
        ascending=False
    )

    st.subheader("🔥 Top Trading Signals")

    st.dataframe(results_df)

    # ====================================
    # CHART SECTION
    # ====================================

    selected = st.selectbox(
        "Select Ticker",
        results_df["Ticker"]
    )

    stock = yf.Ticker(selected)

    chart_df = stock.history(period="6mo")

    # CREATE SMA LINES
    chart_df["SMA20"] = chart_df["Close"].rolling(20).mean()

    chart_df["SMA50"] = chart_df["Close"].rolling(50).mean()

    # ====================================
    # PLOT
    # ====================================

    fig = go.Figure()

    # PRICE
    fig.add_trace(
        go.Scatter(
            x=chart_df.index,
            y=chart_df["Close"],
            name="Price"
        )
    )

    # SMA20
    fig.add_trace(
        go.Scatter(
            x=chart_df.index,
            y=chart_df["SMA20"],
            name="SMA20"
        )
    )

    # SMA50
    fig.add_trace(
        go.Scatter(
            x=chart_df.index,
            y=chart_df["SMA50"],
            name="SMA50"
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:

    st.warning("No trading signals found.")