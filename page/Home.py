import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from page.utils import read_table

st.title("Home Page")

df_fon_table = read_table("tefas_funds", parse_dates=None)

default_recent_date = datetime.today().date()
default_prev_date = datetime.today().date() - pd.Timedelta(days=7)

st.subheader("Select Dates for Comparison")

col1, col2 = st.columns(2)

with col1:
    selected_recent_date = st.date_input("Date To", value=default_recent_date, key="recent_date" )
with col2:
    selected_prev_date = st.date_input("Date From", value=default_prev_date)

recent_date = pd.to_datetime(selected_recent_date)
prev_date = pd.to_datetime(selected_prev_date)

df_transformed = read_table('tefas_transformed', parse_dates=['date'], filter_condition=f" date BETWEEN '{prev_date.date() - pd.Timedelta(days=7) }' AND '{recent_date.date()}' ")

@st.cache_data
def fetch_todays_data(recent_date, prev_date):
    summary_recent = pd.DataFrame(columns=['Fon Unvan Türü', 'symbol', 'market_cap'])  # Initialize as empty DataFrame

    recent_date_adj = df_transformed[df_transformed['date'] <= recent_date]['date'].max()
    # Separate data for recent_date and prev_date
    df_transformed_recent = df_transformed[df_transformed['date'] == recent_date_adj]
    df_transformed_recent = pd.merge(df_transformed_recent, df_fon_table, on='symbol', how='inner')
    
    # Adjust prev_date to the latest date in df_transformed that is <= the user‑selected prev_date
    prev_date_adj = df_transformed[df_transformed['date'] <= prev_date]['date'].max()
    # Use the adjusted date to filter the previous period data
    df_transformed_prev = df_transformed[df_transformed['date'] == prev_date_adj]
    df_transformed_prev = pd.merge(df_transformed_prev, df_fon_table, on='symbol', how='inner')

    # Extract symbol attributes
    symbol_attributes_of_fon_table = [col for col in df_fon_table.columns if col.startswith('FundType_')]
    symbol_attributes_list = [col.replace('FundType_', '') for col in symbol_attributes_of_fon_table]
    
    data_fon_turu_summary = []
    for attribute in symbol_attributes_list:  # Calculate totals and deltas for each attribute
        attribute_col = 'FundType_' + attribute
        
        if not attribute_col in df_transformed_recent.columns: 
            continue 
        if not attribute_col in df_transformed_prev.columns: 
            continue

        filtered_recent = df_transformed_recent[df_transformed_recent[attribute_col] == True].copy()
        filtered_recent.loc[:, "Fon Unvan Türü"] = attribute
        filtered_prev = df_transformed_prev[df_transformed_prev[attribute_col] == True]
        amount_t = filtered_recent['market_cap'].sum()
        amount_t_minus_1 = filtered_prev['market_cap'].sum()

        if amount_t_minus_1 == 0:
            continue

        delta = amount_t - amount_t_minus_1
        delta_pct = (amount_t - amount_t_minus_1) / amount_t_minus_1
        indicator = '✅' if delta > 0 else '🔻' if delta < 0 else '➡️'
        recent_date_str = datetime.strftime(recent_date, "%Y-%m-%d")
        prev_date_str = datetime.strftime(prev_date, "%Y-%m-%d")

        data_fon_turu_summary.append({ # Add to summary data
            'Fon Unvan Türü': attribute,
            recent_date_str: round(amount_t, 0),
            prev_date_str: round(amount_t_minus_1, 0),
            'Δ': round(delta, 0),
            'Δ %': round(delta_pct, 5),
            '': indicator
        })

        if not summary_recent.empty:
            summary_recent = pd.concat([summary_recent, filtered_recent.groupby(['Fon Unvan Türü', 'symbol'])['market_cap'].sum().reset_index()])
        else:
            summary_recent = filtered_recent.groupby(['Fon Unvan Türü', 'symbol'])['market_cap'].sum().reset_index()

    return summary_recent, data_fon_turu_summary, recent_date, prev_date

summary_recent, data_fon_turu_summary, recent_date, prev_date = fetch_todays_data(recent_date, prev_date)

dataframe_height = (len(data_fon_turu_summary) + 1) * 35 + 2

col1, col2, col3 = st.columns([6, 1, 7])
with col1:
    with st.container():
        df_summary = pd.DataFrame(data_fon_turu_summary)
        styled_df = df_summary.style
        recent_date_str = datetime.strftime(recent_date, "%Y-%m-%d")
        prev_date_str = datetime.strftime(prev_date, "%Y-%m-%d")
        styled_df = styled_df.format({f'{recent_date_str}': '₺ {:,.0f}', 
                                      f'{prev_date_str}': '₺ {:,.0f}', 
                                      f'Δ': '₺ {:,.0f}' , 
                                      f'Δ %': '% {:,.4f}'})
        st.dataframe(styled_df, hide_index=True, height=dataframe_height)

with col2:
    with st.container():
# USD TRY RATES
        df_fx = read_table('usd_try_rates', parse_dates=['date'])

        df_fx_recent = df_fx[df_fx['date'] <= recent_date].sort_values('date').tail(1)
        if not df_fx_recent.empty:
            usd_try_rate_recent = df_fx_recent['close'].iloc[0]
            usd_recent_ts = pd.to_datetime(df_fx_recent['date'].iloc[0])
            usd_recent_date_str = usd_recent_ts.strftime('%Y-%m-%d')
        else:
            usd_try_rate_recent = None
            usd_recent_ts = None
            usd_recent_date_str = None

        # previous 2 and 3 points relative to the usd_recent_ts (if available)
        if usd_recent_ts is not None:
            df_fx_recent_1 = df_fx[df_fx['date'] <= usd_recent_ts].sort_values('date').tail(2)
            if not df_fx_recent_1.empty:
                usd_try_rate_recent_1 = df_fx_recent_1['close'].iloc[0]
                usd_recent_date1_str = pd.to_datetime(df_fx_recent_1['date'].iloc[0]).strftime('%Y-%m-%d')
            else:
                usd_try_rate_recent_1 = None
                usd_recent_date1_str = None

            df_fx_recent_2 = df_fx[df_fx['date'] <= usd_recent_ts].sort_values('date').tail(3)
            if not df_fx_recent_2.empty:
                usd_try_rate_recent_2 = df_fx_recent_2['close'].iloc[0]
                usd_recent_date2_str = pd.to_datetime(df_fx_recent_2['date'].iloc[0]).strftime('%Y-%m-%d')
            else:
                usd_try_rate_recent_2 = None
                usd_recent_date2_str = None
        else:
            usd_try_rate_recent_1 = usd_try_rate_recent_2 = None
            usd_recent_date1_str = usd_recent_date2_str = None
         
        # Replace st.rows with nested st.columns for three rows
        row1, row2, row3 = st.columns(1), st.columns(1), st.columns(1)
        
        with row1[0]:
            if usd_try_rate_recent is not None and usd_try_rate_recent_1 is not None:
                delta = usd_try_rate_recent - usd_try_rate_recent_1
                st.metric(label=f"{usd_recent_date_str} USD:", value=f"{usd_try_rate_recent:,.2f}", delta=f"{delta:,.4f}")
            else:
                st.metric(label="Latest USD:", value="N/A")
        with row2[0]:
            if usd_try_rate_recent_1 is not None and usd_try_rate_recent_2 is not None:
                delta = usd_try_rate_recent_1 - usd_try_rate_recent_2
                st.metric(label=f"{usd_recent_date1_str} USD:", value=f"{usd_try_rate_recent_1:,.2f}", delta=f"{delta:,.4f}")
            else:
                st.metric(label="Previous USD:", value="N/A")
        with row3[0]:
            if usd_try_rate_recent_2 is not None:
                st.metric(label=f"{usd_recent_date2_str} USD:", value=f"{usd_try_rate_recent_2:,.2f}")
            else:
                st.metric(label="Earlier USD:", value="N/A")

# GOLD RATES
        df_gold = read_table('gold_try_rates', parse_dates=['date'])

        df_gold_recent = df_gold[df_gold['date'] <= recent_date].sort_values('date').tail(1)
        if not df_gold_recent.empty:
            usd_try_rate_recent = df_gold_recent['close'].iloc[0]
            usd_recent_ts = pd.to_datetime(df_gold_recent['date'].iloc[0])
            usd_recent_date_str = usd_recent_ts.strftime('%Y-%m-%d')
        else:
            usd_try_rate_recent = None
            usd_recent_ts = None
            usd_recent_date_str = None

        # previous 2 and 3 points relative to the usd_recent_ts (if available)
        if usd_recent_ts is not None:
            df_gold_recent_1 = df_gold[df_gold['date'] <= usd_recent_ts].sort_values('date').tail(2)
            if not df_gold_recent_1.empty:
                usd_try_rate_recent_1 = df_gold_recent_1['close'].iloc[0]
                usd_recent_date1_str = pd.to_datetime(df_gold_recent_1['date'].iloc[0]).strftime('%Y-%m-%d')
            else:
                usd_try_rate_recent_1 = None
                usd_recent_date1_str = None

            df_gold_recent_2 = df_gold[df_gold['date'] <= usd_recent_ts].sort_values('date').tail(3)
            if not df_gold_recent_2.empty:
                usd_try_rate_recent_2 = df_gold_recent_2['close'].iloc[0]
                usd_recent_date2_str = pd.to_datetime(df_gold_recent_2['date'].iloc[0]).strftime('%Y-%m-%d')
            else:
                usd_try_rate_recent_2 = None
                usd_recent_date2_str = None
        else:
            usd_try_rate_recent_1 = usd_try_rate_recent_2 = None
            usd_recent_date1_str = usd_recent_date2_str = None
         
        # Replace st.rows with nested st.columns for three rows
        row4, row5, row6 = st.columns(1), st.columns(1), st.columns(1)
        
        with row4[0]:
            if usd_try_rate_recent is not None and usd_try_rate_recent_1 is not None:
                delta = usd_try_rate_recent - usd_try_rate_recent_1
                st.metric(label=f"{usd_recent_date_str} GOLD:", value=f"{usd_try_rate_recent:,.2f}", delta=f"{delta:,.4f}")
            else:
                st.metric(label="Latest GOLD:", value="N/A")
        with row5[0]:
            if usd_try_rate_recent_1 is not None and usd_try_rate_recent_2 is not None:
                delta = usd_try_rate_recent_1 - usd_try_rate_recent_2
                st.metric(label=f"{usd_recent_date1_str} GOLD:", value=f"{usd_try_rate_recent_1:,.2f}", delta=f"{delta:,.4f}")
            else:
                st.metric(label="Previous GOLD:", value="N/A")
        with row6[0]:
            if usd_try_rate_recent_2 is not None:
                st.metric(label=f"{usd_recent_date2_str} GOLD:", value=f"{usd_try_rate_recent_2:,.2f}")
            else:
                st.metric(label="Earlier GOLD:", value="N/A")

with col3:
        treemap_data = pd.DataFrame({
             'names': summary_recent['symbol'],
             'parents': summary_recent['Fon Unvan Türü'],
             'values': summary_recent['market_cap']
         })
 
        treemap_data = treemap_data[treemap_data['values'] > 0]  # Remove negative values
 
        fig = px.treemap(
             treemap_data,
             path=['parents', 'names'],  # Path to the names
             values='values',
             color='values',  # Color by the values to show increase or decrease
             color_continuous_scale='RdYlGn',  # Red for negative, green for positive
             # title="Market Cap Treemap",
             height=dataframe_height, 
             )
 
        st.plotly_chart(fig) # Display the treemap next to the DataFrame
