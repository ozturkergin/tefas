#!/bin/bash

echo "🚀 Starting Docker containers..."
docker-compose up -d

echo "⏳ Waiting for PostgreSQL to initialize (15 seconds)..."
sleep 15

echo "📥 Running initial data extraction to populate the database tables..."
echo "This might take a few minutes as it downloads TEFAS prices, FX and Gold rates, and calculates indicators..."
docker exec tefas python3 page/extract.py --tefas_price true --calculate_indicators true --tefas_fundtype true --timedelta 365

echo "✅ Setup is complete! You can access the application at http://localhost:5002"
