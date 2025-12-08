# Dockerfile
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install dependencies
# We use 'curl' to download Tailwind, we DO NOT need nodejs or npm
RUN apk add --update curl

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 2. Download Tailwind Standalone CLI (Linux version)
# This puts the executable at /usr/bin/tailwindcss so we can run it anywhere
RUN curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 && \
    chmod +x tailwindcss-linux-x64 && \
    mv tailwindcss-linux-x64 /usr/bin/tailwindcss

# 3. Copy your project
COPY virtuallabshop/ /app/

# 4. Build the CSS
# We run the binary directly. No npx, no node_modules.
RUN tailwindcss -i ./static/src/input.css -o ./static/css/output.css --minify

EXPOSE 8000

# 5. Collect static (now includes the compiled css)
RUN python manage.py collectstatic --noinput

CMD sh -lc "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"