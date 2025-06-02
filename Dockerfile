# Use the official Python image from the Docker Hub
FROM python:3.12
LABEL authors="Thomas White"

# Install dependencies
RUN pip3 install flask pyaml

# Create and set the working directory
WORKDIR /app

# Create the config directory
RUN mkdir -p /config

# Add config directory to PYTHONPATH
ENV PYTHONPATH "${PYTHONPATH}:/config"

# Copy the current directory contents into the container at /app
COPY . /app

# Run the command to start the Flask application
CMD ["python", "-u", "app.py"]
