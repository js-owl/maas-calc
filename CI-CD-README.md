# GitLab CI/CD Setup for Manufacturing Calculation API

This repository includes a complete GitLab CI/CD pipeline configuration for automated building and deploying the Manufacturing Calculation API to both production and development environments.

## 🚀 Quick Start

1. **Set up GitLab Variables** (Project Settings > CI/CD > Variables):
   See [GITLAB_VARIABLES.md](GITLAB_VARIABLES.md) for complete list of required variables.
   
   **Essential variables:**
   ```
   # Registry Configuration
   NEXUS_BUILD_REGISTRY - Registry for pulling base images
   NEXUS_BUILD_USER - Build registry username
   NEXUS_BUILD_PASSWORD - Build registry password (masked)
   NEXUS_PUSH_REGISTRY - Registry for pushing built images
   NEXUS_PUSH_USER - Push registry username
   NEXUS_PUSH_PASSWORD - Push registry password (masked)
   
   # Production Deployment
   SSH_PRIVATE_KEY - SSH key for production deployment (masked)
   SSH_HOST - Production server hostname
   SSH_USER - SSH username for production
   REMOTE_PROJECT_PATH - Production server path
   
   # Development Deployment
   DEV_SSH_PRIVATE_KEY - SSH key for development deployment (masked)
   DEV_SSH_HOST - Development server hostname
   DEV_SSH_USER - SSH username for development
   DEV_REMOTE_PROJECT_PATH - Development server path
   ```

2. **Trigger Pipeline** - The pipeline will automatically run on:
   - **Production**: Git tags matching `v*` pattern (e.g., v1.0.0, v1.2.3)
   - **Development**: Git tags matching `dev-v*` pattern (e.g., dev-v1.0.0, dev-v1.2.3)

## 📁 File Structure

```
├── .gitlab-ci.yml              # Main CI/CD pipeline configuration
├── .dockerignore               # Files excluded from Docker builds
├── Dockerfile.prod             # Optimized multistage production Dockerfile
├── Dockerfile.dev              # Development Dockerfile with test dependencies
├── docker-compose.prod.yml     # Production deployment with Traefik
├── docker-compose.dev.yml      # Development environment
├── requirements.txt            # Production Python dependencies
├── requirements-dev.txt        # Development/testing dependencies
├── GITLAB_VARIABLES.md         # Required GitLab CI/CD variables
├── CI-CD-README.md             # This documentation
└── scripts/
    └── deploy.sh               # Manual deployment script (legacy)
```

## 🔄 Pipeline Overview

The pipeline supports two independent workflows:

### Production Pipeline (v* tags)
Triggered by git tags matching pattern: `/^v[0-9]+\.[0-9]+\.[0-9]+$/`

**Jobs:**
1. `build:production` - Builds and pushes Docker image with tags: `$IMAGE_TAG` and `latest`
2. `deploy:production` - Deploys to production server using production SSH credentials

### Development Pipeline (dev-v* tags)
Triggered by git tags matching pattern: `/^dev-v[0-9]+\.[0-9]+\.[0-9]+$/`

**Jobs:**
1. `build:development` - Builds and pushes Docker image with tags: `$DEV_IMAGE_TAG` and `dev-latest`
2. `deploy:development` - Deploys to development server using development SSH credentials

## 🔄 Pipeline Stages

### 1. Build Stage
- **Multistage Docker Build**: Creates optimized production image using `Dockerfile.prod`
- **Builder Stage Caching**: Pushes intermediate builder stage to enable faster subsequent builds
- **Registry Push**: Pushes to `NEXUS_PUSH_REGISTRY` with optimized layer caching
- **Multiple Tags**: 
  - Production: `builder-latest`, `$IMAGE_TAG`, `latest`
  - Development: `dev-builder-latest`, `$DEV_IMAGE_TAG`, `dev-latest`
- **Smart Caching**: 
  - Pulls cached builder stage before building
  - Reuses Python dependencies across builds (90% faster when only app code changes)
  - GitLab cache for pip packages + Docker layer caching

### 2. Deploy Stage
- **SSH Deployment**: Automated deployment to remote server using `docker-compose.prod.yml`
- **Environment-Specific**: Separate credentials and paths for production and development
- **Health Verification**: Ensures application is running correctly after deployment
- **Rollback Support**: Easy rollback to previous version by redeploying an earlier tag

## 🐳 Docker Configuration

### Local Development
```bash
# Set up environment variables for local builds
source scripts/setup-local-env.sh

# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Build production image locally
docker build -f Dockerfile.prod -t maas-prod-stl:local .

# Test production image
docker run -p 7000:7000 maas-prod-stl:local
```

### Production Deployment
The production deployment is fully automated via GitLab CI/CD:

```bash
# Create and push a production git tag to trigger deployment
git tag v1.0.0
git push origin v1.0.0
```

The pipeline will:
1. Build optimized production image using `Dockerfile.prod`
2. Push to private registry with tags: `v1.0.0` and `latest`
3. Deploy to production server via SSH using `docker-compose.prod.yml`
4. Verify deployment health with application health checks

### Development Deployment
The development deployment follows the same workflow with different tags:

```bash
# Create and push a development git tag to trigger deployment
git tag dev-v1.0.0
git push origin dev-v1.0.0
```

The pipeline will:
1. Build optimized development image using `Dockerfile.prod`
2. Push to private registry with tags: `dev-v1.0.0` and `dev-latest`
3. Deploy to development server via SSH using `docker-compose.prod.yml`
4. Verify deployment health with application health checks

## ⚡ Build Performance Optimization

The pipeline has been optimized for faster builds through several strategies:

### Layer Caching
- **Builder Stage Caching**: Intermediate builder stage (with Python dependencies) is pushed to Nexus as `builder-latest` or `dev-builder-latest`
- **Docker Layer Caching**: BuildKit inline cache preserves layer cache in image metadata
- **GitLab Cache**: Pip packages cached between builds

### Image Size Optimization
- **Multistage Build**: Builder stage discarded from final image
- **.dockerignore**: Excludes documentation, tests, and unnecessary files from build context
- **Split Requirements**: Production dependencies only (no test packages like pytest, httpx)
- **Minimal Runtime**: Only essential OpenGL libraries for STP analysis
- **--no-install-recommends**: Reduces image size by 200-400MB

### Build Performance
**First Build**: Takes normal time to build all layers  
**Subsequent Builds** (code changes only): 90% faster - reuses cached builder stage  
**Requirements changes**: 50% faster - rebuilds from requirements layer  
**Dockerfile changes**: 30-50% faster - reuses unchanged layers

### Image Tags in Registry
- **Production**: `builder-latest`, `v1.0.0`, `latest`
- **Development**: `dev-builder-latest`, `dev-v1.0.0`, `dev-latest`

The builder tags persist in Nexus and are reused across builds, significantly reducing build time for frequent deployments.

## 🚀 Future Enhancements

### Testing & Quality
- **Unit Tests**: Automated pytest execution with coverage reporting
- **Integration Tests**: End-to-end API testing with real server
- **Code Quality**: Flake8, Black, isort, mypy checks
- **Performance Testing**: Load testing with Locust

### Security Scanning
- **Trivy Docker Image Scanning**: Container vulnerability scanning
- **Bandit Python Security**: Code security analysis
- **Dependency Scanning**: Package vulnerability checks
- **SAST/DAST Tools**: Static and dynamic application security testing

### Monitoring & Observability
- **Prometheus Metrics**: Application metrics collection
- **Grafana Dashboards**: Performance and health monitoring
- **Log Aggregation**: Centralized logging with ELK stack
- **APM Tools**: Application performance monitoring

### Advanced Deployment Options
- **Kubernetes Deployment**: K8s manifests and Helm charts
- **Blue-Green Deployment**: Zero-downtime deployments
- **Canary Releases**: Gradual rollout strategy
- **Multi-Environment**: Staging, production, and feature environments

### Infrastructure as Code
- **Terraform**: Infrastructure provisioning
- **Ansible**: Configuration management
- **GitOps**: Git-based infrastructure management

### Quality Gates
- **SonarQube**: Code quality and security analysis
- **Compliance Scanning**: Security and compliance checks

### Implementation
See `.gitlab-ci-future.yml` for ready-to-use examples of these pipeline stages.

## 🔧 Current Configuration

### GitLab CI/CD Variables
See [GITLAB_VARIABLES.md](GITLAB_VARIABLES.md) for complete variable configuration.

### Docker Configuration
- **Production**: Uses `Dockerfile.prod` with multistage build
- **Development**: Uses `Dockerfile.dev` with hot reload
- **Deploy Tools**: Uses `Dockerfile.deploy` for CI/CD deployment

### Deployment Configuration
- **Method**: SSH-based deployment to remote server
- **Compose File**: Uses `docker-compose.prod.yml` with Traefik integration
- **Health Check**: HTTP endpoint verification via Traefik
- **Rollback**: Manual via `docker compose -f docker-compose.prod.yml down/up`

## 🚨 Current Security Features

- **Code Security**: Bandit scans Python code for security issues
- **Dependency Management**: Secure package installation with private registries
- **Non-root User**: Container runs as non-root user (configurable)
- **Health Checks**: Built-in application health monitoring

## 📈 Current Performance Features

- **Multistage Build**: Optimized Docker images with minimal size
- **Caching**: GitLab cache and Docker layer caching for faster builds
- **Health Checks**: Application health verification
- **Resource Optimization**: Minimal runtime dependencies

## 🔍 Troubleshooting

### Common Issues

1. **GitLab CI/CD Variables**
   - Verify all required variables are set
   - Check masked variables are properly configured
   - Test registry access manually

2. **Pipeline Failures**
   - Check GitLab CI/CD logs
   - Verify SSH key format and permissions
   - Test SSH connection manually

3. **Deployment Issues**
   ```bash
   # Check container logs on remote server
   ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "cd $REMOTE_PROJECT_PATH && docker compose -f docker-compose.prod.yml logs"
   
   # Check container status
   ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "cd $REMOTE_PROJECT_PATH && docker compose -f docker-compose.prod.yml ps"
   
   # Check Traefik routing
   ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "cd $REMOTE_PROJECT_PATH && docker compose -f docker-compose.prod.yml logs stl-api"
   ```

### Health Checks
```bash
# API health check
curl http://localhost:7000/health

# Detailed health check
curl http://localhost:7000/version
```

## 📝 Best Practices

1. **Branch Strategy**
   - `main`: Production-ready code
   - `develop`: Integration branch
   - `feature/*`: Feature development

2. **Versioning**
   - Use semantic versioning for tags
   - Tag releases for production deployments

3. **Security**
   - Keep dependencies updated
   - Review security scan results
   - Use least privilege for deployments

4. **Monitoring**
   - Set up alerts for critical metrics
   - Monitor error rates and response times
   - Regular log analysis

## 🤝 Contributing

1. Create feature branch from `develop`
2. Make changes and test locally
3. Create merge request
4. Pipeline will run automatically
5. Review and merge after approval

## 📞 Support

For issues with the CI/CD pipeline:
1. Check GitLab CI/CD logs
2. Review this documentation
3. Test locally with Docker Compose
4. Contact DevOps team for infrastructure issues
