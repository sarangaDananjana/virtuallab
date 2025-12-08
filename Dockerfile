FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install system dependencies
RUN apt-get update && apt-get install -y nodejs npm curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project (This copies the "bad" Windows node_modules)
COPY virtuallabshop/ /app/

# --- THE FIX IS HERE ---
# 2. Force delete the copied Windows/Mac modules to ensure a clean slate
RUN rm -rf node_modules package-lock.json

# 3. Fresh Install for Linux
RUN npm init -y
RUN npm install -D tailwindcss

# 4. Build CSS
# Now npx will work because we forced a fresh download of Linux binaries
RUN npx tailwindcss -i ./static/src/input.css -o ./static/css/output.css --minify
# -----------------------

EXPOSE 8000

RUN python manage.py collectstatic --noinput

CMD sh -lc "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"