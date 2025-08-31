# Stage 1: Build the application
FROM node:20-slim AS builder
WORKDIR /app

# Copy package configuration and install all dependencies
COPY package*.json ./
RUN npm ci

# Copy source code and tsconfig
COPY src ./src
COPY tsconfig.json ./

# Build the TypeScript project
RUN npm run build

# Stage 2: Create the production image
FROM node:20-slim
WORKDIR /app

# Copy package configuration and install production dependencies only
COPY package*.json ./
RUN npm ci --omit=dev

# Copy the built application from the builder stage
COPY --from=builder /app/dist ./dist

# Copy the GEMINI.md file
RUN mkdir -p /root/.gemini
COPY .gemini/GEMINI.md /root/.gemini/GEMINI.md

# Expose the port and start the server
EXPOSE 3000
CMD ["npm", "start"]