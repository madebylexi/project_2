# Use the official Python 3.10-slim image as a base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy all files from the local directory to the container's working directory
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create the /app/files directory with proper permissions
RUN mkdir -p /app/files && chmod 777 /app/files

# Expose the port that Flask will run on
EXPOSE 8083

# Define a build argument for the API key
ARG GEMINI_API
# Set the environment variable.
ENV GEMINI_API=${GEMINI_API}

# Command to run the app with Gunicorn for production use
CMD ["gunicorn", "--bind", "0.0.0.0:8083", "main:app"]
