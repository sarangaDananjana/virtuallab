# Dockerfile (Alpine)
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk add --update nodejs npm
# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY virtuallabshop/ /app/

RUN npm install -g tailwindcss
RUN npx tailwindcss -i ./static/src/input.css -o ./static/css/output.css --minify

EXPOSE 8000
RUN python manage.py collectstatic --noinput
# For dev: run migrations then dev server
CMD sh -lc "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
