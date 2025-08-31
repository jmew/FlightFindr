# This Dockerfile is for the mcp-server
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps
EXPOSE 9999
CMD ["python", "mcp_server.py", "--transport", "http", "--host", "0.0.0.0"]
