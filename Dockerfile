# ---- Builder Stage ----
# This stage installs all dependencies and builds the application.
FROM python:3.11-bookworm AS builder

# Install Node.js, npm, and build essentials
RUN apt-get update && \
    apt-get install -y curl gnupg nodejs npm && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies into a virtual environment
COPY flight-findr-mcp/requirements.txt ./
RUN python -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install --no-cache-dir -r requirements.txt && \
    # Install ONLY chromium and its dependencies
    playwright install --with-deps chromium

# Install Node.js dependencies for the web-server
COPY web-server/package*.json ./
RUN npm ci

# ---- Final Stage ----
# This stage creates the lean, final production image.
FROM python:3.11-bookworm

# Install only Node.js and supervisor, which are needed at runtime
RUN apt-get update && \
    apt-get install -y nodejs supervisor && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/venv /app/venv

# Copy the Playwright browser from the builder stage
# The path may vary, check with `playwright install --dry-run chromium` if needed
COPY --from=builder /root/.cache/ms-playwright /root/.cache/ms-playwright

# Copy the web-server node_modules from the builder stage
COPY --from=builder /app/node_modules ./node_modules

# Copy application code
COPY flight-findr-mcp/ ./flight-findr-mcp
COPY web-server/ ./web-server

# Copy the supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set environment variables
# Activate the virtual environment and set the Playwright path
ENV PATH="/app/venv:$PATH"
ENV PLAYWRIGHT_BROWSERS_PATH="/root/.cache/ms-playwright"
ENV GEMINI_API_KEY=$GEMINI_API_KEY

EXPOSE 3000 9999 10000

# Run supervisor to start both services
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]