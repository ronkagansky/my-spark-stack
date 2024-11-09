# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy frontend files
COPY frontend/package*.json ./
RUN npm install

COPY frontend/ .
RUN npm run build

# Stage 2: Build backend and serve frontend
FROM python:3.11-slim
WORKDIR /app

# Install Node.js for serving frontend
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install dependencies
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/frontend/.next /app/frontend/.next
COPY --from=frontend-builder /app/frontend/public /app/frontend/public
COPY --from=frontend-builder /app/frontend/package*.json /app/frontend/
COPY --from=frontend-builder /app/frontend/next.config.mjs /app/frontend/

# Install frontend production dependencies
WORKDIR /app/frontend
RUN npm install --production

# Back to app root
WORKDIR /app

# Create start script
RUN echo '#!/bin/bash\n\
    cd /app/frontend && npm start & \n\
    cd /app && uvicorn main:app --host 0.0.0.0 --port $PORT\n\
    ' > /app/start.sh && chmod +x /app/start.sh

# Set environment variables
ENV PORT=8000
ENV NODE_ENV=production

# Start both servers
CMD ["/app/start.sh"] 