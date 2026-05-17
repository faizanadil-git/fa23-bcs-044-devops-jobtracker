# Dockerfile.backend
# JobTrack Backend — Flask API + Frontend Templates
# FA23-BCS-044

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy only requirements first (layer caching optimization)
COPY requirements.txt .

# Install dependencies without cache to reduce image size
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose Flask port
EXPOSE 5000

# Start the Flask application
CMD ["python", "app.py"]
