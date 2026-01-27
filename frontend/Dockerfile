# Use Node 18
FROM node:18-slim

# Set work directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy project
COPY . .

# Expose port (Vite default is 5173)
EXPOSE 5173

# Run dev server - usually better for dev environments
CMD ["npm", "run", "dev", "--", "--host"]
