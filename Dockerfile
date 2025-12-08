FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install Node.js and NPM
RUN apt-get update && apt-get install -y nodejs npm curl && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY virtuallabshop/ /app/

# 2. Install Tailwind via NPM (The standard, reliable way)
# We use a clean install to ensure Linux binaries are downloaded
RUN npm init -y
RUN npm install -D tailwindcss

# 3. Build CSS
# We use npx, which will now work because of the volume hack in compose
RUN npx tailwindcss -i ./static/src/input.css -o ./static/css/output.css --minify

EXPOSE 8000

RUN python manage.py collectstatic --noinput

CMD sh -lc "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"