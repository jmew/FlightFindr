# Use a Python base image
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and their dependencies
RUN playwright install --with-deps chromium

# Copy the rest of the flight-findr-mcp code
COPY . ./

# Expose the port the app runs on
EXPOSE 9999

# Set the command to start the MCP server
CMD ["python", "-u", "mcp_server.py", "--transport", "http"]
