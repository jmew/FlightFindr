# Node.js runtime stage
FROM node:20.11.1-slim
WORKDIR /app
COPY web-server/package*.json ./
RUN npm ci
COPY web-server/. .

# Python setup stage
FROM python:3.11-slim
WORKDIR /app
COPY flight-findr-mcp/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY flight-findr-mcp/. .

# Final stage
FROM node:20.11.1-slim
WORKDIR /app
COPY --from=0 /app /app
COPY --from=1 /app /app/flight-findr-mcp

ENV GEMINI_API_KEY=$GEMINI_API_KEY
EXPOSE 8080
CMD ["npm", "start"]
