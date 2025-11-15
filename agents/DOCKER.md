# Docker Deployment Guide

Run the Strands Agent Framework team in Docker containers for isolated, reproducible deployments.

## Quick Start

### 1. Build the Image

```bash
cd /Users/franksimpson/CascadeProjects/hetzner-hypervisor-setup/agents

# Build the Docker image
docker-compose build
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.template .env

# Edit with your API keys
nano .env
```

Required environment variables:
```bash
# Choose your LLM provider
ANTHROPIC_API_KEY=sk-ant-your-key-here
# OR
OPENAI_API_KEY=sk-your-key-here
# OR AWS credentials for Bedrock
```

### 3. Run the Orchestrator

```bash
# Dry run to preview execution plan
docker-compose run --rm orchestrator python orchestrator.py --dry-run

# Full execution
docker-compose run --rm orchestrator python orchestrator.py

# Specific phase
docker-compose run --rm orchestrator python orchestrator.py --phase 1

# Check status
docker-compose run --rm orchestrator python orchestrator.py --status
```

## Docker Architecture

### Image Details

**Base Image:** `python:3.11-slim`
- Lightweight Debian-based image
- ~150MB compressed
- Includes essential build tools

**Installed Packages:**
- Python 3.11 with pip
- openssh-client (for SSH connections)
- git (for repository operations)
- All Python dependencies from requirements.txt

**Image Size:** ~500-600MB

### Volume Mounts

The Docker container uses volume mounts for:

1. **State Persistence** (`./state` → `/app/state`)
   - Workflow state and checkpoints
   - Survives container restarts
   - Enables recovery

2. **Logs** (`./logs` → `/app/logs`)
   - Orchestrator and team logs
   - Persistent across runs
   - Easy access from host

3. **Checkpoints** (`./checkpoints` → `/app/checkpoints`)
   - Named checkpoints
   - Rollback points

4. **Cache** (`./cache` → `/app/cache`)
   - Performance optimization
   - LLM response caching (if enabled)

5. **SSH Keys** (`~/.ssh` → `/root/.ssh:ro`)
   - Read-only mount
   - Enables SSH to Hetzner server
   - Uses your existing SSH config

6. **Configuration** (`./config.yaml` → `/app/config.yaml:ro`)
   - Custom config override
   - Read-only mount

### Network Configuration

**Mode:** `host`
- Container shares host network stack
- Direct SSH access to Hetzner server
- No port mapping needed
- Simpler networking

**Alternative:** Bridge mode with port mapping (if needed)
```yaml
# In docker-compose.yml
ports:
  - "8080:8080"  # For web dashboard (future)
network_mode: bridge
```

## Usage Examples

### Basic Operations

```bash
# Build and run in one command
docker-compose up --build

# Run specific command
docker-compose run --rm orchestrator python orchestrator.py --help

# Interactive shell in container
docker-compose run --rm orchestrator /bin/bash

# View logs from running container
docker-compose logs -f orchestrator
```

### Phase-by-Phase Execution

```bash
# Phase 1: Security
docker-compose run --rm orchestrator python orchestrator.py --phase 1

# Wait and verify, then Phase 2
docker-compose run --rm orchestrator python orchestrator.py --phase 2

# Continue through all phases...
docker-compose run --rm orchestrator python orchestrator.py --phase 6
```

### Recovery Operations

```bash
# Resume from last checkpoint
docker-compose run --rm orchestrator python orchestrator.py --resume

# Resume from specific team
docker-compose run --rm orchestrator python orchestrator.py --resume-from team_delta

# Rollback to Phase 3
docker-compose run --rm orchestrator python orchestrator.py --rollback 3

# Nuclear reset
docker-compose run --rm orchestrator python orchestrator.py --nuclear-reset
```

### Accessing Container

```bash
# Get a shell inside the container
docker-compose run --rm orchestrator bash

# Inside container:
python orchestrator.py --status
cat logs/orchestrator.log
ls -la state/

# Exit
exit
```

## Advanced Configuration

### Custom Dockerfile

For custom requirements, modify `Dockerfile`:

```dockerfile
# Add additional system packages
RUN apt-get update && apt-get install -y \
    your-package \
    && rm -rf /var/lib/apt/lists/*

# Add additional Python packages
RUN pip install your-python-package

# Custom entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

### Resource Limits

Adjust in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'        # Max 4 CPU cores
      memory: 8G       # Max 8GB RAM
    reservations:
      cpus: '2'        # Min 2 CPU cores
      memory: 4G       # Min 4GB RAM
```

### Environment Variables

Pass additional variables:

```yaml
environment:
  - DEBUG_MODE=true
  - LOG_LEVEL=DEBUG
  - CUSTOM_VAR=value
```

Or from a different env file:
```bash
docker-compose --env-file .env.production run orchestrator
```

### Named Volumes

Use named volumes instead of bind mounts for better portability:

```yaml
volumes:
  - agent_state:/app/state
  - agent_logs:/app/logs

volumes:
  agent_state:
    driver: local
  agent_logs:
    driver: local
```

List volumes:
```bash
docker volume ls
docker volume inspect agents_agent_state
```

## Multi-Container Setup (Future)

For distributed execution:

```yaml
version: '3.8'

services:
  orchestrator:
    # Main coordinator
    build: .
    depends_on:
      - redis
      - postgres

  team_alpha:
    # Dedicated container for Team Alpha
    build: .
    command: ["python", "team_runner.py", "alpha"]

  team_bravo:
    build: .
    command: ["python", "team_runner.py", "bravo"]

  redis:
    image: redis:alpine
    # For distributed state

  postgres:
    image: postgres:14
    # For metrics storage
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/agents.yml
name: Deploy Agents

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: |
          cd agents
          docker build -t hypervisor-agents:${{ github.sha }} .

      - name: Push to registry
        run: |
          docker tag hypervisor-agents:${{ github.sha }} \
            your-registry/hypervisor-agents:latest
          docker push your-registry/hypervisor-agents:latest

      - name: Deploy
        run: |
          docker-compose pull
          docker-compose up -d
```

### Docker Hub

```bash
# Build and tag
docker build -t your-username/hypervisor-agents:latest .

# Push to Docker Hub
docker login
docker push your-username/hypervisor-agents:latest

# Pull on remote server
docker pull your-username/hypervisor-agents:latest
```

## Production Deployment

### On Remote Server

```bash
# SSH to your deployment server
ssh deployment-server

# Clone repository
git clone https://github.com/klogins-hash/hetzner-hypervisor-setup.git
cd hetzner-hypervisor-setup/agents

# Configure
cp .env.template .env
nano .env  # Add production API keys

# Deploy
docker-compose up -d

# Monitor
docker-compose logs -f
```

### Health Monitoring

```bash
# Check container health
docker-compose ps

# Health check endpoint (if implemented)
curl http://localhost:8080/health

# Resource usage
docker stats hypervisor-orchestrator
```

### Automatic Restart

```yaml
# In docker-compose.yml
restart: always  # Always restart on failure
# OR
restart: unless-stopped  # Restart unless manually stopped
# OR
restart: on-failure:3  # Restart up to 3 times on failure
```

## Troubleshooting

### Container Won't Start

```bash
# View logs
docker-compose logs orchestrator

# Check if port is in use
netstat -tulpn | grep 8080

# Remove and rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### SSH Connection Issues

```bash
# Verify SSH keys are mounted
docker-compose run --rm orchestrator ls -la /root/.ssh

# Test SSH from container
docker-compose run --rm orchestrator ssh -v hetzner1

# Check SSH config
docker-compose run --rm orchestrator cat /root/.ssh/config
```

### Permission Issues

```bash
# Fix volume permissions
sudo chown -R $(id -u):$(id -g) logs/ state/ checkpoints/ cache/

# Or run container as your user
user: "${UID}:${GID}"
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Increase limits in docker-compose.yml
memory: 8G

# Or increase Docker daemon limits
# Docker Desktop → Settings → Resources
```

### Image Size Too Large

```bash
# Check image size
docker images | grep hypervisor-agents

# Clean up layers
docker image prune

# Use multi-stage build (advanced)
# See Dockerfile optimization below
```

## Optimization Tips

### Multi-Stage Build

```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "orchestrator.py"]
```

### Layer Caching

```bash
# Order matters - change least frequently first
COPY requirements.txt .        # Changes rarely
RUN pip install -r requirements.txt
COPY . .                      # Changes often
```

### BuildKit

```bash
# Enable BuildKit for faster builds
DOCKER_BUILDKIT=1 docker-compose build

# Or set in ~/.docker/config.json
{
  "features": {
    "buildkit": true
  }
}
```

## Security Best Practices

1. **Don't include .env in image** - ✅ Already in .dockerignore
2. **Use read-only mounts for sensitive data** - ✅ SSH keys are :ro
3. **Run as non-root user (optional)**:
   ```dockerfile
   RUN useradd -m -u 1000 agent
   USER agent
   ```
4. **Scan for vulnerabilities**:
   ```bash
   docker scan hypervisor-agents:latest
   ```
5. **Use secrets for production**:
   ```yaml
   secrets:
     anthropic_key:
       file: ./secrets/anthropic.key
   ```

## Backup & Recovery

### Backup Volumes

```bash
# Backup state
docker run --rm \
  -v $(pwd)/state:/state \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/state-$(date +%Y%m%d).tar.gz /state

# Restore state
docker run --rm \
  -v $(pwd)/state:/state \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/state-20240115.tar.gz -C /
```

### Export Container

```bash
# Export image
docker save hypervisor-agents:latest | gzip > hypervisor-agents.tar.gz

# Import on another system
docker load < hypervisor-agents.tar.gz
```

---

## Summary

**Benefits of Docker Deployment:**
- ✅ Isolated environment
- ✅ Reproducible builds
- ✅ Easy deployment
- ✅ Version control
- ✅ Portable across systems
- ✅ Resource limits
- ✅ Health monitoring

**When to use Docker:**
- Production deployments
- CI/CD pipelines
- Multiple environments
- Team collaboration
- Cloud deployments

**When to use native Python:**
- Local development
- Quick testing
- Custom system integration
- Full system access needed
