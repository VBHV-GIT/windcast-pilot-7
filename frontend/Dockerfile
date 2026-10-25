# ==============================================================================
# WindCast Analytics - Frontend Multi-Stage Production Dockerfile
# Stage 1: Build static assets using Node.js 22 Alpine
# Stage 2: Serve using NGINX Alpine with reverse proxy configuration
# ==============================================================================

# --- Stage 1: Build Environment ---
FROM node:22-alpine AS build

WORKDIR /app

# Copy dependency manifests and install packages
COPY package.json package-lock.json ./
RUN npm ci

# Copy application sources and build production bundle
COPY . .
RUN npm run build

# --- Stage 2: Production Server ---
FROM nginx:alpine AS production

# Remove default NGINX website
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom NGINX configuration (handles SPA routing and /api/ reverse proxy)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Healthcheck probing NGINX /healthz
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
