# Node.js build stage
FROM node:20-slim AS builder
WORKDIR /app
COPY web-server/package*.json ./
RUN npm ci
COPY web-server/. .
RUN npm run build

# Python setup stage
FROM python:3.11-slim
WORKDIR /app
COPY flight-findr-mcp/. .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM node:20-slim
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json .
COPY --from=0 /usr/local/bin/ /usr/local/bin/
COPY --from=0 /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY flight-findr-mcp/. .

ENV GEMINI_API_KEY=$GEMINI_API_KEY
EXPOSE 8080
CMD ["node", "dist/index.js"]
