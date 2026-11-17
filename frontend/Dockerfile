FROM node:24-bookworm-slim

WORKDIR /app

ENV EXPO_NO_TELEMETRY=1

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

EXPOSE 8081

CMD ["npx", "expo", "start", "--tunnel", "--port", "8081"]