# Docker Deployment Guide

This guide explains how to deploy the STL & STP Manufacturing Calculations API using Docker and Docker Compose.

## 🐳 Docker Setup

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd stl
   ```

2. **Build and run with Docker Compose**
   ```bash
   # Production deployment with Caddy
   docker compose up -d

   # Development with hot reload
   docker compose -f docker-compose.dev.yml up -d

   # Production with Traefik (requires existing Traefik setup)
   docker compose -f docker-compose.prod.yml up -d
   ```

3. **Access the API**
   - API: http://localhost (through Caddy) or http://localhost:7000 (direct)
   - Documentation: http://localhost/docs or http://localhost:7000/docs
   - Health Check: http://localhost/calculate/health or http://localhost:7000/calculate/health

## 📁 File Structure

```
├── docker-compose.yml          # Production deployment with Caddy
├── docker-compose.dev.yml      # Development deployment
├── docker-compose.prod.yml     # Production deployment with Traefik
├── Dockerfile                  # Production image
├── Dockerfile.dev              # Development image
├── Caddyfile                   # Caddy reverse proxy configuration
├── .dockerignore               # Docker ignore file
├── start.sh                    # Linux/Mac startup script
└── start.bat                   # Windows startup script
```

## 🔧 Configuration

### Environment Variables

The following environment variables can be configured:

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `["*"]` | Allowed CORS origins |
| `CORS_ALLOW_CREDENTIALS` | `true` | Allow credentials in CORS |
| `CORS_ALLOW_METHODS` | `["*"]` | Allowed HTTP methods |
| `CORS_ALLOW_HEADERS` | `["*"]` | Allowed headers |

### Reverse Proxy Configuration

#### Caddy (Default Production)
- Automatic HTTPS with Let's Encrypt
- Simple configuration in `Caddyfile`
- Built-in security headers and compression

#### Traefik (Advanced Production)
- Requires existing Traefik setup
- Uses `traefik-global-proxy` network
- Automatic service discovery via labels
- Update domain in `docker-compose.prod.yml` labels

## 🚀 Deployment Options

### Development Deployment

For development with hot reload:

```bash
# Using startup scripts
./start.sh dev
# or on Windows
start.bat dev

# Manual commands
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml logs -f
docker compose -f docker-compose.dev.yml down
```

### Production Deployment

#### Option 1: Caddy (Recommended)
```bash
# Using startup scripts
./start.sh prod
# or on Windows
start.bat prod

# Manual commands
docker compose up -d
docker compose logs -f
docker compose down
```

#### Option 2: Traefik (Advanced)
```bash
# Using startup scripts
./start.sh traefik
# or on Windows
start.bat traefik

# Manual commands
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml down
```

### Scaling

To scale the API service:

```bash
# Scale to 3 instances (Caddy)
docker compose up -d --scale stl-api=3

# Scale to 3 instances (Traefik)
docker compose -f docker-compose.prod.yml up -d --scale stl-api=3
```

## 🔍 Monitoring and Logs

### View Logs

```bash
# Using startup scripts
./start.sh logs
# or on Windows
start.bat logs

# Manual commands
# All services
docker compose logs -f

# Specific service
docker compose logs -f stl-api

# Last 100 lines
docker compose logs --tail=100 stl-api
```

### Health Checks

The application includes health checks:

```bash
# Using startup scripts
./start.sh status
# or on Windows
start.bat status

# Manual commands
# Check container health
docker compose ps

# Manual health check (through Caddy)
curl http://localhost/calculate/health

# Manual health check (direct)
curl http://localhost:7000/calculate/health
```

### Resource Monitoring

```bash
# Container resource usage
docker stats

# Specific container
docker stats stl-manufacturing-api
```

## 🛠️ Maintenance

### Updates

```bash
# Using startup scripts
./start.sh build
# or on Windows
start.bat build

# Manual commands
# Pull latest changes
git pull

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Backup

```bash
# Backup volumes
docker run --rm -v stl_uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads-backup.tar.gz -C /data .
docker run --rm -v stl_logs:/data -v $(pwd):/backup alpine tar czf /backup/logs-backup.tar.gz -C /data .
```

### Cleanup

```bash
# Using startup scripts
./start.sh clean
# or on Windows
start.bat clean

# Manual commands
# Remove unused containers and images
docker system prune -a

# Remove specific volumes
docker volume rm stl_uploads stl_logs
```

## 🔒 Security Considerations

### Production Security

1. **Use HTTPS with automatic certificates (Caddy) or proper SSL setup (Traefik)**
2. **Configure proper CORS origins**
3. **Set up firewall rules**
4. **Regular security updates**
5. **Monitor logs for suspicious activity**
6. **Use Traefik for advanced security features (rate limiting, authentication, etc.)**

### Container Security

- Non-root user in containers
- Minimal base images
- Regular security scans
- Resource limits

## 📊 Performance Tuning

### Caddy Configuration

The included Caddy configuration provides:

- Gzip compression
- Security headers
- Load balancing
- Health checks
- Automatic HTTPS

### Traefik Configuration

For advanced setups, Traefik provides:

- Advanced load balancing
- Rate limiting
- Authentication
- Circuit breakers
- Metrics and monitoring

### Application Tuning

- Adjust worker processes
- Configure memory limits
- Optimize file upload limits
- Set appropriate timeouts

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Check what's using the port
   netstat -tulpn | grep :7000
   
   # Kill the process
   sudo kill -9 <PID>
   ```

2. **Permission denied**
   ```bash
   # Fix volume permissions
   sudo chown -R 1000:1000 uploads/ logs/
   ```

3. **SSL certificate errors**
   ```bash
   # Check certificate files
   ls -la ssl/
   
   # Verify certificate
   openssl x509 -in ssl/cert.pem -text -noout
   ```

### Debug Mode

```bash
# Run in debug mode
docker-compose -f docker-compose.dev.yml up

# Access container shell
docker-compose exec stl-api-dev bash
```

## 📈 Scaling and Load Balancing

### Horizontal Scaling

```bash
# Scale API service
docker-compose up -d --scale stl-api=3

# Update Nginx configuration for load balancing
# (nginx.conf already configured for this)
```

### Load Balancer Configuration

#### Caddy
Caddy automatically handles load balancing when multiple instances are running:

```bash
# Scale to multiple instances
docker compose up -d --scale stl-api=3
```

#### Traefik
Traefik automatically discovers and load balances services via labels in `docker-compose.prod.yml`.

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy to server
        run: |
          docker compose down
          docker compose build --no-cache
          docker compose up -d
```

## 📞 Support

For issues related to Docker deployment:

1. Check the logs: `docker compose logs -f` or use `./start.sh logs`
2. Verify configuration files (`Caddyfile` for Caddy, `docker-compose.prod.yml` for Traefik)
3. Check system resources
4. Review security settings

## 🚀 Quick Commands Reference

```bash
# Development
./start.sh dev          # Start development environment
./start.sh stop         # Stop all services

# Production (Caddy)
./start.sh prod         # Start production with Caddy
./start.sh logs         # View logs
./start.sh status       # Check status

# Production (Traefik)
./start.sh traefik      # Start production with Traefik

# Maintenance
./start.sh build        # Build images
./start.sh clean        # Clean up
./start.sh test         # Run tests
```

---

**Note**: This Docker setup supports both Caddy (simple) and Traefik (advanced) for production. For development, use the development environment which includes hot reload.
