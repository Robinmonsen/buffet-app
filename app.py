import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import time

# API-nøkkel fra Streamlit Cloud eller lokal secrets.toml
ALPHA_VANTAGE_KEY = st.secrets["ALPHA_VANTAGE_KEY"]

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
        data["Error"] = str(e)

    return data

# ---------- Streamlit UI ----------

st.title("📈 Buffett-analyse av aksjer")
st.markdown("Skriv inn opptil 10 aksjer separert med komma (f.eks. `AAPL, MSFT, HEX`). Kortnavn uten punktum får automatisk `.OL` lagt til for Oslo Børs.")

# Tekstinput
ticker_input = st.text_input("Skriv inn tickere her:")

if ticker_input:
    tickers = []
    for t in ticker_input.split(","):
        clean = t.strip().upper()
        if "." not in clean and len(clean) <= 5:
            clean += ".OL"  # antar norsk ticker hvis kort og uten punktum
        tickers.append(clean)

    tickers = tickers[:10]  # maks 10 tickere
    st.info(f"📊 Analyserer {len(tickers)} selskaper ...")

    results = []
    for ticker in tickers:
        with st.spinner(f"Analyserer {ticker} ..."):
            results.append(analyze_ticker(ticker))
            time.sleep(12)  # for å unngå Alpha Vantage rate limit

    df_result = pd.DataFrame(results)
    st.success("✅ Ferdig!")
    st.dataframe(df_result)

    # Last ned som Excel
    output_file = "buffett_resultat.xlsx"
    df_result.to_excel(output_file, index=False)

    with open(output_file, "rb") as f:
        st.download_button("📥 Last ned resultatene", f, file_name="buffett_resultat.xlsx")