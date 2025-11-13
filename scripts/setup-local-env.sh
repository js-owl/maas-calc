#!/bin/bash

# Local development environment setup script
# This script sets up environment variables for local Docker builds

echo "Setting up local development environment..."

# Set default values for local development
export PIP_INDEX_URL="https://maasuser:A8rps0Hk@vortex.kronshtadt.ru:8443/repository/pypi-proxy/simple/"
export PIP_TRUSTED_HOST="vortex.kronshtadt.ru"
export APT_PROXY="http://maasuser:A8rps0Hk@dcksv-vortex.int.kronshtadt.ru:8081/repository/apt-proxy-trixie/"

echo "Environment variables set:"
echo "PIP_INDEX_URL: $PIP_INDEX_URL"
echo "PIP_TRUSTED_HOST: $PIP_TRUSTED_HOST"
echo "APT_PROXY: $APT_PROXY"

echo ""
echo "You can now run:"
echo "  docker build -f Dockerfile.prod -t maas-prod-stl:local ."
echo "  docker build -f Dockerfile.dev -t maas-prod-stl:dev ."
echo ""
echo "Or use docker-compose:"
echo "  docker-compose -f docker-compose.dev.yml up -d"
