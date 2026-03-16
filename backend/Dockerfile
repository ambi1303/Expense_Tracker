# Backend Dockerfile - Gmail Expense Tracker API
FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Non-root user (security)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Port from env (Railway/Render use PORT)
ENV PORT=8000
EXPOSE 8000

# Single worker - APScheduler must not be duplicated
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
