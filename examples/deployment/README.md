# Deployment Examples

Deploy apps, services, and infrastructure.

## 📁 Examples

| File | Description |
|------|-------------|
| [docker_deploy.py](docker_deploy.py) | Deploy with Docker |
| [kubernetes_deploy.py](kubernetes_deploy.py) | Kubernetes deployments |
| [ssh_deploy.sh](ssh_deploy.sh) | SSH-based deployment |
| [webapp_scaffold.py](webapp_scaffold.py) | Generate web app structure |
| [service_monitor.py](service_monitor.py) | Monitor deployed services |

## 🚀 Quick Start

```bash
# Deploy Docker container
sq deploy docker --image myapp:latest --port 8080

# Kubernetes deployment
sq deploy k8s --manifest deployment.yaml

# SSH deploy
sq ssh prod.server.com --upload ./dist --remote /var/www/app

# Create web app
sq webapp create --name myapp --template fastapi

# Monitor service
sq service status --url https://myapp.com/health
```

## 🔧 Configuration

```bash
# SSH
export SSH_KEY=~/.ssh/id_rsa
export SSH_USER=deploy

# Kubernetes
export KUBECONFIG=~/.kube/config

# Docker Registry
export DOCKER_REGISTRY=registry.example.com
```

## 📚 Related Documentation

- [Deploy Component](../../docs/v2/components/DEPLOY_COMPONENT.md)
- [SSH Component](../../docs/v2/components/SSH_COMPONENT.md)
- [Docker Quickstart](../../docs/v2/guides/DOCKER_QUICKSTART.md)

## 🔗 Related Examples

- [Automation](../automation/) - CI/CD automation
- [Communication](../communication/) - Deploy notifications

## 🔗 Source Code

- [streamware/components/deploy.py](../../streamware/components/deploy.py)
- [streamware/components/ssh.py](../../streamware/components/ssh.py)
- [streamware/components/service.py](../../streamware/components/service.py)
