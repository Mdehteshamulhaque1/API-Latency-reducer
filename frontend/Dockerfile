FROM node:20-alpine

WORKDIR /app

# Install dependencies first for better layer caching
COPY package.json package-lock.json ./
RUN npm install

# Copy the rest of the app
COPY . .

EXPOSE 5173

# Vite dev server with API proxy (VITE_PROXY_TARGET points at the backend service)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
