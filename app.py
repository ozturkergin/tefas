import streamlit as st
import pandas as pd
import os
import csv
import json

# Page configuration and styles
st.set_page_config(layout="wide")
with open("assets/styles.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Navigation pages (unchanged)
home_page = st.Page("page/Home.py", title="Home", icon=":material/account_circle:", default=True)
analiz_page = st.Page("page/01_analiz.py", title="TEFAS Analysis", icon=":material/move_up:")
patterns_page = st.Page("page/05_patterns.py", title="Patterns", icon=":material/token:")
islemler_page = st.Page("page/02_islemler.py", title="Transactions", icon=":material/add:")
portfoy_page = st.Page("page/02_portfoy.py", title="Portfolio Analysis", icon=":material/dataset:")
entegrasyon_page = st.Page("page/03_entegrasyon.py", title="Extract Data", icon=":material/library_add:")
fonfavori_page = st.Page("page/02_fonfavori.py", title="Favourites", icon=":material/book:")
tahmin_page = st.Page("page/04_tahmin.py", title="Predictive", icon=":material/data_thresholding:")
tradingview_page = st.Page("page/01_tradingview.py", title="Tradingview Lite", icon=":material/move_up:")
config_page = st.Page("page/07_config.py", title="Configuration", icon=":material/settings:")
history_page = st.Page("page/08_history.py", title="Similar Period Analysis", icon=":material/history:")
LLM_strategy_page = st.Page("page/09_fastmcp.py", title="LLM Strategy", icon=":material/rocket:")

pg = st.navigation(
    {
        "Analysis": [home_page, analiz_page, tahmin_page, patterns_page, tradingview_page, history_page, LLM_strategy_page],
        "Integration": [entegrasyon_page],
        "Portfolio": [islemler_page, portfoy_page],
        "Settings": [config_page, fonfavori_page],
        "Settings": [config_page, fonfavori_page],
    }, 
    position="sidebar"
)

# Authentication
USERS_FILE = "data/users.csv"
def check_credentials(username, password):
    """Check if username and password match a record in the users file."""
    try:
        with open(USERS_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["username"] == username and row["password"] == password:
                    return True
    except Exception as e:
        st.error(f"Error reading users file: {e}")
        return False
    return False

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "remembered_user" not in st.session_state:
    st.session_state["remembered_user"] = None

# Login form if not authenticated
if not st.session_state["authenticated"]:
    st.title("Giriş Yap")
    username = st.text_input("Kullanıcı Adı", value=st.session_state["remembered_user"] or "")
    password = st.text_input("Şifre", type="password")

    if st.button("Giriş"):
        if check_credentials(username, password):
            st.session_state["authenticated"] = True
            st.session_state["remembered_user"] = username
            st.rerun()
        else:
            st.error("Yanlış kullanıcı adı veya şifre")
    st.stop()

# Add logout button (in sidebar)
if st.session_state["authenticated"]:
    if "set_date" not in st.session_state:
        st.session_state["set_date"] = pd.to_datetime('today').date()

    st.session_state["set_date"] = st.sidebar.date_input(
        "Set Date", 
        value=st.session_state["set_date"],
        max_value=pd.to_datetime('today').date()
    )

    if st.sidebar.button("Sign Out"):
        st.session_state["authenticated"] = False
        st.session_state["remembered_user"] = None
        st.rerun()

# Rest of your code (database, portfolio, etc.) remains unchanged
def get_config():
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)
    return {}

config = get_config()
if "use_postgres" not in st.session_state:
    st.session_state["use_postgres"] = config.get("use_postgres", True)

if "POSTGRES_HOST" not in st.session_state:
    st.session_state["POSTGRES_HOST"] = os.getenv("POSTGRES_HOST", "postgres_db")
if "POSTGRES_PORT" not in st.session_state:
    st.session_state["POSTGRES_PORT"] = os.getenv("POSTGRES_PORT", "5432")
if "POSTGRES_DB" not in st.session_state:
    st.session_state["POSTGRES_DB"] = os.getenv("POSTGRES_DB", "tefas_db")
if "POSTGRES_USER" not in st.session_state:
    st.session_state["POSTGRES_USER"] = os.getenv("POSTGRES_USER", "tefas")
if "POSTGRES_PASSWORD" not in st.session_state:
    st.session_state["POSTGRES_PASSWORD"] = os.getenv("POSTGRES_PASSWORD", "tefas")

PORTFOLIO_FILE = f"data/myportfolio_{st.session_state["remembered_user"]}.csv"
FAVOURITES_FILE = f"data/favourites_{st.session_state["remembered_user"]}.csv"

# Portfolio and Favourites loading
if os.path.exists(PORTFOLIO_FILE):
    if not 'myportfolio' in st.session_state:
        myportfolio = pd.read_csv(PORTFOLIO_FILE, parse_dates=['date'])
        myportfolio['quantity'] = pd.to_numeric(myportfolio['quantity'], errors='coerce').fillna(0).astype(int)
        myportfolio = myportfolio[myportfolio.quantity != 0]
        st.session_state.myportfolio = myportfolio

if os.path.exists(FAVOURITES_FILE):
    if not 'favourites' in st.session_state:
        st.session_state.favourites = pd.read_csv(FAVOURITES_FILE)['symbol'].tolist()

pg.run()