FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
# VITE_API_URL is embedded at build time — pass as a Docker build arg.
# Railway: set it to your backend service URL in the service's build variables.
# Docker Compose: defaults to http://localhost:8000 (backend port exposed to host).
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
