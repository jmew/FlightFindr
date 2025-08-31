# Use a Node.js base image
FROM node:20-slim

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm ci

# Copy the rest of the web-server code
COPY . .

# Create .gemini directory and copy GEMINI.md
RUN mkdir -p /root/.gemini
COPY .gemini/GEMINI.md /root/.gemini/GEMINI.md

# Expose the port the app runs on
EXPOSE 3000

# Set the command to start the server
CMD ["npm", "start"]
