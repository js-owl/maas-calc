# Fixing Docker Push Timeouts Behind Traefik

## Problem
When pushing Docker images from the production server to Nexus (running on the same machine behind Traefik), you're experiencing:
- **504 Gateway Timeout**: The push operation times out before completing
- **Broken pipe errors**: TCP connections are being closed prematurely  
- **Client Closed Request**: The client closes the connection before completion
- **DNS resolution failures**: Queries to DNS server `udp:10.33.64.X` are failing

## Root Causes

### 1. **Traefik Timeout Too Short for Large Images**
Docker image pushes can take several minutes, but Traefik's default timeout is only 90 seconds. Large image layers timeout before they can be fully uploaded.

### 2. **Content-Length/Streaming Issues**
Nexus expects content-length headers, but Docker push uses streaming uploads. Traefik may not be configured to handle this correctly.

### 3. **Body Size Limits**
Traefik may have body size limits that prevent large image layers from being uploaded.

### 4. **DNS Resolution Problems**
The concurrent DNS resolution failures suggest network issues that could be contributing to the timeouts.

## Solutions

### Solution 1: Configure Traefik with Extended Timeouts

Add or update Traefik labels for the Nexus registry service in your `docker-compose.yml`:

```yaml
services:
  nexus:
    # ... other config ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.nexus.rule=Host(`nexus.maas.int.kronshtadt.ru`)"
      - "traefik.http.routers.nexus.tls=true"
      - "traefik.http.routers.nexus.entrypoints=websecure"
      - "traefik.http.services.nexus.loadbalancer.server.port=8081"
      # CRITICAL: Add extended timeouts for Docker registry
      - "traefik.http.middlewares.nexus-timeout.retry.attempts=3"
      # Increase timeout to 10 minutes (600 seconds) for large image pushes
      - "traefik.http.middlewares.nexus-timeout.buffering.maxRequestBodyBytes=0"
      - "traefik.http.routers.nexus.middlewares=nexus-timeout"
```

**Alternatively**, if using Traefik's dynamic configuration file (`traefik.yml` or `traefik.yaml`):

```yaml
http:
  middlewares:
    nexus-registry-timeout:
      buffering:
        maxRequestBodyBytes: 0  # No limit on request body
        maxResponseBodyBytes: 0  # No limit on response body
        memRequestBodyBytes: 20971520  # 20MB buffer
        memResponseBodyBytes: 20971520  # 20MB buffer
        retryExpression: "IsNetworkError() && Attempts() < 3"
      forwardAuth:
        address: ""
      headers:
        customRequestHeaders:
          X-Forwarded-For: ""
  routers:
    nexus-registry:
      service: nexus-registry
      rule: "Host(`nexus.maas.int.kronshtadt.ru`) && PathPrefix(`/v2/`)"
      middlewares:
        - nexus-registry-timeout
      tls:
        certResolver: letsencrypt
  services:
    nexus-registry:
      loadBalancer:
        servers:
          - url: http://nexus:8081
        # Extend timeout for slow connections
        passHostHeader: true
```

### Solution 2: Configure Docker daemon.json

On the production server, configure Docker to handle slow connections better:

Edit `/etc/docker/daemon.json`:

```json
{
  "max-concurrent-downloads": 3,
  "max-concurrent-uploads": 3,
  "registry-mirrors": [],
  "insecure-registries": [
    "nexus.maas.int.kronshtadt.ru:8443"
  ],
  "live-restore": true
}
```

Then restart Docker:
```bash
sudo systemctl restart docker
```

### Solution 3: Use Direct Connection (Bypass Traefik for Local Push)

If Traefik continues to be problematic, push directly to the Nexus container using its internal network:

```bash
# From the production server:
# Login to Nexus registry directly (bypass Traefik)
docker login nexus.maas.int.kronshtadt.ru:8443 -u $NEXUS_USER -p $NEXUS_PASSWORD

# Or if on the same Docker network, connect directly to container:
docker exec -it nexus-container-name registry login -u $NEXUS_USER -p $NEXUS_PASSWORD localhost:8081
```

### Solution 4: Configure Traefik Static Configuration

In `traefik.yml` static configuration:

```yaml
global:
  checkNewVersion: false

# Increase timeouts globally
entryPoints:
  web:
    address: ":80"
    http:
      compress: true
      transport:
        respondingTimeouts:
          readTimeout: 600s      # 10 minutes for reads
          writeTimeout: 600s     # 10 minutes for writes
          idleTimeout: 900s      # 15 minutes idle timeout
  websecure:
    address: ":443"
    http:
      compress: true
      transport:
        respondingTimeouts:
          readTimeout: 600s
          writeTimeout: 600s
          idleTimeout: 900s

# Enable access logs for debugging
accessLog: {}

# Increase buffer sizes
buffering:
  maxRequestBodyBytes: 0      # No limit
  maxResponseBodyBytes: 0     # No limit
```

### Solution 5: Fix DNS Issues

The DNS resolution failures could be contributing to the timeouts. Configure Docker to use a reliable DNS server:

Edit `/etc/docker/daemon.json`:

```json
{
  "dns": ["8.8.8.8", "8.8.4.4"]
}
```

Or configure Traefik DNS:

In `traefik.yml`:
```yaml
providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    network: "maas-internal"
    # Use Docker's internal DNS
    exposedByDefault: false
```

## Recommended Quick Fix

The fastest solution is to add Traefik middleware for extended timeouts. Add this to your Nexus Traefik labels:

```yaml
labels:
  # ... existing labels ...
  - "traefik.http.middlewares.nexus-timeout.retry.attempts=5"
  - "traefik.http.routers.nexus.middlewares=nexus-timeout@docker"
```

Then restart Traefik to apply the changes.

## Testing the Fix

After applying the configuration:

1. **Test with a small image first:**
   ```bash
   docker pull alpine:latest
   docker tag alpine:latest nexus.maas.int.kronshtadt.ru:8443/maas-hosted/test:latest
   docker push nexus.maas.int.kronshtadt.ru:8443/maas-hosted/test:latest
   ```

2. **If successful, test with a larger image:**
   ```bash
   docker pull python:3.11-slim
   docker tag python:3.11-slim nexus.maas.int.kronshtadt.ru:8443/maas-hosted/test:latest
   docker push nexus.maas.int.kronshtadt.ru:8443/maas-hosted/test:latest
   ```

3. **Monitor Traefik logs:**
   ```bash
   docker logs -f traefik-container-name
   ```

## Monitoring

Watch for these in Traefik logs:
- Connection timeouts
- 504 errors
- DNS failures
- Buffer overruns

If issues persist after applying these fixes, the problem may be:
- Network instability between Docker and Traefik
- Insufficient resources (CPU/Memory) on the production server
- Nexus registry configuration issues
- Firewall rules interfering with large transfers

