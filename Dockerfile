# This Dockerfile is for the web-server
FROM node:20.11.1-slim
WORKDIR /app
COPY web-server/package*.json ./
RUN npm ci
COPY web-server/. .
EXPOSE 3000
CMD ["npm", "start"]

