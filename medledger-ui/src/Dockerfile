# Use a Node image
FROM node:18

WORKDIR /app

# Copy package.json and install deps
COPY package*.json ./
RUN npm install

# Copy the full source
COPY . .

# Expose port
EXPOSE 3000

# Start the React app
CMD ["npm", "start"]
