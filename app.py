import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import time

# 🔐 Henter Alpha Vantage-nøkkel fra secrets
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


# ---------------------- UI ----------------------

st.title("📈 Buffett-analyse")
st.markdown(
    """
    Skriv inn inntil 10 tickere, separert med komma (f.eks. `AAPL, MSFT, EQNR.OL`).  
    Du må inkludere korrekt suffiks selv, for eksempel:

    - `.OL` for Oslo Børs (f.eks. `HEX.OL`)
    - `.ST` for Stockholm (f.eks. `ERIC-B.ST`)
    - `.HE` for Helsinki (f.eks. `NOKIA.HE`)
    """
)

ticker_input = st.text_input("🎯 Tickere (separert med komma):")

if ticker_input:
    tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
    tickers = tickers[:10]  # maks 10

    st.info(f"Starter analyse av {len(tickers)} selskaper ...")
    results = []

    for ticker in tickers:
        with st.spinner(f"🔎 Analyserer {ticker}..."):
            results.append(analyze_ticker(ticker))
            time.sleep(12)  # Alpha Vantage API-begrensning

    df_result = pd.DataFrame(results)
    st.success("✅ Ferdig!")

    st.dataframe(df_result)

    # Nedlasting som Excel
    output_file = "buffett_resultat.xlsx"
    df_result.to_excel(output_file, index=False)

    with open(output_file, "rb") as f:
        st.download_button("📥 Last ned Excel-fil", f, file_name="buffett_resultat.xlsx")