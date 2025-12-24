FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server_sse.py .
COPY client_sse.html .

# Create non-root user
RUN useradd -m -u 1000 mapserver && chown -R mapserver:mapserver /app
USER mapserver

# Environment variables (can be overridden)
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV REDIS_DB=0
ENV HTTP_PORT=8081

# Expose HTTP port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/health')"

# Run server
CMD ["python", "server_sse.py"]
