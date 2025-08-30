# Final stage
FROM node:20.11.1-slim
WORKDIR /app
COPY web-server/package*.json ./
RUN npm ci
COPY web-server/. .
EXPOSE 8080
CMD ["npm", "start"]
