# IBM Connect:Direct Prometheus Exporter - Docker Guide

Complete guide for building and running the CD Exporter as a Docker container.

## Prerequisites

- Docker 20.10 or higher
- Docker Compose 2.0 or higher (optional)
- Access to IBM Connect:Direct node

## Project Structure

```
cd-exporter/
├── Dockerfile
├── docker-compose.yml
├── pom.xml
├── CDExporter.java
└── README-Docker.md
```

## Building the Docker Image

### Option 1: Build with Docker

```bash
# Build the image
docker build -t cd-exporter:latest .

# Build with specific tag
docker build -t cd-exporter:1.0.0 .

# Build with no cache
docker build --no-cache -t cd-exporter:latest .
```

### Option 2: Build with specific platform

```bash
# For AMD64
docker build --platform linux/amd64 -t cd-exporter:latest .

# For ARM64
docker build --platform linux/arm64 -t cd-exporter:latest .
```

### Verify the image

```bash
# List images
docker images | grep cd-exporter

# Inspect the image
docker inspect cd-exporter:latest
```

## Running the Container
### Basic Run with Podman

```bash
podman run -d \
  --name cd-exporter \
  -p 9100:9100 \
  cd-exporter:latest \
  cd-node01 1364 admin password123
```

### Run with custom parameters

```bash
podman run -d \
  --name cd-exporter \
  -p 8080:8080 \
  cd-exporter:latest \
  cd-node01 1364 admin password123 8080 30
```

### Run with environment variables

```bash
podman run -d \
  --name cd-exporter \
  -p 9100:9100 \
  -e HTTP_PORT=9100 \
  -e SCRAPE_INTERVAL=60 \
  cd-exporter:latest \
  cd-node01 1364 admin password123
```

### Run in foreground (for testing)

```bash
podman run --rm \
  --name cd-exporter \
  -p 9100:9100 \
  cd-exporter:latest \
  cd-node01 1364 admin password123
```
### Basic Run

```bash
docker run -d \
  --name cd-exporter \
  -p 9100:9100 \
  cd-exporter:latest \
  cd-node01 1364 admin password123
```

### Run with custom parameters

```bash
docker run -d \
  --name cd-exporter \
  -p 8080:8080 \
  cd-exporter:latest \
  cd-node01 1364 admin password123 8080 30
```

### Run with environment variables

```bash
docker run -d \
  --name cd-exporter \
  -p 9100:9100 \
  -e HTTP_PORT=9100 \
  -e SCRAPE_INTERVAL=60 \
  cd-exporter:latest \
  cd-node01 1364 admin password123
```

### Run in foreground (for testing)

```bash
docker run --rm \
  --name cd-exporter \
  -p 9100:9100 \
  cd-exporter:latest \
  cd-node01 1364 admin password123
```

## Docker Compose

### Create docker-compose.yml

```yaml
version: '3.8'

services:
  cd-exporter:
    build: .
    image: cd-exporter:latest
    container_name: cd-exporter
    ports:
      - "9100:9100"
    environment:
      - HTTP_PORT=9100
      - SCRAPE_INTERVAL=60
    command: ["cd-node01", "1364", "admin", "password123", "9100", "60"]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:9100/metrics"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

### Run with Docker Compose

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down

# Restart the service
docker-compose restart

# Rebuild and start
docker-compose up -d --build
```

## Managing the Container

### View logs

```bash
# Follow logs
docker logs -f cd-exporter

# Last 100 lines
docker logs --tail 100 cd-exporter

# Logs with timestamps
docker logs -t cd-exporter
```

### Check container status

```bash
# List running containers
docker ps

# Container details
docker inspect cd-exporter

# Container stats
docker stats cd-exporter

# Health check status
docker inspect --format='{{.State.Health.Status}}' cd-exporter
```

### Stop and remove container

```bash
# Stop container
docker stop cd-exporter

# Remove container
docker rm cd-exporter

# Stop and remove in one command
docker rm -f cd-exporter
```

### Restart container

```bash
# Restart container
docker restart cd-exporter
```

### Execute commands inside container

```bash
# Get a shell
docker exec -it cd-exporter sh

# Check Java version
docker exec cd-exporter java -version

# Test metrics endpoint
docker exec cd-exporter wget -O- http://localhost:9100/metrics
```

## Testing the Exporter

### Test from host machine

```bash
# Check if metrics endpoint is accessible
curl http://localhost:9100/metrics

# Check specific metric
curl http://localhost:9100/metrics | grep ibm_cd_processes

# Pretty print with jq (if available)
curl -s http://localhost:9100/metrics | grep ibm_cd
```

### Test health check

```bash
# Manual health check
docker exec cd-exporter wget --no-verbose --tries=1 --spider http://localhost:9100/metrics && echo "OK" || echo "FAIL"
```

## Production Deployment

### Using secrets for credentials

#### Option 1: Docker Secrets (Swarm mode)

```bash
# Create secrets
echo "admin" | docker secret create cd_username -
echo "password123" | docker secret create cd_password -

# docker-compose.yml with secrets
version: '3.8'

services:
  cd-exporter:
    image: cd-exporter:latest
    ports:
      - "9100:9100"
    secrets:
      - cd_username
      - cd_password
    command: ["cd-node01", "1364", "admin", "password123"]
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure

secrets:
  cd_username:
    external: true
  cd_password:
    external: true
```

#### Option 2: Environment file

Create `.env` file:
```bash
CD_NODE=cd-node01
CD_PORT=1364
CD_USER=admin
CD_PASS=password123
HTTP_PORT=9100
SCRAPE_INTERVAL=60
```

Update docker-compose.yml:
```yaml
version: '3.8'

services:
  cd-exporter:
    image: cd-exporter:latest
    env_file:
      - .env
    ports:
      - "${HTTP_PORT}:${HTTP_PORT}"
    command: ["${CD_NODE}", "${CD_PORT}", "${CD_USER}", "${CD_PASS}", "${HTTP_PORT}", "${SCRAPE_INTERVAL}"]
```

Run:
```bash
docker-compose --env-file .env up -d
```

### Resource limits

```yaml
version: '3.8'

services:
  cd-exporter:
    image: cd-exporter:latest
    ports:
      - "9100:9100"
    command: ["cd-node01", "1364", "admin", "password123"]
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    restart: unless-stopped
```

### Running multiple instances

```yaml
version: '3.8'

services:
  cd-exporter-node1:
    image: cd-exporter:latest
    container_name: cd-exporter-node1
    ports:
      - "9100:9100"
    command: ["cd-node01", "1364", "admin", "password123"]
    restart: unless-stopped

  cd-exporter-node2:
    image: cd-exporter:latest
    container_name: cd-exporter-node2
    ports:
      - "9101:9100"
    command: ["cd-node02", "1364", "admin", "password123"]
    restart: unless-stopped

  cd-exporter-node3:
    image: cd-exporter:latest
    container_name: cd-exporter-node3
    ports:
      - "9102:9100"
    command: ["cd-node03", "1364", "admin", "password123"]
    restart: unless-stopped
```

## Integration with Prometheus

### Prometheus configuration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'ibm-connect-direct'
    static_configs:
      - targets: 
          - 'cd-exporter:9100'  # If in same Docker network
          # OR
          - 'localhost:9100'     # If on host network
        labels:
          node: 'cd-node01'
          environment: 'production'
```

### Complete monitoring stack with Docker Compose

```yaml
version: '3.8'

services:
  cd-exporter:
    build: .
    image: cd-exporter:latest
    container_name: cd-exporter
    command: ["cd-node01", "1364", "admin", "password123"]
    networks:
      - monitoring
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - monitoring
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - monitoring
    restart: unless-stopped

networks:
  monitoring:
    driver: bridge

volumes:
  prometheus_data:
  grafana_data:
```

Start the complete stack:
```bash
docker-compose up -d
```

Access:
- **CD Exporter metrics**: http://localhost:9100/metrics
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

## Troubleshooting

### Container won't start

```bash
# Check logs
docker logs cd-exporter

# Check if port is already in use
netstat -tuln | grep 9100
# OR
lsof -i :9100

# Run in foreground to see errors
docker run --rm cd-exporter:latest cd-node01 1364 admin password123
```

### Cannot connect to Connect:Direct node

```bash
# Test network connectivity from container
docker exec cd-exporter ping cd-node01

# Check if dmcli is available
docker exec cd-exporter which dmcli
```

### Metrics not updating

```bash
# Check if container is healthy
docker inspect --format='{{.State.Health.Status}}' cd-exporter

# Check logs for errors
docker logs cd-exporter | grep ERROR

# Verify scrape interval
docker logs cd-exporter | grep "Scrape interval"
```

### High memory usage

```bash
# Check container stats
docker stats cd-exporter

# Set memory limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 512M
```

## Cleanup

### Remove everything

```bash
# Stop and remove container
docker rm -f cd-exporter

# Remove image
docker rmi cd-exporter:latest

# Remove with docker-compose
docker-compose down -v

# Remove all unused images and containers
docker system prune -a
```

## Security Best Practices

1. **Don't hardcode credentials** - Use environment variables or secrets
2. **Run as non-root user** - Already configured in Dockerfile
3. **Use specific image tags** - Avoid `latest` in production
4. **Scan images for vulnerabilities**:
   ```bash
   docker scan cd-exporter:latest
   ```
5. **Use read-only filesystem** (if possible):
   ```bash
   docker run --read-only -d cd-exporter:latest cd-node01 1364 admin pass
   ```
6. **Limit container capabilities**:
   ```bash
   docker run --cap-drop=ALL -d cd-exporter:latest cd-node01 1364 admin pass
   ```

## Publishing to Registry

### Docker Hub

```bash
# Tag the image
docker tag cd-exporter:latest yourusername/cd-exporter:latest
docker tag cd-exporter:latest yourusername/cd-exporter:1.0.0

# Login to Docker Hub
docker login

# Push the image
docker push yourusername/cd-exporter:latest
docker push yourusername/cd-exporter:1.0.0
```

### Private Registry

```bash
# Tag for private registry
docker tag cd-exporter:latest registry.example.com/cd-exporter:latest

# Login to private registry
docker login registry.example.com

# Push to private registry
docker push registry.example.com/cd-exporter:latest
```

## Support

For issues or questions, please refer to your organization's support channels.