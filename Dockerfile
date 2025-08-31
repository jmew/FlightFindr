# Use a single, compatible base image for both runtimes
FROM python:3.11-slim-bookworm

# Install Node.js, npm, and supervisor
RUN apt-get update && \
    apt-get install -y curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs supervisor && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY flight-findr-mcp/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium
COPY flight-findr-mcp/ ./flight-findr-mcp

# Install Node.js dependencies
COPY web-server/package*.json ./
RUN npm ci
COPY web-server/. .

# Copy the supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create .gemini directory and copy GEMINI.md
RUN mkdir -p /root/.gemini
COPY .gemini/GEMINI.md /root/.gemini/GEMINI.md

ENV GEMINI_API_KEY=$GEMINI_API_KEY
EXPOSE 3000 9999 10000

# Run supervisor to start both services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
