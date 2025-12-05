FROM node:20-alpine AS build
WORKDIR /app

ENV npm_config_cache=/tmp/.npm

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .

ARG API_URL=http://localhost:8000
ENV API_URL=${API_URL}

RUN npm run build

FROM nginx:1.27-alpine AS runtime
ENV PORT=8080

COPY frontend/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
