import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import requests
import time

# Alpha Vantage API-nøkkel fra Streamlit secrets
ALPHA_VANTAGE_KEY = st.secrets["ALPHA_VANTAGE_KEY"]

# 📋 Liste over kjente aksjer i Norden
aksjeliste = {
    "Norge": {
        "HEXAGON COMPOSITES": "HEX.OL",
        "DNB BANK": "DNB.OL",
        "EQUINOR": "EQNR.OL",
        "ORKLA": "ORK.OL",
        "YARA": "YAR.OL",
        "TOMRA": "TOM.OL",
        "AKER BP": "AKRBP.OL",
        "MOWI": "MOWI.OL",
        "SALMAR": "SALM.OL",
        "KAHOOT": "KAHOT.OL"
    },
    "Sverige": {
        "H&M": "HM-B.ST",
        "ELECTROLUX": "ELUX-B.ST",
        "VOLVO": "VOLV-B.ST",
        "ERICSSON": "ERIC-B.ST",
        "SANDVIK": "SAND.ST"
    },
    "Finland": {
        "NOKIA": "NOKIA.HE",
        "KESKO": "KESKOB.HE",
        "UPM": "UPM.HE"
    }
}

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

# ----------------- Streamlit UI -------------------

st.title("📈 Buffett Score – Fundamental aksjeanalyse")
st.markdown("Velg inntil 10 nordiske aksjer fra listen eller skriv inn egne tickere manuelt (f.eks. AAPL, MSFT).")

# Rullegardin med grupperte aksjer
valg_norske = st.multiselect("🇳🇴 Norske aksjer", list(aksjeliste["Norge"].keys()))
valg_svenske = st.multiselect("🇸🇪 Svenske aksjer", list(aksjeliste["Sverige"].keys()))
valg_finske = st.multiselect("🇫🇮 Finske aksjer", list(aksjeliste["Finland"].keys()))

# Manuell tekstinput
manuell_input = st.text_input("✍️ Evt. egne tickere (kommaseparert, f.eks. AAPL, TSLA, AMZN)")

# Kombiner valgte tickere
tickers = []

for navn in valg_norske:
    tickers.append(aksjeliste["Norge"][navn])
for navn in valg_svenske:
    tickers.append(aksjeliste["Sverige"][navn])
for navn in valg_finske:
    tickers.append(aksjeliste["Finland"][navn])

if manuell_input:
    for t in manuell_input.split(","):
        clean = t.strip().upper()
        if "." not in clean and len(clean) <= 5:
            clean += ".OL"  # antar Oslo Børs hvis kort og uten suffix
        tickers.append(clean)

tickers = tickers[:10]  # maks 10 tickere

# ----------------------------------------

if tickers:
    st.info(f"📊 Analyserer {len(tickers)} selskaper ...")
    results = []
    for ticker in tickers:
        with st.spinner(f"Analyserer {ticker} ..."):
            results.append(analyze_ticker(ticker))
            time.sleep(12)  # for å unngå API-rate limit
    df_result = pd.DataFrame(results)

    st.success("✅ Analyse ferdig!")
    st.dataframe(df_result)

    # Last ned som Excel
    output_file = "buffett_resultat.xlsx"
    df_result.to_excel(output_file, index=False)

    with open(output_file, "rb") as f:
        st.download_button("📥 Last ned som Excel", f, file_name="buffett_resultat.xlsx")