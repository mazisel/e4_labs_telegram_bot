# Base image with Python
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Pillow and psd-tools
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate template from PSD on build
RUN python generate_template.py

# Run the bot
CMD ["python", "main.py"]
