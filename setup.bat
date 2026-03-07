@echo off
echo =======================================================
echo 🚀 Starting Docker containers...
echo =======================================================
docker-compose up -d

echo.
echo ⏳ Waiting for PostgreSQL to initialize (15 seconds)...
timeout /t 15 /nobreak >nul

echo.
echo 📥 Running initial data extraction to populate the database tables...
echo This might take a few minutes as it downloads TEFAS prices, FX and Gold rates, and calculates indicators for the last year...
docker exec tefas python3 page/extract.py --tefas_price true --calculate_indicators true --tefas_fundtype true --timedelta 365

echo.
echo =======================================================
echo ✅ Setup is complete! 
echo You can access the application at http://localhost:5002
echo =======================================================
