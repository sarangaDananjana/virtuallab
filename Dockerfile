# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install curl (to download Tailwind)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 2. Download Tailwind Binary (Global Install)
# We put it in /usr/local/bin so it is always found
RUN curl -L https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 -o /usr/local/bin/tailwindcss && \
    chmod +x /usr/local/bin/tailwindcss

# Copy project
COPY virtuallabshop/ /app/

EXPOSE 8000

# 3. THE FIX: Build CSS *at runtime*
# We chain the commands: Build CSS -> Collect Static -> Run Server
# This ensures the build happens AFTER your local files are mounted.
CMD sh -c "tailwindcss -i ./static/src/input.css -o ./static/css/output.css --content './shop/templates/**/*.html' --minify && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"