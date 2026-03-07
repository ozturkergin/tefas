import streamlit as st
import pandas as pd
import os
import concurrent.futures
import seaborn as sns
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from page.utils import read_table

st.subheader("Portföy Analiz")
col1, col2, col3, col4, col5, col6, col7, col8, col9 = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 1])
# Define a default value for currency
currency = '₺'  # Default to TRY

with col8: 
    subcol1, subcol2, subcol3, subcol4 = st.columns([1,1,1,1])
    if subcol2.button("USD"):
        st.session_state["USD"] = True
        st.session_state["GOLD"] = False
        st.session_state["TRY"] = False
        currency = '$'
    if subcol3.button("GOLD"):
        st.session_state["GOLD"] = True
        st.session_state["USD"] = False
        st.session_state["TRY"] = False
        currency = 'gr'
    if subcol4.button("TRY"):
        st.session_state["TRY"] = True
        st.session_state["USD"] = False
        st.session_state["GOLD"] = False
        currency = '₺'

    # Ensure currency is set correctly based on session state
    if st.session_state.get("TRY", False):
        currency = '₺'
    elif st.session_state.get("USD", False):
        currency = '$'
    elif st.session_state.get("GOLD", False):
        currency = 'gr'

PORTFOLIO_FILE = f"data/myportfolio_{st.session_state["remembered_user"]}.csv"

if 'myportfolio' in st.session_state:
    myportfolio = st.session_state.myportfolio.copy()
elif os.path.exists(PORTFOLIO_FILE):
    myportfolio = pd.read_csv(PORTFOLIO_FILE, parse_dates=['date'])
    myportfolio['quantity'] = pd.to_numeric(myportfolio['quantity'], errors='coerce').fillna(0).astype(int)
    myportfolio = myportfolio[myportfolio.quantity != 0]
    
    set_date = st.session_state.get("set_date")
    if set_date:
        myportfolio = myportfolio[myportfolio['date'].dt.date <= set_date]
else:
    myportfolio = pd.DataFrame(columns=['symbol', 'transaction_type', 'quantity', 'date'])

use_postgres = st.session_state.get("use_postgres", True)
if use_postgres:
    set_date = st.session_state.get("set_date")
    date_filter = ""
    if set_date:
        date_filter = f"date <= '{set_date.strftime('%Y-%m-%d')}'"

    df_fx = read_table('usd_try_rates', parse_dates=['date'], filter_condition=date_filter if date_filter else None)
    df_fx.rename(columns={'close': 'USD'}, inplace=True)
    full_date_range = pd.date_range(start=df_fx['date'].min(), end=df_fx['date'].max())
    df_fx = df_fx.set_index('date').reindex(full_date_range).rename_axis('date').reset_index()
    df_fx['USD'] = df_fx['USD'].fillna(method='ffill')

    df_gold = read_table('gold_try_rates', parse_dates=['date'], filter_condition=date_filter if date_filter else None)
    df_gold.rename(columns={'close': 'GOLD'}, inplace=True)
    full_date_range = pd.date_range(start=df_gold['date'].min(), end=df_gold['date'].max())
    df_gold = df_gold.set_index('date').reindex(full_date_range).rename_axis('date').reset_index()
    df_gold['GOLD'] = df_gold['GOLD'].fillna(method='ffill')

    symbols = myportfolio['symbol'].dropna().unique()
    symbol_list = ','.join(f"'{s}'" for s in symbols)
    filter_cond = f"symbol IN ({symbol_list})"
    if date_filter:
        filter_cond += f" AND {date_filter}"
    df_transformed = read_table('tefas_transformed', parse_dates=['date'], filter_condition=filter_cond)
    df_transformed = pd.merge(df_transformed, df_fx[['date', 'USD']], on=['date'], how='left')
    df_transformed = pd.merge(df_transformed, df_gold[['date', 'GOLD']], on=['date'], how='left')
    
    if st.session_state.get("USD", False):
        df_transformed['close'] = df_transformed['close'] / df_transformed['USD']
    elif st.session_state.get("GOLD", False):
        df_transformed['close'] = ( ( df_transformed['close'] / df_transformed['USD'] ) * 31.1035 ) / df_transformed['GOLD'] 
    else:
        df_transformed['close'] = df_transformed['close'] 

    if 'df_fon_table' in st.session_state :
        df_fon_table = st.session_state.df_fon_table 
    else : 
        df_fon_table = read_table('tefas_funds', parse_dates=None)
        st.session_state.df_fon_table = df_fon_table

# Load portfolio data or create an empty DataFrame
def load_portfolio():
    merged_df = pd.merge(myportfolio, df_transformed[['symbol', 'date', 'close']], on=['symbol', 'date'], how='left')
    merged_df.rename(columns={'close': 'price'}, inplace=True)
    return merged_df

# Load the portfolio data
df_portfolio = load_portfolio()

# Stop if the portfolio is empty
if df_portfolio.empty:
    st.stop()

# Create a summary dataframe
df_summary = pd.DataFrame(columns=['Count', 'Date', 'Fon', 'Unvan', 'Miktar', 'Maliyet', 'Gider', 'Fiyat', 'Tutar', 'Stopaj', 'Gün', '1d Δ', '1d Δ %', 'Δ', 'Başarı Δ', 'Artı Gün %', 'RSI'])

df_portfolio['date'] = pd.to_datetime(df_portfolio['date'], errors='coerce')
df_portfolio = df_portfolio[df_portfolio['symbol'] != ""].sort_values(by=['symbol', 'date'])

def color_gradient(val, column_name):
    if pd.isna(val) or pd.isnull(val):
        return ''
    ranks = df_summary[column_name].rank(method='min')
    max_rank = ranks.max()
    try:
        current_rank = ranks[df_summary[column_name] == val].iloc[0]
    except IndexError:
        return ''
    norm_val = (current_rank - 1) / max_rank
    norm_val = max(0, min(1, norm_val))
    color = sns.color_palette("RdYlGn", as_cmap=True)(norm_val)
    return f'background-color: rgba{tuple(int(c * 255) for c in color[:3])}; font-weight: bold; color: black;'

def RSI_gradient(val):
    if pd.isna(val) or pd.isnull(val):
        return ''
    if val < 40:
        norm_val = 1 - ((val - 40) / 30)
        color = sns.color_palette("RdYlGn", as_cmap=True)(norm_val)
        return f'background-color: rgba{tuple(int(c * 255) for c in color[:3])}; color: black; font-weight: bold;'
    elif val > 70:
        return 'background-color: darkred; color: black; font-weight: bold;'
    else:
        norm_val = 1 - ((val - 40) / 30)
        color = sns.color_palette("RdYlGn", as_cmap=True)(norm_val)
        return f'background-color: rgba{tuple(int(c * 255) for c in color[:3])}; color: black; font-weight: bold;'

# Function to process each symbol
def process_symbol(symbol, count):
    total_quantity = 0
    total_value = 0
    avg_buy_price = 0
    weighted_daily_gain = 0
    total_days = 0
    avg_days = 0
    total_quantity_bought = 0
    quantity_remained = 0
    symbol_amount = 0
    d1_percentage_change = 0
    percentage_change = 0
    annual_gain = 0
    d1_recent_price = 0
    most_recent_rsi = 0
    tax_amount = 0
    positive_days = 0  # Counter for positive price gain days
    first_buy_date = None  # Store the first buying date

    count_index = count * -1 
    recent_data = df_transformed[df_transformed['symbol'] == symbol].sort_values('date')

    if recent_data.empty:
        return None

    try:
        most_recent_price = recent_data.iloc[count_index]['close']
    except IndexError:
        return None

    try:
        d1_recent_price = recent_data.iloc[count_index-1]['close']
    except IndexError:
        d1_recent_price = most_recent_price

    most_recent_date = recent_data.iloc[count_index]['date']
    most_recent_rsi = recent_data.iloc[count_index]['RSI_14']

    symbol_data = df_portfolio[(df_portfolio['symbol'] == symbol) & (df_portfolio['date'] <= most_recent_date)].sort_values('date')

    for i, (idx, row) in enumerate(symbol_data.iterrows()):
        transaction_type = row['transaction_type']
        transaction_date = row['date']
        quantity = row['quantity']
        unit_price = df_transformed.loc[(df_transformed['symbol'] == symbol) & (df_transformed['date'] == transaction_date), 'close']
        symbol_title = df_fon_table.loc[df_fon_table['symbol'] == symbol, 'title']

        if not unit_price.empty:
            unit_price = unit_price.iloc[0]
        else:
            unit_price = 0

        quantity_remained = 0

        if ( most_recent_price - unit_price > 0 and transaction_type == 'buy' ):
            tax_amount += row['tax_ratio'] * quantity * ( most_recent_price - unit_price )
        elif ( most_recent_price - unit_price > 0 and transaction_type == 'sell' ):
            tax_amount -= row['tax_ratio'] * quantity * ( most_recent_price - unit_price )

        if transaction_type == 'buy':
            # Reset positive_days for a new buy transaction
            if first_buy_date is None:
                first_buy_date = transaction_date

            total_value += quantity * unit_price
            total_quantity += quantity
            total_quantity_bought += quantity
            avg_buy_price = total_value / total_quantity
            quantity_remained += quantity
            avg_days += (most_recent_date - transaction_date).days * quantity 

            for j in range(i + 1, len(symbol_data)):
                next_row = symbol_data.iloc[j]
                if next_row['transaction_type'] == 'sell':
                    sell_quantity = next_row['quantity']
                    sell_date = next_row['date']
                    sell_price = next_row['price']
                    days_held = (sell_date - transaction_date).days
                    if sell_quantity <= quantity_remained:
                        weighted_daily_gain += ((sell_price - unit_price) / unit_price * 100) / days_held * 365 * sell_quantity
                        quantity_remained -= sell_quantity
                        total_days += sell_quantity
                    else:
                        weighted_daily_gain += ((sell_price - unit_price) / unit_price * 100) / days_held * 365 * quantity
                        quantity_remained -= sell_quantity
                        total_days += quantity
                        break

            if quantity_remained > 0:
                days_held = (most_recent_date - transaction_date).days
                if unit_price not in (None, 0) and days_held not in (None, 0) and most_recent_price is not None:
                    weighted_daily_gain += ((most_recent_price - unit_price) / unit_price * 100) / days_held * 365 * quantity_remained
                total_days += quantity_remained

        elif transaction_type == 'sell':
            total_value -= quantity * avg_buy_price
            total_quantity -= quantity
            avg_days -= (most_recent_date - transaction_date).days * quantity 
            if total_quantity == 0:
                avg_buy_price = 0
            else:
                avg_buy_price = total_value / total_quantity

            # Reset positive_days if quantity_remained becomes zero
        if quantity_remained == 0:
            first_buy_date = None 

    # Count positive price gain days from the first buying date to the most recent date
    total_duration = 0 
    if first_buy_date is not None:
        price_data = recent_data[recent_data['date'] >= first_buy_date].sort_values('date')
        for j in range(1, len(price_data)):
            if price_data.iloc[j]['close'] > price_data.iloc[j - 1]['close']:
                positive_days += 1
        # Calculate total duration in days
        total_duration = (most_recent_date - first_buy_date).days

    if total_quantity > 0:
        try:
            percentage_change = ((most_recent_price - avg_buy_price) / avg_buy_price) * 100 if avg_buy_price != 0 and avg_buy_price is not None else 0
            symbol_amount = round(total_quantity * most_recent_price, 2)
        except Exception as e:
            st.error(f"Error calculating percentage change for {symbol}: {e}") 
            percentage_change = 0.0
            symbol_amount = 0.0

        annual_gain = weighted_daily_gain / total_days if total_days != 0 else 0
        avg_days = avg_days / total_quantity_bought if total_quantity_bought != 0 else 0
        if d1_recent_price not in (None, 0):
            d1_percentage_change = ((most_recent_price - d1_recent_price) / d1_recent_price) * 100
        else:
            d1_percentage_change = 0

        return {
            'Count' : count,
            'Date' : most_recent_date,
            'Fon': symbol,
            'Unvan': symbol_title.iloc[0] if not symbol_title.empty else "",
            'Miktar': total_quantity,
            'Maliyet': avg_buy_price,
            'Gider': round(total_value, 2),
            'Fiyat': most_recent_price,
            'Tutar': symbol_amount,
            'Stopaj': tax_amount,
            'Gün': avg_days,
            '1d Δ': (most_recent_price - d1_recent_price) * total_quantity,
            '1d Δ %': d1_percentage_change,
            'Δ': percentage_change,
            'Başarı Δ': round(annual_gain, 2),
            'Artı Gün %': round(positive_days / total_duration * 100 , 2) if total_duration > 0 else 0,
            'RSI': round(most_recent_rsi, 2),
        }

# Function to calculate daily portfolio value
def calculate_daily_portfolio():
    price_dates = sorted(df_transformed['date'].unique())
    start_date = df_portfolio['date'].min()
    set_date = st.session_state.get("set_date")
    end_date = pd.to_datetime(set_date if set_date else datetime.today().date())
    valid_dates = [d for d in price_dates if start_date <= d <= end_date]
    if not valid_dates:
        return pd.DataFrame()
    
    trx = df_portfolio[['date', 'symbol', 'transaction_type', 'quantity']].copy()
    trx['signed_quantity'] = trx['quantity'].where(trx['transaction_type'] == 'buy', -trx['quantity'])
    
    trx_daily = trx.groupby(['date', 'symbol'])['signed_quantity'].sum().reset_index()
    trx_pivot = trx_daily.pivot(index='date', columns='symbol', values='signed_quantity').fillna(0)
    trx_pivot = trx_pivot.reindex(valid_dates).fillna(0).cumsum()
    
    df_quantities = trx_pivot.reset_index().melt(id_vars='date', value_name='cum_quantity')
    df_daily = df_quantities.merge(df_transformed[['symbol', 'date', 'close']], on=['symbol', 'date'], how='left')
    df_daily['value'] = df_daily['cum_quantity'] * df_daily['close'].fillna(0)
    
    df_daily = df_daily.groupby('date')['value'].sum().reset_index()
    df_daily = df_daily.rename(columns={'date': 'Date', 'value': 'Total Portfolio Value'})
    df_daily['Total Portfolio Value'] = df_daily['Total Portfolio Value'].round(0)
    return df_daily

# Execute the process for each unique symbol in parallel
summary_rows = []
with concurrent.futures.ThreadPoolExecutor() as executor:
    for i in range(1, 6):
        future_to_symbol = {executor.submit(process_symbol, symbol, i): symbol for symbol in df_portfolio['symbol'].unique()}
        for future in concurrent.futures.as_completed(future_to_symbol):
            result = future.result()
            if result:
                summary_rows.append(result)

# Convert summary rows to DataFrame and display
if summary_rows:
    df_summary = pd.DataFrame(summary_rows).sort_values(by="Tutar", ascending=False)

    column_configuration = {
        "Count"      : st.column_config.NumberColumn("Count", help="Count", width="small"),
        "Date"       : st.column_config.DateColumn("Date", help="Date", width="small"),
        "Fon"        : st.column_config.LinkColumn("Fon", help="Fon Kodu", display_text=r"https://www\.tefas\.gov\.tr/FonAnaliz\.aspx\?FonKod=(.*)", width="small"),
        "Unvan"      : st.column_config.TextColumn("Unvan", help="Fonun Ünvanı", width="large"),
        "Miktar"     : st.column_config.NumberColumn("Miktar", help="Fon Adedi", width="small"),
        "Maliyet"    : st.column_config.NumberColumn("Maliyet", help="İşlemler sonucu birim maliyeti", width="small"),
        "Gider"      : st.column_config.NumberColumn("Gider", help="İşlemler sonucu gider", width="small"),
        "Fiyat"      : st.column_config.NumberColumn("Fiyat", help="Güncel Fiyat", width="small"),
        "Tutar"      : st.column_config.NumberColumn("Tutar", help="Güncel Tutar", width="small"),
        "Stopaj"     : st.column_config.NumberColumn("Stopaj", help="Stopaj Tutar", width="small"),
        "Gün"        : st.column_config.NumberColumn("Gün", help="Gün", width="small"),
        "1d Δ"       : st.column_config.NumberColumn("1d Δ", help="Günlük Getiri", width="small"),
        "1d Δ %"     : st.column_config.NumberColumn("1d Δ", help="Günlük fiyat değişim yüzdesi", width="small"),
        "Δ"          : st.column_config.NumberColumn("Δ", help="Güncel fiyat değişim yüzdesi", width="small"),
        "Başarı Δ"   : st.column_config.NumberColumn("Başarı Δ", help="Yıllıklandırılmış işlem getiri yüzdesi", width="small"),
        "Artı Gün %" : st.column_config.NumberColumn("Artı Gün %", help="Artış yaşanmış gün oranı", width="small"),
        "RSI"        : st.column_config.NumberColumn("RSI", help="RSI 14", width="small"),
    }
 
    recent_dates = df_summary['Date'].sort_values(ascending=False).unique()

    df_summary_metric = df_summary[df_summary['Count'] <= 1].copy()

    with col7:       
        if (
            not df_summary_metric.empty
            and 'Tutar' in df_summary_metric.columns
            and 'Başarı Δ' in df_summary_metric.columns
            and 'Gün' in df_summary_metric.columns
        ):
            numerator = (df_summary_metric['Başarı Δ'] * df_summary_metric['Tutar'] * df_summary_metric['Gün']).sum()
            denominator = (df_summary_metric['Tutar'] * df_summary_metric['Gün']).sum()
            weighted_perf = numerator / denominator if denominator != 0 else 0
            st.metric("Portföy Tutar ve Gün Ağırlıklı Ortalama Başarı Δ", f"% {weighted_perf:.2f}")
    with col6:
        if (
            not df_summary_metric.empty
            and 'Gider' in df_summary_metric.columns
            and 'Başarı Δ' in df_summary_metric.columns
            and 'Gün' in df_summary_metric.columns
        ):
            numerator2 = (df_summary_metric['Gün'] * df_summary_metric['Başarı Δ'] * df_summary_metric['Gider']).sum()
            denominator2 = (df_summary_metric['Gün'] * df_summary_metric['Gider']).sum()
            weighted_perf2 = numerator2 / denominator2 if denominator2 != 0 else 0
            st.metric("Portföy Gider Ağırlıklı Ortalama Başarı Δ", f"% {weighted_perf2:.2f}")
    with col5:
        if len(recent_dates) > 4:
            recent_date = recent_dates[4].strftime('%Y-%m-%d')
            total_portfoy_5 = df_summary.loc[df_summary['Count'] == 5, 'Tutar'].sum() - df_summary.loc[df_summary['Count'] == 5, 'Stopaj'].sum()
            st.metric(label=f"{recent_date} Portföy:", value=f"{total_portfoy_5:,.0f} {currency}")
    with col4:
        if len(recent_dates) > 3:
            recent_date = recent_dates[3].strftime('%Y-%m-%d')
            total_portfoy_4 = df_summary.loc[df_summary['Count'] == 4, 'Tutar'].sum() - df_summary.loc[df_summary['Count'] == 4, 'Stopaj'].sum()
            delta = total_portfoy_4 - total_portfoy_5 
            st.metric(label=f"{recent_date} Portföy:", value=f"{total_portfoy_4:,.0f} {currency}", delta=f"{delta:,.0f} {currency}")
    with col3:
        if len(recent_dates) > 2:
            recent_date = recent_dates[2].strftime('%Y-%m-%d')
            total_portfoy_3 = df_summary.loc[df_summary['Count'] == 3, 'Tutar'].sum() - df_summary.loc[df_summary['Count'] == 3, 'Stopaj'].sum()
            delta = total_portfoy_3 - total_portfoy_4 
            st.metric(label=f"{recent_date} Portföy:", value=f"{total_portfoy_3:,.0f} {currency}", delta=f"{delta:,.0f} {currency}")
    with col2:
        if len(recent_dates) > 1:
            recent_date = recent_dates[1].strftime('%Y-%m-%d')
            total_portfoy_2 = df_summary.loc[df_summary['Count'] == 2, 'Tutar'].sum() - df_summary.loc[df_summary['Count'] == 2, 'Stopaj'].sum()
            delta = total_portfoy_2 - total_portfoy_3 
            st.metric(label=f"{recent_date} Portföy:", value=f"{total_portfoy_2:,.0f} {currency}", delta=f"{delta:,.0f} {currency}")
    with col1:
        if len(recent_dates) > 0:
            recent_date = recent_dates[0].strftime('%Y-%m-%d')
            total_portfoy_1 = df_summary.loc[df_summary['Count'] == 1, 'Tutar'].sum() - df_summary.loc[df_summary['Count'] == 1, 'Stopaj'].sum()
            delta = total_portfoy_1 - total_portfoy_2 
            st.metric(label=f"{recent_date} Portföy:", value=f"{total_portfoy_1:,.0f} {currency}", delta=f"{delta:,.0f} {currency}")

    df_summary = df_summary[df_summary['Count'] <= 1]
    df_summary.drop(columns=['Date', 'Count'], inplace=True)

    styled_df = df_summary.style
    styled_df = styled_df.format({
        'Gider'       : ' {:,.2f}', 
        'Miktar'      : ' {:,.0f}', 
        'Maliyet'     : ' {:.4f}', 
        'Fiyat'       : ' {:.4f}', 
        'Tutar'       : ' {:,.2f}', 
        'Stopaj'      : ' {:,.2f}', 
        'Gün'         : '{:,.0f}', 
        '1d Δ'        : '{:,.2f}', 
        '1d Δ %'      : '% {:,.2f}', 
        'Δ'           : '% {:,.2f}', 
        'Başarı Δ'    : '% {:,.2f}', 
        'Artı Gün %'  : '% {:,.2f}', 
        'RSI'         : '{:.2f}'
    })

    # Add the hyperlinked strings directly into the underlying dataframe column just before styling
    df_summary['Fon'] = "https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod=" + df_summary['Fon']

    styled_df = styled_df.map(lambda val: color_gradient(val, 'Δ') if pd.notnull(val) else '', subset=['Δ'])
    styled_df = styled_df.map(lambda val: color_gradient(val, 'Başarı Δ') if pd.notnull(val) else '', subset=['Başarı Δ'])
    styled_df = styled_df.map(lambda val: RSI_gradient(val) if pd.notnull(val) else '', subset=['RSI'])
    
    dataframe_height = (len(df_summary) + 1) * 35 + 2
    st.dataframe(styled_df, hide_index=True, height=dataframe_height, column_config=column_configuration)

    # Re-extract the original symbol string from the URL to perform the merge with the tefas fund table
    df_summary['Fon_Symbol'] = df_summary['Fon'].str.replace('https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod=', '')

    # Create a pie chart based on FundType
    df_summary = df_summary.merge(df_fon_table, left_on='Fon_Symbol', right_on='symbol', how='left')
    fund_types = [col for col in df_fon_table.columns if col.startswith('FundType_')]
    df_summary['FundType'] = df_summary[fund_types].idxmax(axis=1).str.replace('FundType_', '')
    
    Umbrellafund_types = [col for col in df_fon_table.columns if col.startswith('UmbrellaFundType_')]
    df_summary['UmbrellaFundType'] = df_summary[Umbrellafund_types].idxmax(axis=1).str.replace('UmbrellaFundType_', '')
    
    col1, col2, col3 = st.columns([6, 6, 10])
    
    with col1:
        fig = px.sunburst(df_summary, path=['UmbrellaFundType', 'Fon_Symbol'], values='Tutar', title='Şemsiye Fon Türü Dağılımı')
        st.plotly_chart(fig)
    with col2:
        fig2 = px.sunburst(df_summary, path=['FundType', 'Fon_Symbol'], values='Tutar', title='Fon Türü Dağılımı')
        st.plotly_chart(fig2)
    with col3:
        df_daily_portfolio = calculate_daily_portfolio()
        # Calculate daily cost time series
        def calculate_daily_cost():
            price_dates = sorted(df_transformed['date'].unique())
            start_date = df_portfolio['date'].min()
            set_date = st.session_state.get("set_date")
            end_date = pd.to_datetime(set_date if set_date else datetime.today().date())
            valid_dates = [d for d in price_dates if start_date <= d <= end_date]
            if not valid_dates:
                return pd.DataFrame()
                
            trx = df_portfolio[['date', 'symbol', 'transaction_type', 'quantity', 'price']].copy()
            trx['signed_quantity'] = trx['quantity'].where(trx['transaction_type'] == 'buy', -trx['quantity'])
            trx['cost'] = trx['signed_quantity'] * trx['price']
            
            daily_cost = trx.groupby('date')['cost'].sum()
            df_cost = pd.DataFrame({'Total Portfolio Cost': daily_cost})
            df_cost = df_cost.reindex(valid_dates).fillna(0).cumsum().reset_index()
            df_cost['Total Portfolio Cost'] = df_cost['Total Portfolio Cost'].round(0)
            df_cost = df_cost.rename(columns={'date': 'Date'})
            return df_cost

        df_daily_cost = calculate_daily_cost()

        if not df_daily_portfolio.empty:
            fig3 = go.Figure()
            # Portfolio Value Line
            fig3.add_trace(go.Scatter(
                x=df_daily_portfolio['Date'], 
                y=df_daily_portfolio['Total Portfolio Value'], 
                mode='lines',
                name='Portföy Değeri'
            ))
            # Portfolio Cost Line
            if not df_daily_cost.empty:
                fig3.add_trace(go.Scatter(
                    x=df_daily_cost['Date'],
                    y=df_daily_cost['Total Portfolio Cost'],
                    mode='lines',
                    name='Portföy Maliyeti'
                ))
            
            # Update each trace to set a distinct color and keep the correct name
            # Update the configuration of each line trace to differentiate between positive (increase) and negative (decrease) changes
            # Replace tuple-based loop with explicit updates
            fig3.data[0].update(
                mode='lines',
                name='Portföy Değeri',
                line=dict(color='blue')
            )
            fig3.data[1].update(
                mode='lines',
                name='Portföy Maliyeti',
                line=dict(color='red')
            )
            
            # Update layout to ensure clear differentiation and visibility
            fig3.update_layout(
                title="Portföy Değeri ve Maliyeti Zaman Serisi",
                height=600,
                xaxis_title="Date",
                yaxis_title=f"Portföy Değeri/Maliyeti ({currency})",
                xaxis=dict(rangeslider_visible=True),
                yaxis=dict(tickformat=f".2f {currency}"),
            )
            # Display the plotly chart with differentiated lines for portfolio value and cost
            st.plotly_chart(fig3)

else:
    st.write("No data to display.")