# Frontend: build the React app, then serve it with Caddy. Caddy also forwards /api to the backend
# and gets a free HTTPS certificate automatically when SITE_ADDRESS is a domain name.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# No VITE_API_URL: the app calls /api on its own domain, which Caddy forwards to the backend
RUN npm run build

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
