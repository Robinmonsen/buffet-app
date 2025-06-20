import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import time
import matplotlib.pyplot as plt

# 🔐 Alpha Vantage API-nøkkel (fra secrets.toml eller Streamlit Cloud)
ALPHA_VANTAGE_KEY = st.secrets["ALPHA_VANTAGE_KEY"]

# -------- Hent data --------
def get_alpha_vantage_data(ticker):
    url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={ALPHA_VANTAGE_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return {}

def analyze_ticker(ticker):
    data = {"Ticker": ticker}
    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info

        if not info or "shortName" not in info:
            raise ValueError("Ticker ikke funnet eller data utilgjengelig.")

        pe = info.get("trailingPE", np.nan)
        pb = info.get("priceToBook", np.nan)
        roe = info.get("returnOnEquity", np.nan)
        if roe is not None: roe *= 100
        dte = info.get("debtToEquity", np.nan)

        av_data = get_alpha_vantage_data(ticker)
        eps_growth_5y = float(av_data.get("EPSGrowth5Y", np.nan)) if av_data else np.nan
        op_margin = float(av_data.get("OperatingMarginTTM", np.nan)) if av_data else np.nan

        score = 0
        if pe and pe < 20: score += 1
        if pb and pb < 3: score += 1
        if roe and roe > 15: score += 1
        if eps_growth_5y and eps_growth_5y > 10: score += 1
        if dte and dte < 100: score += 1
        if op_margin and op_margin > 10: score += 1

        data.update({
            "P/E": round(pe, 2),
            "P/B": round(pb, 2),
            "ROE (%)": round(roe, 2),
            "EPS growth 5y (%)": round(eps_growth_5y, 2),
            "Debt/Equity": round(dte, 2),
            "Op. Margin (%)": round(op_margin, 2),
            "Buffett Score (0–6)": score
        })

    except Exception as e:
        data.update({
            "P/E": "N/A",
            "P/B": "N/A",
            "ROE (%)": "N/A",
            "EPS growth 5y (%)": "N/A",
            "Debt/Equity": "N/A",
            "Op. Margin (%)": "N/A",
            "Buffett Score (0–6)": 0,
            "Error": str(e)
        })

    return data

# -------- Fargekodingsfunksjon --------
def color_score(val):
    if isinstance(val, int):
        if val == 6:
            return "background-color: #2ECC71; color: black;"  # grønn
        elif val == 5:
            return "background-color: #58D68D; color: black;"
        elif val == 4:
            return "background-color: #ABEBC6; color: black;"
        elif val == 3:
            return "background-color: #F4D03F; color: black;"  # gul
        elif val == 2:
            return "background-color: #F5B041; color: black;"
        elif val == 1:
            return "background-color: #EB984E; color: black;"
        elif val == 0:
            return "background-color: #E74C3C; color: white;"  # rød
    return ""

# -------- Streamlit UI --------
st.set_page_config(page_title="Buffett-analyse", layout="centered")
st.title("📈 Buffett Score – Fundamentalanalyse av aksjer")

st.markdown("""
Skriv inn inntil 10 tickere, separert med komma (f.eks. `AAPL, MSFT, HEX.OL`).  
**Du må inkludere korrekt suffiks** selv, for eksempel:
- `.OL` for Oslo Børs (f.eks. `EQNR.OL`)
- `.ST` for Stockholm (f.eks. `ERIC-B.ST`)
- `.HE` for Helsinki (f.eks. `NOKIA.HE`)
""")

ticker_input = st.text_input("🎯 Tickere:")

if ticker_input:
    tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
    tickers = tickers[:10]

    st.info(f"🔍 Analyserer {len(tickers)} selskaper ...")
    results = []

    for ticker in tickers:
        with st.spinner(f"🔎 Analyserer {ticker} ..."):
            results.append(analyze_ticker(ticker))
            time.sleep(12)  # Alpha Vantage rate limit

    df = pd.DataFrame(results)

    st.success("✅ Ferdig!")

    # 🎨 Fargekoding
    styled_df = df.style.applymap(color_score, subset=["Buffett Score (0–6)"])
    st.dataframe(styled_df, use_container_width=True)

    # 📊 Graf – toppscorede aksjer
    valid_scores = df[df["Buffett Score (0–6)"] > 0]
    if not valid_scores.empty:
        chart_data = valid_scores[["Ticker", "Buffett Score (0–6)"]].sort_values(by="Buffett Score (0–6)", ascending=False)
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.barh(chart_data["Ticker"], chart_data["Buffett Score (0–6)"], color="#2E86C1")
        ax.invert_yaxis()
        ax.set_xlabel("Buffett Score")
        ax.set_title("🔝 Toppscorede aksjer")
        st.pyplot(fig)

    # 📥 Nedlasting
    df.to_excel("buffett_resultat.xlsx", index=False)
    with open("buffett_resultat.xlsx", "rb") as f:
        st.download_button("📥 Last ned Excel", f, file_name="buffett_resultat.xlsx")