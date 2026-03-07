FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for building TA-Lib and locale support
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Generate the tr_TR.UTF-8 locale
RUN sed -i '/tr_TR.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen

# Copy the requirements files and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app files
COPY . .
