# Stage 1: Build stage
FROM python:3.10-slim AS builder

# Set the working directory
WORKDIR /app

# Install runtime dependencies (minimal!)
RUN apt-get update && apt-get install -y \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Install and cache dependencies
COPY requirements.txt /app/
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Final stage
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# Copy only the needed wheels from the builder stage
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt /app/requirements.txt

# Install the wheels
RUN pip install --no-cache /wheels/*

# Copy the application code
COPY . /app

# Expose port 5000
EXPOSE 5000

# Define environment variable
ENV FLASK_ENV=development

ENV FLASK_APP=manage.py

# Run the command to start the application
CMD ["python", "manage.py", "runserver","--host=0.0.0.0"]

