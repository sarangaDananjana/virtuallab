# Dockerfile (Alpine)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update && apt-get install -y \
    curl \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY virtuallabshop/ /app/

EXPOSE 8000
RUN python manage.py tailwind build && python manage.py collectstatic --noinput
CMD sh -lc "python manage.py migrate && gunicorn virtuallabshop.wsgi:application --bind 0.0.0.0:8000"
