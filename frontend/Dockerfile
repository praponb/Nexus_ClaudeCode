# syntax=docker/dockerfile:1
FROM node:22-slim AS base

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

# --host is required: `nuxt dev` binds to localhost only by default, which
# would be unreachable from outside the container despite the port mapping.
FROM base AS dev
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM base AS build
RUN npm run build

# Nitro's node-server preset (Nuxt's default) bundles its own runtime
# dependencies into .output/server, so the production image doesn't need
# node_modules or a second `npm install` -- just the build output.
FROM node:22-slim AS production
WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY --from=build /app/.output ./.output
USER appuser
ENV HOST=0.0.0.0 PORT=3000
EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
