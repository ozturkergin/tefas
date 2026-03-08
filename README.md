# TEFAS Portfolio Analyzer & Manager

An interactive, containerized web application built with **Streamlit** and **PostgreSQL** that enables Turkish investors to deeply analyze mutual funds (`TEFAS`), track personal portfolios, calculate daily portfolio performances, and visualize key performance indicators across different currencies (TRY, USD, and Gold).

## 🚀 Features
- **Portfolio Management**: Record buy and sell transactions, seeing real-time realized and unrealized tax ratios.
- **Dynamic Charting**: Built-in plotly interactive visualizations for fund comparisons.
- **Cross-Currency Backtesting**: Check fund histories against FX Rates (₺, $, and gr Gold) over custom timelines.
- **Data Integration Scripts**: Automated ingestion algorithms specifically scraping historical data spanning over a year directly from TEFAS infrastructure.
- **Full Docker Support**: Ships encapsulated securely behind a custom bridging network allowing out-of-the-box local operation! 

---

## 🛠️ Installation & Setup (For First Time Users)
To run this application, you must have [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed on your machine. 

### 1. Clone the Repository
Open your terminal/command-prompt and clone this repository down:
```bash
git clone https://github.com/ozturkergin/tefas.git
cd tefas
```

### 2. Configure Users (Optional)
The authentication logic reads from `data/users.csv`. By default, you'll need to create this locally inside the `data/` folder, adding credentials for you to access the dashboard:
```csv
username,password
admin,Tefas
```

### 3. Quickstart Initializing Sequence 
Because this application depends heavily on historical index data spanning years back, we created automated setup bash and batch scripts that instantiate the Postgres schema internally and fetch recent prices.

**Windows Users**:
Simply run:
```cmd
setup.bat
```

**Mac / Linux Users**:
Make the script executable, and run it:
```bash
chmod +x setup.sh
./setup.sh
```

*(Note: The setup script will sleep for 15 seconds sequentially after pulling the Docker containers to let the PostgreSQL runtime engine internally bind port schemas completely before passing it large chunks of table rows from TEFAS servers. Be patient initially.)*

### 4. Open Application
Once the terminal notifies you the setup is complete, navigate to:
👉 **[http://localhost:5002](http://localhost:5002)**

---

## 🏗️ Architecture Overview
* **UI**: Streamlit Python
* **Analytics**: Pandas, Plotly, Pandas-TA
* **Storage**: Remote PostgreSQL Database Engine Instance
* **Data Sources**: Internal web scraping logic combined directly with Yahoo Finance for FX equivalents.

### Port Configuration
By default, the Docker containers are mapped to the following ports on your host machine:
- **`5002`**: The main Streamlit Web Application (`localhost:5002`).
- **`5433`**: The PostgreSQL Database (`localhost:5433`). 

*Note: The database is intentionally mapped to custom port `5433` (instead of the standard `5432`) to prevent conflicts if you already have a native PostgreSQL instance running on your machine. You can connect to this isolated database using any SQL Client (like pgAdmin or DBeaver) using `localhost`, port `5433`, username `tefas`, and password `tefas`.*

---

## ⚙️ Administration Commands
If you want granular control, you can always bypass the `setup` scripts and build it raw:
```bash
docker-compose up -d --build
```

If you ever need to manually force the python extract scripts to update your tables with newest data limits or compute missing indicators outside the web interface:
```bash
docker exec tefas python3 page/extract.py --tefas_price true --calculate_indicators true --tefas_fundtype true --timedelta 365
```

## 📜 Repository Maintainers
Please make Pull Requests directly toward the `main` branch. 
Data generated securely in `.csv` forms will not track across your source control due to gitignore specifications protecting personal portfolios. 
