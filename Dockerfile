FROM python:3.12-slim

LABEL maintainer="Kritika Garg"

ENV PYTHONUNBUFFERED=1 \
    DOCROOT=/var/www/html \
    LOG_DIR=/var/log/httpd

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/
COPY www/ /var/www/html/

# Run as an unprivileged user; it owns the docroot so authorized PUT/DELETE work.
RUN useradd --system --no-create-home httpd \
    && mkdir -p /var/log/httpd \
    && chown -R httpd /var/log/httpd /var/www/html
USER httpd

EXPOSE 8080
CMD ["python", "server.py", "0.0.0.0", "8080"]
