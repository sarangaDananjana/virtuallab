FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Install Node.js and NPM
RUN apk add --update nodejs npm

# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project (The .dockerignore will now block node_modules)
COPY virtuallabshop/ /app/

# 2. Force a clean Tailwind Install
# We delete node_modules just in case .dockerignore was skipped
RUN rm -rf node_modules package-lock.json package.json
RUN npm init -y
RUN npm install tailwindcss

# 3. Build the CSS
# Using npx is safer now that we have a clean install
RUN npx tailwindcss -i ./static/src/input.css -o ./static/css/output.css --minify

EXPOSE 8000

# 4. Collect static files
RUN python manage.py collectstatic --noinput

CMD sh -lc "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"