# Multi-stage build for Next.js standalone output
# Build context: repo root (required for @samaa/shared workspace dependency)

# ── Stage 1: Install dependencies ────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app

# Copy root workspace files needed for npm workspace resolution
COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/
COPY packages/shared/package.json ./packages/shared/

# Install all workspace dependencies
RUN npm ci --workspace=apps/web --include-workspace-root 2>/dev/null || npm ci

# ── Stage 2: Build ───────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app

# Build-time environment variables
ARG NEXT_PUBLIC_API_URL=/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NODE_ENV=production

COPY --from=deps /app/node_modules ./node_modules

# Copy workspace node_modules to web app directory for Next.js to find dependencies
COPY --from=deps /app/node_modules ./apps/web/node_modules

# Copy shared package source (used as workspace dep)
COPY packages/shared/ ./packages/shared/

# Copy web app source
COPY apps/web/ ./apps/web/

# Build Next.js (standalone output)
WORKDIR /app/apps/web
RUN npm run build

# ── Stage 3: Production runtime ──────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copy standalone output + static assets
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./.next/static
COPY --from=builder /app/apps/web/public ./public

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Start standalone server
CMD ["node", "server.js"]
