# Use Python 3.11 slim image as base
FROM vortex.kronshtadt.ru:8443/maas-proxy/python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

#ARG maasuser


#RUN echo "deb [trusted=yes] http://dcksv-vortex.int.kronshtadt.ru:8081/repository/apt-proxy-trixie/ stable main" >> /etc/apt/sources.list.d/private-repo.list
#RUN echo "deb http://dcksv-vortex.int.kronshtadt.ru:8081/repository/apt-proxy-trixie/ trixie main restricted universe multiverse" > /etc/apt/sources.list.d/nexus.list
#RUN echo "Acquire::http::Proxy \"http://maasuser:A8rps0Hk@dcksv-vortex.int.kronshtadt.ru:8081/repository/apt-proxy-trixie/\";" > /etc/apt/apt.conf.d/99nexus
RUN echo "deb [trusted=yes] http://maasuser:A8rps0Hk@dcksv-vortex.int.kronshtadt.ru:8081/repository/apt-proxy-trixie/ trixie main contrib non-free-firmware" > /etc/apt/sources.list
RUN echo "deb [trusted=yes] http://maasuser:A8rps0Hk@dcksv-vortex.int.kronshtadt.ru:8081/repository/apt-proxy-trixie/ trixie-updates main contrib non-free-firmware" >> /etc/apt/sources.list
RUN echo "deb [trusted=yes] http://maasuser:A8rps0Hk@dcksv-vortex.int.kronshtadt.ru:8081/repository/apt-proxy-trixie/ trixie-security main contrib non-free-firmware" >> /etc/apt/sources.list

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose port
EXPOSE 7000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:7000/calculate/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7000"]
