# Stage 1: Build the Node.js web-server
FROM node:20.11.1-slim AS web-server-build
WORKDIR /app
COPY web-server/package*.json ./
RUN npm ci
COPY web-server/. .
# This build step is intentionally a no-op
RUN npm run build

# Stage 2: Setup the Python MCP server
FROM python:3.11-slim AS mcp-server-build
WORKDIR /app
COPY flight-findr-mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY flight-findr-mcp/. .

# Final stage: Combine both services
FROM node:20.11.1-slim
WORKDIR /app

# Copy the Node.js app and its dependencies
COPY --from=web-server-build /app /app

# Copy the Python interpreter and installed packages
COPY --from=mcp-server-build /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=mcp-server-build /usr/local/bin/ /usr/local/bin/

# Copy the Python app code
COPY --from=mcp-server-build /app /app/flight-findr-mcp

ENV GEMINI_API_KEY=$GEMINI_API_KEY
EXPOSE 8080 10000 9999

# We need a way to run both servers. We'll use a simple script.
# First, create the script.
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo 'python flight-findr-mcp/mcp_server.py --transport http &' >> /app/start.sh && \
    echo 'npm start' >> /app/start.sh && \
    chmod +x /app/start.sh

# Run the start script
CMD ["/app/start.sh"]

