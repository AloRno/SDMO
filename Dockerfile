# --- Build stage ---
# Use a full image with build tools so mlkem's C extension compiles cleanly
FROM python:3.12-slim AS builder

# Install C build tools needed by mlkem and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install --no-warn-script-location -r requirements.txt


# --- Runtime stage ---
# Lean final image — no compiler needed at runtime
FROM python:3.12-slim AS runtime

# Copy installed packages from build stage
COPY --from=builder /install /usr/local

# Create app directory
WORKDIR /app

# Copy only what's needed to run the pipeline
COPY src/       ./src/
COPY tests/     ./tests/

# Pre-create output directories so the app doesn't need to mkdir at runtime
RUN mkdir -p Output_Components/gateway Output_Components/cloud

# The source files import each other by name (e.g. from legacy_device import ...),
# so the working directory must be src/ when running main.py
WORKDIR /app/src

CMD ["python", "main.py"]
