# CHANGE 1: Use 'slim' instead of 'alpine'.
# This is standard Linux (Debian), so the Tailwind binary will actually work.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# CHANGE 2: Install 'curl' using apt-get (Debian's package manager)
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# CHANGE 3: Download Tailwind
# We download the standard Linux binary. On 'slim', this runs natively.
RUN curl -sLO https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 && \
    chmod +x tailwindcss-linux-x64 && \
    mv tailwindcss-linux-x64 /usr/bin/tailwindcss

# Copy project files
COPY virtuallabshop/ /app/

# CHANGE 4: Build CSS
# This command will finally succeed because the OS is compatible.
RUN tailwindcss -i ./static/src/input.css -o ./static/css/output.css --minify

EXPOSE 8000

# Collect static files (now that CSS is built)
RUN python manage.py collectstatic --noinput

CMD sh -lc "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"