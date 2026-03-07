import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import concurrent.futures

st.title("Similar Period Analysis")

# Add input for days variable outside the cached function
col1, col2, col3 = st.columns(3)

with col1:
    strategy_start_date = st.date_input("Select strategy start date for analysis:", value=datetime(datetime.today().year, 6, 1) - timedelta(days=0))
with col2:
    days_bucket = st.number_input("Enter days for analysis bucket:", min_value=1, value=7,step=1)
with col3:
    days_forward = st.number_input("Enter days for best performers in similar history:", min_value=1, value=14, step=1)

# Note: The "missing ScriptRunContext!" warning is expected when using ThreadPoolExecutor with Streamlit.
# It does not affect the correctness of your results, but Streamlit widgets (like st.write, st.warning, etc.)
# should NOT be called from within threads. Only call Streamlit functions from the main thread.

def find_similar_period(recent_date, days_bucket, days_forward, top_n=1):
    # Load data from session state or CSV
    if 'df_fon_table' in st.session_state:
        df_fon_table = st.session_state.df_fon_table
    else:
        df_fon_table = pd.read_csv('data/fon_table.csv')
        st.session_state.df_fon_table = df_fon_table

    if 'df_transformed' in st.session_state:
        df_transformed = st.session_state.df_transformed
    else:
        df_transformed = pd.read_csv('data/tefas_transformed.csv', encoding='utf-8-sig', parse_dates=['date'])
        st.session_state.df_transformed = df_transformed

    # Get symbol attributes
    symbol_attributes_of_fon_table = [col for col in df_fon_table.columns if col.startswith('FundType_')]
    symbol_attributes_list = [col.replace('FundType_', '') for col in symbol_attributes_of_fon_table]

    # Update week_ago calculation
    week_ago = recent_date - timedelta(days=days_bucket)
    
    # Filter recent week's data
    recent_data = df_transformed[(df_transformed['date'] >= week_ago) & (df_transformed['date'] <= recent_date)]
    recent_data = pd.merge(recent_data, df_fon_table, on='symbol', how='inner')

    # Calculate recent week's percentage change by Fon Unvan Türü
    recent_summary = []
    for attribute in symbol_attributes_list:
        attribute_col = 'FundType_' + attribute
        if attribute_col not in recent_data.columns:
            continue
            
        filtered_data = recent_data[recent_data[attribute_col] == True]
        if filtered_data.empty:
            continue
            
        start_value = filtered_data[filtered_data['date'] == filtered_data['date'].min()]['market_cap'].sum()
        end_value = filtered_data[filtered_data['date'] == filtered_data['date'].max()]['market_cap'].sum()
        
        if start_value == 0:
            continue
            
        pct_change = (end_value - start_value) / start_value * 100
        
        recent_summary.append({
            'Fon Unvan Türü': attribute,
            'Recent_%_Change': pct_change
        })

    recent_df = pd.DataFrame(recent_summary)
    if recent_df.empty:
        st.warning("No recent data available for comparison.")
        return None

    # Find historical periods with similar changes
    results = []
    min_date = df_transformed['date'].min()
    max_date = recent_date - timedelta(days=days_bucket)  # Don't overlap with recent period
    
    # Iterate through historical periods
    current_start = min_date
    while current_start + timedelta(days=days_bucket) <= max_date:
        current_end = current_start + timedelta(days=days_bucket)
        period_data = df_transformed[(df_transformed['date'] >= current_start) & 
                                  (df_transformed['date'] <= current_end)]
        period_data = pd.merge(period_data, df_fon_table, on='symbol', how='inner')
        
        period_summary = []
        for attribute in symbol_attributes_list:
            attribute_col = 'FundType_' + attribute
            if attribute_col not in period_data.columns:
                continue
                
            filtered_data = period_data[period_data[attribute_col] == True]
            if filtered_data.empty:
                continue
                
            start_value = filtered_data[filtered_data['date'] == filtered_data['date'].min()]['market_cap'].sum()
            end_value = filtered_data[filtered_data['date'] == filtered_data['date'].max()]['market_cap'].sum()
            
            if start_value == 0:
                continue
                
            pct_change = (end_value - start_value) / start_value * 100
            
            period_summary.append({
                'Fon Unvan Türü': attribute,
                'Period_%_Change': pct_change
            })
        
        if period_summary:
            period_df = pd.DataFrame(period_summary)
            # Merge with recent data to compare
            comparison = pd.merge(recent_df, period_df, on='Fon Unvan Türü', how='inner')
            
            if not comparison.empty:
                # Calculate similarity (mean absolute difference)
                comparison['Diff'] = abs(comparison['Recent_%_Change'] - comparison['Period_%_Change'])
                similarity_score = comparison['Diff'].mean()
                
                results.append({
                    'Period_Start': current_start,
                    'Period_End': current_end,
                    'Similarity_Score': similarity_score,
                    'Details': comparison[['Fon Unvan Türü', 'Recent_%_Change', 'Period_%_Change']]
                })
        
        current_start += timedelta(days=1)  # Slide window by 1 day

    if not results:
        st.warning("No similar periods found in historical data.")
        return None

    # Find the most similar period
    results_df = pd.DataFrame([(r['Period_Start'], r['Period_End'], r['Similarity_Score']) 
                             for r in results], 
                            columns=['Period_Start', 'Period_End', 'Similarity_Score'])
    most_similar = results_df.loc[results_df['Similarity_Score'].idxmin()]
    
    # Get details for the most similar period
    most_similar_details = next(r['Details'] for r in results 
                              if r['Period_Start'] == most_similar['Period_Start'] and 
                              r['Period_End'] == most_similar['Period_End'])
    
    # Calculate top n most profitable symbols per category for the `days_forward` period after the historical start date
    historical_start_date = most_similar['Period_Start']
    future_start_date = historical_start_date
    future_end_date = future_start_date + timedelta(days=days_forward)
    
    # Filter data for the `days_forward` period after the historical start date
    future_data = df_transformed[(df_transformed['date'] >= future_start_date) & 
                                 (df_transformed['date'] <= future_end_date)]
    future_data = pd.merge(future_data, df_fon_table, on='symbol', how='inner')
    
    # Calculate profitability for each symbol in each category (future period)
    profitability_data = []
    for attribute in symbol_attributes_list:
        attribute_col = 'FundType_' + attribute
        if attribute_col not in future_data.columns:
            continue
            
        filtered_data = future_data[future_data[attribute_col] == True]
        if filtered_data.empty:
            continue
            
        # Group by symbol and calculate percentage change over the `days_forward` period using close
        symbols = filtered_data['symbol'].unique()
        for symbol in symbols:
            symbol_data = filtered_data[filtered_data['symbol'] == symbol]
            if symbol_data.empty:
                continue

            # Check if 'close' column exists in the symbol data
            if 'close' not in symbol_data.columns:
                st.warning(f"close data is missing for symbol {symbol}. Skipping this symbol.")
                continue

            start_price = symbol_data[symbol_data['date'] == symbol_data['date'].min()]['close'].mean()
            end_price = symbol_data[symbol_data['date'] == symbol_data['date'].max()]['close'].mean()
            
            if start_price > 0 and end_price > 0:
                pct_change = (end_price - start_price) / start_price * 100
                profitability_data.append({
                    'Fon Unvan Türü': attribute,
                    'Symbol': symbol,
                    'Profitability_%_Change': pct_change,
                    'Serbest mi': symbol_data[symbol_data['date'] == symbol_data['date'].min()]['FundType_Serbest'].values[0]
                })

    profitability_df = pd.DataFrame(profitability_data)

    # Get top n symbols per category based on profitability
    top_symbols = profitability_df.groupby('Fon Unvan Türü').apply(
        lambda x: x.nlargest(
            top_n, 'Profitability_%_Change'
        ) if x.name == 'Serbest' else x[x['Serbest mi'] == False].nlargest(
            top_n, 'Profitability_%_Change'
        )
    ).reset_index(drop=True)
    
    # Calculate similarity score based on market_cap
    symbol_changes = []
    for _, row in top_symbols.iterrows():
        category = row['Fon Unvan Türü']
        symbol = row['Symbol']
        
        # Historical period change (market_cap)
        historical_symbol_data = future_data[future_data['symbol'] == symbol]
        if not historical_symbol_data.empty:
            start_value_hist = historical_symbol_data[historical_symbol_data['date'] == historical_symbol_data['date'].min()]['market_cap'].sum()
            end_value_hist = historical_symbol_data[historical_symbol_data['date'] == historical_symbol_data['date'].max()]['market_cap'].sum()
            hist_pct_change = (end_value_hist - start_value_hist) / start_value_hist * 100 if start_value_hist != 0 else 0
        else:
            hist_pct_change = 0
        
        # Recent period change (market_cap)
        recent_symbol_data = recent_data[recent_data['symbol'] == symbol]
        if not recent_symbol_data.empty:
            start_value_recent = recent_symbol_data[recent_symbol_data['date'] == recent_symbol_data['date'].min()]['market_cap'].sum()
            end_value_recent = recent_symbol_data[recent_symbol_data['date'] == recent_symbol_data['date'].max()]['market_cap'].sum()
            recent_pct_change = (end_value_recent - start_value_recent) / start_value_recent * 100 if start_value_recent != 0 else 0
        else:
            recent_pct_change = 0
        
        # Calculate similarity score
        if recent_pct_change == 0 and hist_pct_change == 0:
            similarity_score = 100  # Both are 0, so 100% similar
        else:
            max_val = max(abs(recent_pct_change), abs(hist_pct_change))
            if max_val == 0:
                similarity_score = 0
            else:
                similarity_score = 100 * (1 - abs(recent_pct_change - hist_pct_change) / max_val)
        
        symbol_changes.append({
            'Fon Unvan Türü': category,
            'Symbol': symbol,
            'Historical_%_Change': hist_pct_change,
            'Recent_%_Change': recent_pct_change,
            'Similarity_Score': similarity_score
        })

    symbol_changes_df = pd.DataFrame(symbol_changes)

    # Pivot the top symbols into separate columns
    top_symbols['Rank'] = top_symbols.groupby('Fon Unvan Türü').cumcount() + 1
    top_symbols_pivot = top_symbols.pivot(index='Fon Unvan Türü', columns='Rank', values=['Symbol', 'Profitability_%_Change'])
    
    # Flatten the multi-level column names
    top_symbols_pivot.columns = [
        f'Top{rank}_Symbol' if name == 'Symbol' else 
        f'Top{rank}_%_Profitability'
        for name, rank in top_symbols_pivot.columns
    ]
    top_symbols_pivot = top_symbols_pivot.reset_index()
    
    # Merge with comparison details
    most_similar_details = most_similar_details.merge(
        top_symbols_pivot,
        on='Fon Unvan Türü',
        how='left'
    )
    
    # Do NOT fill NaN values - let them remain as NaN to display as empty in Streamlit
    # Format output (round numerical columns, but preserve NaN)
    most_similar_details['Recent_%_Change'] = pd.to_numeric(most_similar_details['Recent_%_Change'], errors='coerce').round(2)
    most_similar_details['Period_%_Change'] = pd.to_numeric(most_similar_details['Period_%_Change'], errors='coerce').round(2)
    for rank in range(1, top_n + 1):
        colname = f'Top{rank}_%_Profitability'
        if colname in most_similar_details.columns:
            most_similar_details[colname] = pd.to_numeric(most_similar_details[colname], errors='coerce').round(2)
    
    return {
        'Period_Start': most_similar['Period_Start'],
        'Period_End': most_similar['Period_End'],
        'Similarity_Score': round(most_similar['Similarity_Score'], 2),
        'Details': most_similar_details,
        'Top1_Symbols': top_symbols_pivot['Top1_Symbol'].dropna().unique().tolist() if 'Top1_Symbol' in top_symbols_pivot.columns else [],
        # Add period start/end for easy access
        'Most_Similar_Period_Start': most_similar['Period_Start'],
        'Most_Similar_Period_End': most_similar['Period_End']
    }

# Add a button to trigger the yearly Top1 backtest
if st.button("Run Top1 Backtest for Each Day of This Year"):
    # Load df_transformed for backtest
    if 'df_transformed' in st.session_state:
        df_transformed = st.session_state.df_transformed
    else:
        df_transformed = pd.read_csv('data/tefas_transformed.csv', encoding='utf-8-sig', parse_dates=['date'])
        st.session_state.df_transformed = df_transformed

    # Remove 'Serbest' if present
    if 'FundType_Serbest' in df_transformed.columns:
        df_transformed = df_transformed[df_transformed['FundType_Serbest'] != True]

    # Load df_fon_table
    if 'df_fon_table' in st.session_state:
        df_fon_table = st.session_state.df_fon_table
    else:
        df_fon_table = pd.read_csv('data/fon_table.csv')
        st.session_state.df_fon_table = df_fon_table

    yearly_results = []

    year_start = strategy_start_date
    year_end = datetime.today() - timedelta(days=days_forward)
    all_days = pd.date_range(year_start, year_end, freq='D')

    # Show a placeholder for progress bar and status text
    progress_bar = st.empty()
    status_text = st.empty()

    def process_single_date(looped_recent_date):
        result = find_similar_period(looped_recent_date, days_bucket, days_forward, top_n=1)
        results_for_date = []
        if result and result.get('Top1_Symbols'):
            period_start = result.get('Most_Similar_Period_Start')
            period_end = result.get('Most_Similar_Period_End')
            # Find the symbol with the max Similar Period Profit %
            max_profit = None
            max_symbol = None
            max_buy_price = None
            max_sell_price = None
            max_sell_day = None
            for symbol in result['Top1_Symbols']:
                buy_row = df_transformed[(df_transformed['symbol'] == symbol) & (df_transformed['date'] == looped_recent_date)]
                sell_day = looped_recent_date + timedelta(days=int(days_forward))
                sell_row = df_transformed[(df_transformed['symbol'] == symbol) & (df_transformed['date'] == sell_day)]
                # Get Similar Period Profit % from result['Details'] for this symbol
                details = result.get('Details')
                similar_period_profit = None
                if details is not None and 'Top1_%_Profitability' in details.columns:
                    row = details[(details['Top1_Symbol'] == symbol)]
                    if not row.empty:
                        similar_period_profit = row['Top1_%_Profitability'].values[0]
                if not buy_row.empty and not sell_row.empty and similar_period_profit is not None:
                    buy_price = buy_row['close'].values[0]
                    sell_price = sell_row['close'].values[0]
                    profit_pct = ((sell_price - buy_price) / buy_price) * 100 if buy_price != 0 else np.nan
                    if (max_profit is None) or (similar_period_profit > max_profit):
                        max_profit = similar_period_profit
                        max_symbol = symbol
                        max_buy_price = buy_price
                        max_sell_price = sell_price
                        max_sell_day = sell_day
            if max_symbol is not None:
                results_for_date.append({
                    'Date': looped_recent_date,
                    'Similar_Period_Start': period_start,
                    'Similar_Period_End': period_end,
                    'Top1_Symbol': max_symbol,
                    'Buy_Price': max_buy_price,
                    'Sell_Date': max_sell_day,
                    'Sell_Price': max_sell_price,
                    'Profit_%': ((max_sell_price - max_buy_price) / max_buy_price) * 100 if max_buy_price != 0 else np.nan,
                    'Similar_Period_Profit_%': max_profit
                })
        return results_for_date

    yearly_results = []
    total_days = len(all_days)
    for i, looped_recent_date in enumerate(all_days):
        result = process_single_date(looped_recent_date)
        if result:
            yearly_results.extend(result)
        # Update progress bar and status
        progress = (i + 1) / total_days
        progress_bar.progress(progress)
        status_text.text(f"Processed {i+1} of {total_days} days...")

    # Clear status after completion
    progress_bar.empty()
    status_text.empty()

    if yearly_results:
        yearly_df = pd.DataFrame(yearly_results)
        st.write(f"Yearly Top1 Symbol Backtest Results (using find_similar_period, buy & hold for {days_forward} days):")
        st.dataframe(yearly_df, hide_index=True, height=min(600, (len(yearly_df)+1)*35+2))
        avg_profit = yearly_df['Profit_%'].sum()
        st.metric("Average Profit % (Yearly Top1 Strategy)", f"{avg_profit:.2f}")
    else:
        st.info("No valid Top1 backtest results for this year.")

# Performance tips for this calculation:
# 1. Cache expensive data loads and computations outside the loop.
# 2. Avoid repeated merges and filtering inside the loop.
# 3. Precompute and reuse as much as possible.
# 4. Use vectorized pandas operations instead of for-loops where possible.
# 5. Consider reducing the number of days or categories if possible.

# Example improvements:
# - Move df_fon_table and df_transformed loading outside the loop (already done).
# - Pre-merge df_transformed with df_fon_table once, and use this merged DataFrame in all calculations.
# - If possible, filter df_transformed to only relevant dates before looping.
# - If you only need Top1 symbol per day, consider using groupby and rolling windows for vectorized calculations.

# Example: Pre-merge and filter once
if 'df_fon_table' in st.session_state:
    df_fon_table = st.session_state.df_fon_table
else:
    df_fon_table = pd.read_csv('data/fon_table.csv')
    st.session_state.df_fon_table = df_fon_table

if 'df_transformed' in st.session_state:
    df_transformed = st.session_state.df_transformed
else:
    df_transformed = pd.read_csv('data/tefas_transformed.csv', encoding='utf-8-sig', parse_dates=['date'])
    st.session_state.df_transformed = df_transformed

# Remove 'Serbest' once
if 'FundType_Serbest' in df_transformed.columns:
    df_transformed = df_transformed[df_transformed['FundType_Serbest'] != True]

# Merge once
df_merged = pd.merge(df_transformed, df_fon_table, on='symbol', how='inner')

# Then, in your loop, use df_merged instead of merging every time.
# You can also filter df_merged to only the date range you need for the whole backtest.

# If you want to go further, you can use pandas rolling/groupby to calculate rolling windows for each symbol/category,
# but this requires more advanced pandas usage.