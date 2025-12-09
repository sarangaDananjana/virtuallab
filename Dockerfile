# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install System Dependencies AND Node.js + NPM
# (We need Node to run Tailwind reliably in Docker)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Python Dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the project code
COPY virtuallabshop/ /app/

# 4. Install Tailwind Node Dependencies
# (This assumes your theme app is named 'theme'. Adjust path if different)
WORKDIR /app/theme/static_src
RUN npm install
# Go back to root
WORKDIR /app

EXPOSE 8000

# 5. Build Tailwind once (so static files exist on startup)
RUN python manage.py tailwind build
RUN python manage.py collectstatic --noinput

# 6. FIXED COMMAND: Run Tailwind Watcher in background (&) AND Django Server
CMD sh -lc "(python manage.py tailwind start &) && python manage.py runserver 0.0.0.0:8000"