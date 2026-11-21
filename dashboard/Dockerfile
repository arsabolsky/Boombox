# Build Xander's Vue website, then serve the built files with nginx on port 80.
FROM node:22 AS build
WORKDIR /app
COPY frontend/boombox/package.json frontend/boombox/package-lock.json ./
RUN npm ci
COPY frontend/boombox/ ./
RUN npm run build-only

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
