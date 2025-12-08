FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install Node.js, NPM, and dos2unix (To fix Windows file endings)
RUN apt-get update && apt-get install -y nodejs npm dos2unix && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY virtuallabshop/ /app/

# 2. FIX WINDOWS LINE ENDINGS (The "Nuclear" fix for empty CSS)
# This converts all your HTML files to Linux format so Tailwind can read them
RUN find . -name "*.html" -exec dos2unix {} +

# 3. Install Tailwind GLOBALLY
# The '-g' flag installs it to the system path, bypassing local node_modules issues
RUN npm install -g tailwindcss

# 4. Build the CSS
# We run 'tailwindcss' directly (no npx). It will find the global command.
# We also use the --content flag to FORCE it to find your files.
RUN tailwindcss -i ./static/src/input.css -o ./static/css/output.css --content "./shop/templates/**/*.html" --minify

EXPOSE 8000

RUN python manage.py collectstatic --noinput

CMD sh -lc "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"