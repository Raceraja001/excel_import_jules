# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed by some Python packages
# (e.g., for database connectors or cryptography)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     libpq-dev \
#     && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY ./app /app/app
COPY ./alembic /app/alembic
COPY alembic.ini /app/alembic.ini

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable (optional, can be set at runtime)
# ENV MODULE_NAME="app.main"
# ENV VARIABLE_NAME="app"

# Run app.main.py when the container launches
# The command uses Uvicorn to run the FastAPI application.
# --host 0.0.0.0 makes the server accessible externally.
# --port 8000 specifies the port.
# --reload is useful for development but should be removed for production.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
