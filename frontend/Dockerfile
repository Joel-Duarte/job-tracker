# ==============================================================================
# Build Stage: Compile Vite Vue.js SPA
# ==============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Cache package installation
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and compile production bundle
COPY . ./
RUN npm run build

# ==============================================================================
# Runtime Stage: Serve via Nginx
# ==============================================================================
FROM nginx:1.27-alpine AS runtime

# Install curl for container healthchecks
RUN apk add --no-cache curl

# Copy custom Nginx configuration and static assets
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

# Health check probing Nginx /healthz endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
