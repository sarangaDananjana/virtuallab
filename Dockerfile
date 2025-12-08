FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install curl (to download Tailwind) and dos2unix (to fix Windows file corruption)
RUN apt-get update && apt-get install -y curl dos2unix && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 2. Download the Standalone Tailwind Binary
# This puts a Linux-compatible binary directly in your path. No npm required.
RUN curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 && \
    chmod +x tailwindcss-linux-x64 && \
    mv tailwindcss-linux-x64 /usr/bin/tailwindcss

# Copy project
COPY virtuallabshop/ /app/

# 3. FIX WINDOWS LINE ENDINGS (Crucial!)
# Your HTML files have Windows hidden characters (\r\n) that blind the Tailwind scanner.
# This command converts them to Linux format (\n) so the tool can read them.
RUN find . -name "*.html" -exec dos2unix {} +

# 4. Build the CSS
# We use the binary directly.
# We use the --content flag to explicitly tell it where to look, bypassing config issues.
RUN tailwindcss -i ./static/src/input.css -o ./static/css/output.css --content "./shop/templates/**/*.html" --minify

EXPOSE 8000

RUN python manage.py collectstatic --noinput

CMD sh -lc "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"