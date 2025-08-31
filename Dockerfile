# Stage 1: Build the Node.js web-server
FROM node:20.11.1-slim AS web-server-stage
WORKDIR /app
COPY web-server/package*.json ./
RUN npm ci
COPY web-server/. .
RUN npm run build

# Stage 2: Setup the Python MCP server
FROM python:3.11-slim AS mcp-server-stage
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY flight-findr-mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps
COPY flight-findr-mcp/. .

# Final stage: Combine both services into a single Node.js image
FROM node:20.11.1-slim
RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Copy the Node.js app and its dependencies from the first stage
COPY --from=web-server-stage /app /app

# Copy the entire Python installation from the second stage
COPY --from=mcp-server-stage /usr/local/ /usr/local/

# Copy the Python app code from the second stage
COPY --from=mcp-server-stage /app /app/flight-findr-mcp

# Copy the supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

ENV GEMINI_API_KEY=$GEMINI_API_KEY
EXPOSE 3000 9999 10000

# Run supervisor to start both services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]

