import streamlit as st
import pandas as pd
import os
from datetime import datetime
from page.utils import read_table

df_fon_table = read_table('tefas_funds', parse_dates=None)
unique_symbols = sorted(df_fon_table['symbol'].unique().tolist())
symbol_titles = df_fon_table.set_index('symbol')['title'].to_dict()

# Function to load favourites
def load_favourites(favourites_file='data/favourites.csv'):
    if os.path.exists(favourites_file):
        return pd.read_csv(favourites_file)['symbol'].tolist()  # Return as list
    return []  # Return empty list if file doesn't exist

# Initialize favourites in session state
if 'favourites' not in st.session_state:
    st.session_state.favourites = load_favourites()

# Multiselect with unique symbols
selected_symbols = st.multiselect(
    'Select Symbols:',
    unique_symbols,
    default=st.session_state.favourites,
    key='selected_symbols'
)

# Save selected symbols to favourites.csv when the selection changes
if selected_symbols != st.session_state.favourites:
    st.session_state.favourites = selected_symbols  # Update session state
    # Save the selected symbols to CSV
    pd.DataFrame({'symbol': selected_symbols}).to_csv('data/favourites.csv', index=False)
    st.success("Favourites updated successfully.")
    st.rerun()  # Rerun the script to refresh the page

# Create DataFrame for st.dataframe
selected_df = pd.DataFrame({
    'code': selected_symbols,
    'codewithtext': [f"{code} - {symbol_titles.get(code, '')}" for code in selected_symbols]
})

# Display selected symbols using st.dataframe
st.dataframe(selected_df, hide_index=True, height=500)