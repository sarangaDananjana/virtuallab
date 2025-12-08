FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install Node.js and NPM (Standard Debian versions)
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY virtuallabshop/ /app/

EXPOSE 8000

# 2. THE FIX: Run everything at startup
# This command does 4 things in order:
# A. Installs Tailwind (Fresh for this container)
# B. Creates a guaranteed valid input.css file
# C. Builds the CSS immediately
# D. Starts the Django Server
CMD sh -c "echo '🚀 Starting Runtime Build...' && \
           npm install -D tailwindcss && \
           echo '@tailwind base; @tailwind components; @tailwind utilities;' > ./static/src/input.css && \
           npx tailwindcss -i ./static/src/input.css -o ./static/css/output.css --content './shop/templates/**/*.html' --minify && \
           echo '✅ CSS Build Complete!' && \
           python manage.py collectstatic --noinput && \
           python manage.py migrate && \
           python manage.py runserver 0.0.0.0:8000"