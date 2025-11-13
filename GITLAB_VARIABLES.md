# GitLab CI/CD Variables Configuration

This document lists all required GitLab CI/CD variables for the Manufacturing Calculation API pipeline.

## Required Variables

Set these variables in GitLab Project Settings > CI/CD > Variables:

### Registry Configuration

| Variable | Description | Example | Masked |
|----------|-------------|---------|--------|
| `NEXUS_BUILD_REGISTRY` | Registry for pulling base images | `vortex.kronshtadt.ru:8443` | No |
| `NEXUS_BUILD_USER` | Username for build registry | `maasuser` | No |
| `NEXUS_BUILD_PASSWORD` | Password for build registry | `A8rps0Hk` | **Yes** |
| `NEXUS_PUSH_REGISTRY` | Registry for pushing built images | `nexus.maas.int.kronshtadt.ru:8443` | No |
| `NEXUS_PUSH_USER` | Username for push registry | `maasuser` | No |
| `NEXUS_PUSH_PASSWORD` | Password for push registry | `A8rps0Hk` | **Yes** |

### Docker Configuration

| Variable | Description | Example | Masked |
|----------|-------------|---------|--------|
| `DOCKER_IMAGE` | Docker image version for build stage | `docker:28.4.0` | No |
| `DOCKER_BUILD_TOOLS_IMAGE` | Docker image with deployment tools (SSH, Docker Compose) | `maas-deploy-tools:latest` | No |

### Proxy Configuration (Optional)

| Variable | Description | Example | Masked |
|----------|-------------|---------|--------|
| `APT_PROXY` | APT proxy URL for package installation | `http://proxy.company.com:8080` | No |
| `PIP_INDEX_URL` | PyPI registry URL (if using private registry) | `https://maasuser:password@vortex.kronshtadt.ru:8443/repository/pypi-proxy/simple/` | **Yes** |
| `PIP_TRUSTED_HOST` | PyPI registry host for SSL (if using private registry) | `vortex.kronshtadt.ru` | No |

### Production Deployment Configuration

| Variable | Description | Example | Masked |
|----------|-------------|---------|--------|
| `SSH_PRIVATE_KEY` | SSH private key for production deployment | `-----BEGIN OPENSSH PRIVATE KEY-----...` | **Yes** |
| `SSH_PORT` | SSH port for production server | `22` | No |
| `SSH_HOST` | Production server hostname | `prod-server.company.com` | No |
| `SSH_USER` | SSH username for production deployment | `deploy` | No |
| `REMOTE_PROJECT_PATH` | Path on production server | `/opt/maas-prod-stl` | No |

### Development Deployment Configuration

| Variable | Description | Example | Masked |
|----------|-------------|---------|--------|
| `DEV_SSH_PRIVATE_KEY` | SSH private key for development deployment | `-----BEGIN OPENSSH PRIVATE KEY-----...` | **Yes** |
| `DEV_SSH_PORT` | SSH port for development server | `22` | No |
| `DEV_SSH_HOST` | Development server hostname | `dev-server.company.com` | No |
| `DEV_SSH_USER` | SSH username for development deployment | `deploy` | No |
| `DEV_REMOTE_PROJECT_PATH` | Path on development server | `/opt/maas-prod-stl-dev` | No |

## How to Set Variables

1. Go to your GitLab project
2. Navigate to **Settings** > **CI/CD**
3. Expand **Variables** section
4. Click **Add variable**
5. Fill in the **Key** and **Value**
6. Check **Mask variable** for sensitive values (passwords, keys)
7. Click **Add variable**

## Security Notes

- **Always mask** passwords and private keys
- Use least-privilege credentials
- Rotate credentials regularly
- Consider using GitLab's CI/CD variable types (File, Variable)

## Testing Variables

To test if variables are set correctly, you can add a debug job to your pipeline:

```yaml
debug:variables:
  stage: test
  script:
    - echo "Build registry: $NEXUS_BUILD_REGISTRY"
    - echo "Push registry: $NEXUS_PUSH_REGISTRY"
    - echo "SSH host: $SSH_HOST"
    - echo "Remote path: $REMOTE_PROJECT_PATH"
  only:
    - tags
```

## Troubleshooting

### Common Issues

1. **Authentication failures**: Check username/password combinations
2. **SSH connection issues**: Verify SSH key format and permissions
3. **Registry access denied**: Ensure credentials have proper permissions
4. **Deployment failures**: Check remote server path and permissions

### Debug Commands

```bash
# Test registry access
docker login $NEXUS_BUILD_REGISTRY -u $NEXUS_BUILD_USER

# Test SSH connection
ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "echo 'SSH connection successful'"

# Check remote directory
ssh -p $SSH_PORT $SSH_USER@$SSH_HOST "ls -la $REMOTE_PROJECT_PATH"
```
