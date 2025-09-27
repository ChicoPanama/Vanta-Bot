# Multi-stage build for production optimization
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILDPLATFORM
ARG TARGETPLATFORM

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Install runtime dependencies and security packages
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# Create non-root user with specific UID/GID for security
RUN groupadd -r -g 10001 vanta && useradd -r -g vanta -u 10001 vanta

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/vanta/.local

# Copy application code
COPY --chown=vanta:vanta src/ ./src/
COPY --chown=vanta:vanta config/ ./config/
COPY --chown=vanta:vanta migrations/ ./migrations/
COPY --chown=vanta:vanta main.py ./
COPY --chown=vanta:vanta pyproject.toml ./

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/tmp && \
    chown -R vanta:vanta /app && \
    chmod -R 755 /app && \
    chmod 700 /app/tmp

# Set environment variables for security and performance
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONHASHSEED=random
ENV PATH=/home/vanta/.local/bin:$PATH

# Security labels
LABEL org.opencontainers.image.title="Vanta Bot"
LABEL org.opencontainers.image.description="Professional Trading Bot for Avantis Protocol"
LABEL org.opencontainers.image.vendor="Vanta Bot Team"
LABEL org.opencontainers.image.source="https://github.com/ChicoPanama/Vanta-Bot"
LABEL security.scanning="enabled"

# Switch to non-root user
USER vanta

# Expose port for health checks
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Run the application
CMD ["python", "main.py"]