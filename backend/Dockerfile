# Use Python official image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create necessary directories
RUN mkdir -p temp chroma_db

# Expose port
EXPOSE 5000

# Start the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--reload"] 