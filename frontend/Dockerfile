FROM node:18-alpine

WORKDIR /app

# Copy dependency manifests
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the source code
COPY . .

# Expose the frontend port (e.g., Vite defaults to 5173, React to 3000)
EXPOSE 3000

# Command to run the development server (adjust for host binding if using Vite)
CMD ["npm", "run", "dev", "--", "--host"]
