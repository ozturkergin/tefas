import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from prophet import Prophet
import logging
from page.utils import read_table

# Suppress cmdstanpy logs
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)

# Initialize the set properly
if 'set_filtered_symbols' not in st.session_state:
    st.session_state.set_filtered_symbols = set()

set_filtered_symbols = st.session_state.set_filtered_symbols

@st.cache_data
def fetch_data():
    if 'df_fon_table' in st.session_state:
        df_fon_table = st.session_state.df_fon_table
    else:
        df_fon_table = read_table("tefas_funds", parse_dates=None)
        st.session_state.df_fon_table = df_fon_table

    return df_fon_table

df_fon_table = fetch_data()

unique_symbols = sorted(df_fon_table['symbol'].unique().tolist())

st.title("Forecasting")

# Multiselect with unique symbols
selected_symbols = st.multiselect(
    'Fon:',
    unique_symbols,
    default=None,
    key='selected_symbols'
)

with st.sidebar:
    with st.container():
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            show_favourites = st.checkbox("Favorilerim", value=False)
        with row1_col2:
            show_portfolio = st.checkbox("Portföyüm", value=True)
            
        prompt_number_of_days_to_predict = st.number_input("Gelecek Kaç Gözlem Tahminlenmeli:", min_value=0, step=1, value=30)

        # Clear the set and rebuild it
        set_filtered_symbols.clear()
        set_filtered_symbols.update(selected_symbols)
        FAVOURITES_FILE = f"data/favourites_{st.session_state["remembered_user"]}.csv"
        PORTFOLIO_FILE = f"data/myportfolio_{st.session_state["remembered_user"]}.csv"

        if show_favourites:
            if 'favourites' in st.session_state:
                set_filtered_symbols.update(st.session_state.favourites)
            elif os.path.exists(FAVOURITES_FILE):
                fav_symbols = pd.read_csv(FAVOURITES_FILE)['symbol'].tolist()
                set_filtered_symbols.update(fav_symbols)
            
        if show_portfolio:
            if 'myportfolio' in st.session_state:
                myportfolio = st.session_state.myportfolio.copy()
            elif os.path.exists(PORTFOLIO_FILE):
                myportfolio = pd.read_csv(PORTFOLIO_FILE, parse_dates=['date'])
                myportfolio['quantity'] = pd.to_numeric(myportfolio['quantity'], errors='coerce').fillna(0).astype(int)
                myportfolio = myportfolio[myportfolio.quantity != 0]
            else:
                myportfolio = pd.DataFrame()
            
            if not myportfolio.empty:
                myportfolio_summarized = ( myportfolio
                .groupby('symbol', as_index=False)                              
                .apply(lambda df: pd.Series({'net_quantity': df.loc[df['transaction_type'] == 'buy', 'quantity'].sum() - df.loc[df['transaction_type'] == 'sell', 'quantity'].sum()}))
                .query('net_quantity != 0') )  # Keep only symbols with non-zero net quantity  
                set_filtered_symbols.update(myportfolio_summarized['symbol'].unique().tolist())
        
        if set_filtered_symbols:
            symbol_list = ','.join(f"'{s}'" for s in set_filtered_symbols)
            filter_cond = f"symbol IN ({symbol_list})"
            df_transformed = read_table('tefas_transformed', parse_dates=['date'], filter_condition=filter_cond)
            df_merged = pd.merge(df_transformed, df_fon_table, on='symbol', how='inner')
            df_merged['date'] = pd.to_datetime(df_merged['date'], errors='coerce')
        else:
            st.warning("Lütfen en az bir fon seçiniz.")
            st.stop()

for symbol in set_filtered_symbols:
    data = df_merged[df_merged['symbol'] == symbol].copy()
    data.set_index('date', inplace=True)
    
    complete_date_range = pd.date_range(start=data.index.min(), end=data.index.max(), freq='D')

    data = data.reindex(complete_date_range)
    data['close'] = pd.to_numeric(data['close'], errors='coerce')
    data = data.ffill().reset_index()
    data.rename(columns={'index': 'date'}, inplace=True)

    title = data.iloc[0]['title']
    data = data[['date', 'close']].copy()
    data.rename(columns={'date': 'ds', 'close': 'y'}, inplace=True)

    # Create Prophet model with sampling disabled to reduce logs
    model = Prophet(
        yearly_seasonality="auto",
        weekly_seasonality="auto",
        daily_seasonality="auto",
        mcmc_samples=0,  # Disable MCMC sampling to reduce verbose logging
        interval_width=0.8  # Confidence interval width
    )
    
    model.fit(data)

    future = model.make_future_dataframe(periods=prompt_number_of_days_to_predict)    # Prediction with x days into the future
    forecast = model.predict(future)

    future_x_days = forecast[['ds', 'yhat']].tail(prompt_number_of_days_to_predict)    # Select the last x days of predictions for display
    future_x_days.rename(columns={'ds': 'Date', 'yhat': 'Predicted Close'}, inplace=True)

    last_actual_price = data['y'].iloc[-1]    # Calculate the percentage change between the last actual close and the predicted latest close
    predicted_latest_price = future_x_days['Predicted Close'].iloc[-1]
    percentage_change = ((predicted_latest_price - last_actual_price) / last_actual_price) * 100

    with st.expander(f"{symbol} - {title}", expanded=True):
        fig = go.Figure()        # Create Plotly figure
        fig.add_trace(go.Scatter(x=data['ds'], y=data['y'], mode='lines', name='Past Close'))        # Add historical data
        fig.add_trace(go.Scatter(x=forecast['ds'], y=forecast['yhat'], mode='lines', name='Full Prediction', line=dict(color='blue', dash='dash')))        # Add full prediction range in a single color

        # Overlay final x days in a different color
        fig.add_trace(go.Scatter(x=forecast['ds'][-prompt_number_of_days_to_predict:], y=forecast['yhat'][-prompt_number_of_days_to_predict:], mode='lines', name=f'{prompt_number_of_days_to_predict}-Day Future Prediction', line=dict(color='red')))
        
        # Update layout for clarity
        fig.update_layout(
            title=f'Tahmin: {symbol} - {title}',
            xaxis_title='Date',
            yaxis_title='Close Price',
            xaxis=dict(rangeslider=dict(visible=True), type="date")
        )
        col1, col2, col3 = st.columns([2, 2, 8])

        with col1:            # Display percentage change in a card
            st.metric(
                label=f"{prompt_number_of_days_to_predict}-Günlük Tahmin: {symbol}",
                value=f"{percentage_change:.2f}%",
                delta=round(percentage_change, 2),
                delta_color="normal"
            )
        with col2:            # Display the future prediction data in a dataframe
            future_x_days.sort_values(by="Date", ascending=False, inplace=True)
            future_x_days['Date'] = future_x_days['Date'].dt.strftime('%Y-%m-%d')
            st.dataframe(future_x_days, hide_index=True)
        with col3:            # Display the chart in Streamlit
            st.plotly_chart(fig)
