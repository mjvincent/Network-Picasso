FROM node:22-alpine

WORKDIR /app

ENV NETWORK_PICASSO_UI_PORT=5173
ENV NETWORK_PICASSO_API_TARGET=http://network-picasso-api:8787

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.ts tsconfig.json ./
COPY src ./src

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
