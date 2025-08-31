# Stage 1: Build the Node.js web-server
FROM node:20.11.1-slim AS web-server-stage
WORKDIR /app
COPY web-server/package*.json ./
RUN npm ci
COPY web-server/. .
# This build step is intentionally a no-op, we just need the files and node_modules
RUN npm run build

# Stage 2: Setup the Python MCP server
FROM python:3.11-slim AS mcp-server-stage
WORKDIR /app
# Install curl for the healthcheck and other dependencies
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY flight-findr-mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps
COPY flight-findr-mcp/. .

# Final stage: Combine both services into a single Node.js image
FROM node:20.11.1-slim
WORKDIR /app

# Copy the Node.js app and its dependencies from the first stage
COPY --from=web-server-stage /app /app

# Copy the Python interpreter and installed packages from the second stage
COPY --from=mcp-server-stage /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=mcp-server-stage /usr/local/bin/ /usr/local/bin/

# Copy the Python app code from the second stage
COPY --from=mcp-server-stage /app /app/flight-findr-mcp

ENV GEMINI_API_KEY=$GEMINI_API_KEY
EXPOSE 3000 9999 10000

# Create a start script to run both servers
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo '# Start the Python MCP server in the background' >> /app/start.sh && \
    echo 'python flight-findr-mcp/mcp_server.py --transport http &' >> /app/start.sh && \
    echo '# Start the Node.js web-server in the foreground' >> /app/start.sh && \
    echo 'npm start' >> /app/start.sh && \
    chmod +x /app/start.sh

# Run the start script
CMD ["/app/start.sh"]

