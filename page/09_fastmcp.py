import streamlit as st
import pandas as pd
import talib
import ollama
from page.utils import read_table

# ------------------------------------------------------------------
# 1️⃣  Load your data first (the part you already have)
# ------------------------------------------------------------------
@st.cache_data
def load_data():
    use_postgres = st.session_state.get("use_postgres", True)
    if use_postgres:
        df_fon_table = read_table('tefas_funds', parse_dates=None)
        df_transformed = read_table('tefas_transformed', parse_dates=['date'], filter_condition=" date > ( SELECT MAX(date) - 40 FROM ""tefas_transformed"" ) ")
    return df_fon_table, df_transformed

df_fon_table, df_transformed = load_data()
df_merged = pd.merge(df_transformed, df_fon_table, on='symbol', how='inner')

# ------------------------------------------------------------------
# 2️⃣  Prepare the “table” that will be embedded in the prompt
# ------------------------------------------------------------------
df_changes = df_merged.copy()
# Exclude rows where FundType_Özel or FundType_Serbest is True
if "FundType_Özel" in df_changes.columns:
    df_changes = df_changes[df_changes["FundType_Özel"] != True]
if "FundType_Serbest" in df_changes.columns:
    df_changes = df_changes[df_changes["FundType_Serbest"] != True]

df_changes = df_changes.sort_values(['symbol', 'date'])
df_changes['pct_change'] = df_changes.groupby('symbol')['close'].pct_change().fillna(0) * 100

indicator_rows = []
day_headers = ["1 Day % Change", "7 Day % Change", "30 Day % Change", "90 Day % Change", "180 Day % Change", "1 Year % Change", "3 Years % Change"]
table_header = (
    "| Symbol | " + " | ".join(day_headers) + " | RSI (14) | EMA (14) | BB Upper | BB Lower |\n"
    + "|--------|" + "|".join(["-----------------" for _ in day_headers]) + "|----------|----------|----------|----------|"
)
table_header = ("Symbol," + ",".join(day_headers) + ",RSI (14),EMA (14),BB Upper,BB Lower")

for symbol in df_changes['symbol'].unique():
    sym_data = df_changes[df_changes['symbol'] == symbol].sort_values('date')
    df_changes_recent = sym_data.tail(1).copy()
    if  df_changes_recent["open"].values[0] == 0 or \
        df_changes_recent["close"] .values[0] == 0 or \
        df_changes_recent["close_7d"].values[0] == 0 or \
        df_changes_recent["close_1m"].values[0] == 0 or \
        df_changes_recent["close_3m"].values[0] == 0 or \
        df_changes_recent["close_6m"].values[0] == 0 or \
        df_changes_recent["close_1y"].values[0] == 0 or \
        df_changes_recent["close_3y"].values[0] == 0 :
        continue  # Skip symbols with zero open price
    df_changes_recent["1 Day % Change"] = ( df_changes_recent["close"] - df_changes_recent["open"] ) / df_changes_recent["open"] * 100
    df_changes_recent["7 Day % Change"] = ( df_changes_recent["close"] - df_changes_recent["close_7d"] ) / df_changes_recent["close_7d"] * 100
    df_changes_recent["30 Day % Change"] = ( df_changes_recent["close"] - df_changes_recent["close_1m"] ) / df_changes_recent["close_1m"] * 100
    df_changes_recent["90 Day % Change"] = ( df_changes_recent["close"] - df_changes_recent["close_3m"] ) / df_changes_recent["close_3m"] * 100
    df_changes_recent["180 Day % Change"] = ( df_changes_recent["close"] - df_changes_recent["close_6m"] ) / df_changes_recent["close_6m"] * 100
    df_changes_recent["1 Year % Change"] = ( df_changes_recent["close"] - df_changes_recent["close_1y"] ) / df_changes_recent["close_1y"] * 100
    df_changes_recent["3 Years % Change"] = ( df_changes_recent["close"] - df_changes_recent["close_3y"] ) / df_changes_recent["close_3y"] * 100

    pct_last10 = df_changes_recent

    # Most recent technical indicators
    close_prices = sym_data['close'].values
    try:
        rsi_val = round(talib.RSI(close_prices, timeperiod=14)[-1], 2)
        ema_val = round(talib.EMA(close_prices, timeperiod=14)[-1], 2)
        upper, _, lower = talib.BBANDS(close_prices, timeperiod=20)
        bb_up = round(upper[-1], 2)
        bb_lo = round(lower[-1], 2)
    except Exception:
        rsi_val = ema_val = bb_up = bb_lo = None
    
    df_changes_recent["rsi"] = rsi_val
    df_changes_recent["ema"] = ema_val
    df_changes_recent["bb_upper"] = bb_up
    df_changes_recent["bb_lower"] = bb_lo

#     indicator_rows.append(
# f'| {symbol} \
# | {df_changes_recent["1 Day % Change"].iloc[0].round(4)} \
# | {df_changes_recent["7 Day % Change"].iloc[0].round(4)} \
# | {df_changes_recent["30 Day % Change"].iloc[0].round(4)} \
# | {df_changes_recent["90 Day % Change"].iloc[0].round(4)} \
# | {df_changes_recent["180 Day % Change"].iloc[0].round(4)} \
# | {df_changes_recent["1 Year % Change"].iloc[0].round(4)} \
# | {df_changes_recent["3 Years % Change"].iloc[0].round(4)} \
# | {rsi_val} | {ema_val} | {bb_up} | {bb_lo} |'
#     )

    indicator_rows.append(
f'{symbol}\
,{df_changes_recent["1 Day % Change"].iloc[0].round(4)}\
,{df_changes_recent["7 Day % Change"].iloc[0].round(4)}\
,{df_changes_recent["30 Day % Change"].iloc[0].round(4)}\
,{df_changes_recent["90 Day % Change"].iloc[0].round(4)}\
,{df_changes_recent["180 Day % Change"].iloc[0].round(4)}\
,{df_changes_recent["1 Year % Change"].iloc[0].round(4)}\
,{df_changes_recent["3 Years % Change"].iloc[0].round(4)}\
,{rsi_val},{ema_val},{bb_up},{bb_lo}')

indicator_table = "\n".join([table_header] + indicator_rows)

# ------------------------------------------------------------------
# 3️⃣  Build the *editable* default prompt
# ------------------------------------------------------------------
default_prompt = f"""
You are a seasoned financial analyst specialized in Turkish mutual funds (fon).
Using the table below, recommend the **top 10 best performing fund symbol** to invest.
Respond **exactly** in the following format:

Recommended Symbol(s): <symbol>
Reason: <short, max 3 sentences justification>
Make sure to consider both short-term and long-term performance, as well as technical indicators like RSI, EMA, and Bollinger Bands.

Table of data in csv format:

{indicator_table}

Note: The percentages are % changes over the periods specified in table header.
The RSI, EMA, and Bollinger Bands are the most recent values.
"""
# ------------------------------------------------------------------
# 4️⃣  UI – allow the user to tweak the prompt
# ------------------------------------------------------------------
st.markdown("#### Ask LLM for Fund Selection")

# Optional: let the user pick which Ollama model and host to use
col1, col2 = st.columns(2)
with col1:
    ollama_preset = st.selectbox(
        "Ollama Host Configuration", 
        [
            "http://host.docker.internal:11434 (Docker Default)", 
            "http://localhost:11434 (Local Node)", 
            "Custom URL"
        ]
    )
    if ollama_preset == "Custom URL":
        ollama_host = st.text_input("Custom Ollama Host", value="http://192.168.1.X:11434")
    else:
        ollama_host = ollama_preset.split(" ")[0]

with col2:
    model_name = st.text_input("Ollama Model Name", value="gpt-oss:latest")

# Text area that shows the default prompt but is fully editable
user_prompt = st.text_area(
    "Prompt for LLM (you can edit the template if needed)",
    value=default_prompt,
    height=500
)

# ------------------------------------------------------------------
# 5️⃣  When the user clicks the button, send the (possibly edited)
#      prompt to the LLM
# ------------------------------------------------------------------
if st.button("Ask LLM for Fund Selection"):
    with st.spinner("LLM is analyzing…"):
        try:
            client = ollama.Client(host=ollama_host)
            response = client.chat(
                model=model_name,
                messages=[{"role": "user", "content": user_prompt}]
            )
            st.markdown("**LLM Analysis & Recommendation:**")
            st.write(response['message']['content'])
        except Exception as e:
            st.error(f"Ollama error: {e}")