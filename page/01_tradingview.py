import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from page.utils import read_table

symbol_attributes_df = pd.DataFrame()

# Turkish sorting function
def turkish_sort(x):
    import locale
    locale.setlocale(locale.LC_ALL, 'tr_TR.UTF-8')
    return locale.strxfrm(x)

df_fon_table = read_table("tefas_funds", parse_dates=None)
symbol_attributes_of_fon_table = [col for col in df_fon_table.columns if col.startswith('FundType_')]
symbol_attributes_list = [col.replace('FundType_', '') for col in symbol_attributes_of_fon_table]
symbol_attributes_list = sorted(symbol_attributes_list, key=turkish_sort)
symbol_attributes_df = pd.DataFrame({'Fon Unvan Türü': symbol_attributes_list})

config_file_path = "page/config.json"
def load_config():
    if os.path.exists(config_file_path):
        with open(config_file_path, "r") as file:
            config = json.load(file)
            return config

config = load_config()
chart_height = config["chart_height"] 

set_filtered_symbols = set()

with st.sidebar:
    with st.container():
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            show_favourites = st.checkbox("Favorilerim", key="Favorilerim")
        with row1_col2:
            show_portfolio = st.checkbox("Portföyüm", key="Portföyüm", value=True)

        selectable_attributes = st.dataframe(symbol_attributes_df, hide_index=True, on_select="rerun", selection_mode="multi-row")
        filtered_attributes = symbol_attributes_df.loc[selectable_attributes.selection.rows]

        if not filtered_attributes.empty or set_filtered_symbols:
            df_symbol_history_list = []

            if not filtered_attributes.empty:
                for filtered_attribute in filtered_attributes['Fon Unvan Türü']:
                    df_filtered_symbols = df_fon_table[df_fon_table[f'FundType_{filtered_attribute}'] == True]['symbol'].unique().tolist()
                    set_filtered_symbols.update(df_filtered_symbols)

        if show_favourites:
            if 'favourites' in st.session_state:
                set_filtered_symbols.update(st.session_state.favourites)

        if show_portfolio:
            if 'myportfolio' in st.session_state:
                myportfolio_summarized = (st.session_state.myportfolio
                                          .groupby('symbol', as_index=False)
                                          .apply(lambda df: pd.Series(
                                              {'net_quantity': df.loc[df['transaction_type'] == 'buy', 'quantity'].sum() - df.loc[
                                                  df['transaction_type'] == 'sell', 'quantity'].sum()}))
                                          .query('net_quantity != 0'))
                set_filtered_symbols.update(myportfolio_summarized['symbol'].unique().tolist())

        symbol_list = ','.join(f"'{s}'" for s in set_filtered_symbols)
        filter_cond = f"symbol IN ({symbol_list})"
        df_transformed = read_table('tefas_transformed', parse_dates=['date'], filter_condition=filter_cond)

# Filter and prepare data for the selected symbols
df_raw = df_transformed.copy()

if df_raw.empty:
    st.warning(f"No data available for symbols: {set_filtered_symbols}")
else:
    # Pivot the data to have symbols as columns and dates as rows
    df_pivot = df_raw.pivot(index='date', columns='symbol', values='close').reset_index()
    df_pivot['date'] = pd.to_datetime(df_pivot['date']).dt.strftime('%Y-%m-%d')
    df_pivot.sort_values('date', inplace=True)
    dates = df_pivot['date'].tolist()
    dates = [datetime.strptime(date, '%Y-%m-%d') for date in dates]

    start_date, end_date = st.slider(
        "",
        min_value=dates[0],
        max_value=dates[-1],
        value=(dates[0], dates[-1]),
        format="YYYY-MM-DD",
        key="date_range_slider",
        label_visibility="visible",
    )

    # Create tabs for different chart types
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📉 Lightweight Charts",
        "📊 Plotly",
        "📈 Altair",
        "📊 Echarts",
        "📋 Tablo"
    ])

    start_date_f = start_date.strftime('%Y-%m-%d')
    end_date_f = end_date.strftime('%Y-%m-%d')
    start_date_f_buffer = start_date - timedelta(days=15)
    start_date_f_buffer_str = start_date_f_buffer.strftime('%Y-%m-%d')
    date_range = pd.date_range(start=start_date_f_buffer, end=end_date)
    
    # Prepare data for each symbol
    symbols_data = {}
    for symbol in set_filtered_symbols:
        df_symbol = df_raw[df_raw['symbol'] == symbol][['date', 'close']].copy()
        df_symbol.rename(columns={'date': 'time'}, inplace=True)
        df_symbol.set_index('time', inplace=True)
        df_symbol = df_symbol.reindex(date_range).ffill().reset_index()
        # df_symbol = df_symbol.reindex(date_range).bfill().reset_index()
        df_symbol.rename(columns={'index': 'time'}, inplace=True)
        df_symbol['time'] = df_symbol['time'].dt.strftime('%Y-%m-%d')
        df_symbol = df_symbol[(df_symbol['time'] >= start_date_f) & (df_symbol['time'] <= end_date_f)]

        if df_symbol.empty or df_symbol['time'].min() > start_date_f:
            df_symbol = pd.concat([pd.DataFrame({'time': [start_date_f], 'close': [0]}), df_symbol])

        base_value = df_symbol['close'].iloc[0] if not df_symbol.empty else 0
        df_symbol['cumulative_gain'] = ((df_symbol['close'] - base_value) / base_value) * 100 if base_value != 0 else 0
        
        # Replace NaN values with 0 to avoid JSON serialization issues
        df_symbol['cumulative_gain'] = df_symbol['cumulative_gain'].fillna(0)
        df_symbol['close'] = df_symbol['close'].fillna(0)
        
        symbols_data[symbol] = df_symbol[['time', 'cumulative_gain']].copy()

    # Tab 1: Streamlit-Lightweight-Charts Implementation
    with tab1:
        try:
            from streamlit_lightweight_charts import renderLightweightCharts
            
            colors = ['#2962FF', '#FF6D00', '#00C853', '#D50000', '#6200EA']
            series_list = []
            
            for idx, (symbol, df_data) in enumerate(symbols_data.items()):
                color = colors[idx % len(colors)]
                data_points = [
                    {"time": row['time'], "value": row['cumulative_gain']}
                    for _, row in df_data.iterrows()
                ]
                series_list.append({
                    "type": 'Line',
                    "data": data_points,
                    "options": {
                        "color": color,
                        "lineWidth": 2,
                        "title": symbol
                    }
                })
            
            chartOptions = {
                "layout": {
                    "background": {"color": "#ffffff"},
                    "textColor": "#333"
                },
                "grid": {
                    "vertLines": {"color": "#e0e0e0"},
                    "horzLines": {"color": "#e0e0e0"}
                },
                "height": chart_height,
            }
            
            renderLightweightCharts([{"chart": chartOptions, "series": series_list}], 'multiple')
            
        except ImportError:
            st.error("streamlit-lightweight-charts kütüphanesi yüklü değil. Lütfen 'pip install streamlit-lightweight-charts' komutunu çalıştırın.")

    # Tab 2: Plotly Implementation
    with tab2:
        try:
            import plotly.graph_objects as go
            
            fig = go.Figure()
            colors = ['#2962FF', '#FF6D00', '#00C853', '#D50000', '#6200EA', '#AA00FF', '#0091EA', '#00BFA5']
            
            for idx, (symbol, df_data) in enumerate(symbols_data.items()):
                color = colors[idx % len(colors)]
                fig.add_trace(go.Scatter(
                    x=df_data['time'],
                    y=df_data['cumulative_gain'],
                    mode='lines',
                    name=symbol,
                    line=dict(color=color, width=2),
                    hovertemplate='%{y:.2f}%<extra></extra>'
                ))
            
            fig.update_layout(
                height=chart_height,
                hovermode='x unified',
                xaxis_title='Tarih',
                yaxis_title='Kümülatif Kazanç (%)',
                legend=dict(
                    orientation="v",
                    yanchor="top",
                    y=1,
                    xanchor="left",
                    x=1.02
                ),
                plot_bgcolor='white',
                xaxis=dict(showgrid=True, gridcolor='#e0e0e0'),
                yaxis=dict(showgrid=True, gridcolor='#e0e0e0')
            )
            
            st.plotly_chart(fig)
        except ImportError:
            st.error("Plotly kütüphanesi yüklü değil. Lütfen 'pip install plotly' komutunu çalıştırın.")

    # Tab 3: Altair Implementation
    with tab3:
        try:
            import altair as alt
            
            # Combine all data into a single dataframe for Altair
            combined_data = []
            for symbol, df_data in symbols_data.items():
                df_temp = df_data.copy()
                df_temp['symbol'] = symbol
                combined_data.append(df_temp)
            
            df_combined = pd.concat(combined_data, ignore_index=True)
            df_combined['time'] = pd.to_datetime(df_combined['time'])
            
            chart = alt.Chart(df_combined).mark_line(point=False).encode(
                x=alt.X('time:T', title='Tarih', axis=alt.Axis(format='%Y-%m-%d')),
                y=alt.Y('cumulative_gain:Q', title='Kümülatif Kazanç (%)'),
                color=alt.Color('symbol:N', 
                                legend=alt.Legend(title='Sembol'),
                                scale=alt.Scale(scheme='category10')),
                tooltip=[
                    alt.Tooltip('time:T', title='Tarih', format='%Y-%m-%d'),
                    alt.Tooltip('symbol:N', title='Sembol'),
                    alt.Tooltip('cumulative_gain:Q', title='Kazanç (%)', format='.2f')
                ]
            ).properties(
                width='container',
                height=chart_height,
            ).interactive()
            
            st.altair_chart(chart)
            
        except ImportError:
            st.error("altair kütüphanesi yüklü değil. Lütfen 'pip install altair' komutunu çalıştırın.")

    # Tab 4: Streamlit-Echarts Implementation
    with tab4:
        try:
            from streamlit_echarts import st_echarts
            
            colors = ['#2962FF', '#FF6D00', '#00C853', '#D50000', '#6200EA', '#AA00FF', '#0091EA', '#00BFA5']
            
            # Get all unique dates for x-axis
            all_dates = sorted(set(date for df_data in symbols_data.values() for date in df_data['time'].tolist()))
            
            series_list = []
            for idx, (symbol, df_data) in enumerate(symbols_data.items()):
                color = colors[idx % len(colors)]
                data_values = df_data['cumulative_gain'].tolist()
                
                series_list.append({
                    "name": symbol,
                    "type": "line",
                    "data": data_values,
                    "smooth": False,
                    "lineStyle": {"width": 2, "color": color},
                    "itemStyle": {"color": color},
                    "showSymbol": False
                })
            
            option = {
                "title": {"text": "Fon Karşılaştırma", "left": "center"},
                "tooltip": {
                    "trigger": "axis",
                    "axisPointer": {"type": "cross"}
                },
                "legend": {
                    "data": list(symbols_data.keys()),
                    "top": 30,
                    "type": "scroll"
                },
                "grid": {
                    "left": "3%",
                    "right": "4%",
                    "bottom": "3%",
                    "top": 80,
                    "containLabel": True
                },
                "xAxis": {
                    "type": "category",
                    "data": all_dates,
                    "boundaryGap": False,
                    "axisLabel": {"rotate": 45}
                },
                "yAxis": {
                    "type": "value",
                    "name": "Kümülatif Kazanç (%)",
                    "axisLabel": {"formatter": "{value}%"}
                },
                "series": series_list,
                "dataZoom": [
                    {"type": "inside", "start": 0, "end": 100},
                    {"start": 0, "end": 100}
                ]
            }
            
            st_echarts(options=option, height="{}px".format(chart_height))
            
        except ImportError:
            st.error("streamlit-echarts kütüphanesi yüklü değil. Lütfen 'pip install streamlit-echarts' komutunu çalıştırın.")

    # Tab 5: Data Table
    with tab5:
        df_show = df_pivot[(df_pivot['date'] >= start_date_f) & (df_pivot['date'] <= end_date_f)].sort_values(by="date", ascending=False).copy()
        st.dataframe(df_show, hide_index=True, height=800, selection_mode=["multi-row", "multi-column"])