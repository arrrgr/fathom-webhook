FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Expose port
EXPOSE 5000

# Run with gunicorn explicitly
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
