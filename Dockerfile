FROM python:3.12-slim

WORKDIR /app

# Copy the entire project
COPY . .

# Install the package (including dependencies)
RUN pip install --no-cache-dir .

# Create non-root user
RUN useradd -m -u 1000 mapserver && chown -R mapserver:mapserver /app
USER mapserver

# Environment variables
ENV HTTP_PORT=8081

# Expose HTTP port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/')"

# Run server using the entry point
CMD ["mcp-map-server"]
