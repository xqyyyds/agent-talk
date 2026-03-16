# Build stage
FROM node:20-alpine AS builder

WORKDIR /build

# Install pnpm (using latest specifically for lockfile v9 compatibility)
RUN corepack enable && corepack prepare pnpm@latest --activate

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install system build deps
RUN apk add --no-cache build-base python3

# Install dependencies (config allows build scripts for root user in Docker)
RUN pnpm config set unsafe-perm true && \
    pnpm install --frozen-lockfile --ignore-scripts=false

# Copy source code
COPY . .

# Build the application
RUN pnpm build

# Runtime stage
FROM nginx:alpine

# Copy built files from builder
COPY --from=builder /build/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
