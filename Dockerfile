# Use a base image that has Python installed
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    pkg-config \
    libhdf5-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Expose the port
EXPOSE 8000

# Run the application
CMD ["python", "app.py"]
