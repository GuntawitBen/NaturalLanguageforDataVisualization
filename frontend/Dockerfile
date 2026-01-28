# Use Node 22 (Required by Vite 6+)
FROM node:22-slim

# Set work directory
WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy project
COPY . .

# Build the application
RUN npm run build

# Expose port (We keep 5173 to avoid requiring DO config changes)
EXPOSE 5173

# Run preview server - serves the built `dist` folder
# We force it to port 5173 to match the EXPOSE instruction
CMD ["npm", "run", "preview", "--", "--port", "5173", "--host"]
