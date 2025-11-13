#!/bin/bash

# Deployment script for Manufacturing Calculation API
# This script can be used in GitLab CI/CD or manually

set -e

# Configuration
IMAGE_NAME="${IMAGE_NAME:-maas-prod-stl}"
REGISTRY_URL="${REGISTRY_URL:-vortex.kronshtadt.ru:8443/maas-proxy}"
FULL_IMAGE_NAME="${REGISTRY_URL}/${IMAGE_NAME}"
TAG="${CI_COMMIT_SHA:-latest}"
ENVIRONMENT="${ENVIRONMENT:-staging}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are available
check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! command -v kubectl &> /dev/null && [ "$ENVIRONMENT" = "production" ]; then
        log_warn "kubectl not found. Kubernetes deployment will be skipped."
    fi
    
    log_info "Dependencies check completed"
}

# Pull latest image
pull_image() {
    log_info "Pulling image: ${FULL_IMAGE_NAME}:${TAG}"
    
    if ! docker pull "${FULL_IMAGE_NAME}:${TAG}"; then
        log_error "Failed to pull image ${FULL_IMAGE_NAME}:${TAG}"
        exit 1
    fi
    
    log_info "Image pulled successfully"
}

# Run health check
health_check() {
    local container_name="maas-api-${ENVIRONMENT}-${TAG}"
    local port="7000"
    
    log_info "Starting container for health check..."
    
    # Start container
    docker run -d --name "${container_name}" -p "${port}:7000" "${FULL_IMAGE_NAME}:${TAG}"
    
    # Wait for container to start
    log_info "Waiting for container to start..."
    sleep 30
    
    # Health check
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log_info "Health check attempt $attempt/$max_attempts"
        
        if curl -f "http://localhost:${port}/health" > /dev/null 2>&1; then
            log_info "Health check passed!"
            break
        else
            if [ $attempt -eq $max_attempts ]; then
                log_error "Health check failed after $max_attempts attempts"
                docker logs "${container_name}"
                docker stop "${container_name}" || true
                docker rm "${container_name}" || true
                exit 1
            fi
            log_warn "Health check failed, retrying in 10 seconds..."
            sleep 10
            attempt=$((attempt + 1))
        fi
    done
    
    # Clean up test container
    docker stop "${container_name}" || true
    docker rm "${container_name}" || true
    
    log_info "Health check completed successfully"
}

# Deploy to Kubernetes (if kubectl is available)
deploy_kubernetes() {
    if ! command -v kubectl &> /dev/null; then
        log_warn "kubectl not available, skipping Kubernetes deployment"
        return
    fi
    
    log_info "Deploying to Kubernetes..."
    
    # Update image in deployment
    kubectl set image deployment/maas-api maas-api="${FULL_IMAGE_NAME}:${TAG}" -n "${ENVIRONMENT}"
    
    # Wait for rollout to complete
    kubectl rollout status deployment/maas-api -n "${ENVIRONMENT}" --timeout=300s
    
    log_info "Kubernetes deployment completed"
}

# Deploy using Docker Compose
deploy_docker_compose() {
    log_info "Deploying using Docker Compose..."
    
    # Update image in docker-compose file
    export IMAGE_TAG="${FULL_IMAGE_NAME}:${TAG}"
    
    # Deploy
    docker-compose -f docker-compose.${ENVIRONMENT}.yml up -d
    
    log_info "Docker Compose deployment completed"
}

# Main deployment function
deploy() {
    log_info "Starting deployment to ${ENVIRONMENT} environment"
    log_info "Image: ${FULL_IMAGE_NAME}:${TAG}"
    
    check_dependencies
    pull_image
    health_check
    
    # Choose deployment method based on environment
    case "${ENVIRONMENT}" in
        "production")
            deploy_kubernetes
            ;;
        "staging")
            deploy_docker_compose
            ;;
        *)
            log_warn "Unknown environment: ${ENVIRONMENT}"
            log_info "Skipping deployment"
            ;;
    esac
    
    log_info "Deployment to ${ENVIRONMENT} completed successfully!"
}

# Rollback function
rollback() {
    local previous_tag="${1:-latest}"
    
    log_info "Rolling back to previous version: ${previous_tag}"
    
    # Update image to previous version
    export IMAGE_TAG="${FULL_IMAGE_NAME}:${previous_tag}"
    
    case "${ENVIRONMENT}" in
        "production")
            kubectl set image deployment/maas-api maas-api="${FULL_IMAGE_NAME}:${previous_tag}" -n "${ENVIRONMENT}"
            kubectl rollout status deployment/maas-api -n "${ENVIRONMENT}" --timeout=300s
            ;;
        "staging")
            docker-compose -f docker-compose.${ENVIRONMENT}.yml up -d
            ;;
    esac
    
    log_info "Rollback completed"
}

# Main script logic
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "rollback")
        rollback "$2"
        ;;
    "health-check")
        health_check
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|health-check} [rollback-tag]"
        echo ""
        echo "Environment variables:"
        echo "  IMAGE_NAME: Docker image name (default: maas-prod-stl)"
        echo "  REGISTRY_URL: Docker registry URL"
        echo "  TAG: Image tag (default: latest or CI_COMMIT_SHA)"
        echo "  ENVIRONMENT: Target environment (default: staging)"
        exit 1
        ;;
esac
