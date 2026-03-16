FROM node:20-alpine AS builder

WORKDIR /build
RUN corepack enable && corepack prepare pnpm@latest --activate

COPY package.json ./
RUN apk add --no-cache build-base python3
RUN pnpm install --prod=false

COPY . .
RUN pnpm build

FROM nginx:alpine
COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]