FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install curl (Essential for the bypass)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY virtuallabshop/ /app/

EXPOSE 8000

# We leave the command empty here because we override it in docker-compose
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]