# Dockerfile (Alpine)
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# deps for mysqlclient on musl/Alpine
RUN apk add --no-cache \
    build-base \
    mariadb-connector-c-dev \
    mariadb-dev \
    pkgconfig \
    linux-headers
# Install Python deps
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY virtuallabshop/ /app/

EXPOSE 8000
RUN python manage.py collectstatic --noinput
# For dev: run migrations then dev server
CMD bash -lc "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
