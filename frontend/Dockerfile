FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
# nginx processes /etc/nginx/templates/*.template through envsubst at startup,
# substituting env vars (e.g. BACKEND_URL) and writing to /etc/nginx/conf.d/
COPY nginx.conf /etc/nginx/templates/default.conf.template
