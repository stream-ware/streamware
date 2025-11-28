# Deploy Component - Kubernetes, Docker Compose, Swarm

Komponent do deploymentu aplikacji na różne platformy używając Streamware Quick.

## 🚀 Quick Start

### Kubernetes

```bash
# Apply deployment
sq deploy k8s --apply --file deployment.yaml --namespace production

# Scale
sq deploy k8s --scale 5 --name myapp

# Update image
sq deploy k8s --update --name myapp --image myapp:v2.0

# Rollback
sq deploy k8s --rollback --name myapp

# Status
sq deploy k8s --status --namespace production

# Logs
sq deploy k8s --logs --name myapp

# Delete
sq deploy k8s --delete --file deployment.yaml
```

### Docker Compose

```bash
# Deploy
sq deploy compose --apply --file docker-compose.yml --project myapp

# Scale service
sq deploy compose --scale 3 --name web --project myapp

# Status
sq deploy compose --status --project myapp

# Stop
sq deploy compose --delete --project myapp
```

### Docker Swarm

```bash
# Deploy stack
sq deploy swarm --apply --file docker-compose.yml --stack mystack

# Remove stack
sq deploy swarm --delete --stack mystack
```

## 📋 Kubernetes Examples

### Basic Deployment

```bash
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 8080

# Deploy
sq deploy k8s --apply --file deployment.yaml --namespace production
```

### Update Deployment

```bash
# Update image
sq deploy k8s --update \
  --name myapp \
  --image myregistry.io/myapp:v2.0 \
  --namespace production

# Check rollout status
kubectl rollout status deployment/myapp -n production
```

### Scale Deployment

```bash
# Scale to 10 replicas
sq deploy k8s --scale 10 --name myapp --namespace production

# Scale down to 2
sq deploy k8s --scale 2 --name myapp --namespace production
```

### Rollback Deployment

```bash
# Rollback to previous version
sq deploy k8s --rollback --name myapp --namespace production

# Check rollout history
kubectl rollout history deployment/myapp -n production
```

### Multi-Environment Deployment

```bash
#!/bin/bash
# Deploy to multiple environments

APP_NAME="myapp"
VERSION="v2.0"

# Development
sq deploy k8s --apply \
  --file k8s/deployment.yaml \
  --namespace dev \
  --context dev-cluster

# Staging  
sq deploy k8s --apply \
  --file k8s/deployment.yaml \
  --namespace staging \
  --context staging-cluster

# Production (with confirmation)
read -p "Deploy to production? (yes/no) " confirm
if [[ "$confirm" == "yes" ]]; then
  sq deploy k8s --apply \
    --file k8s/deployment.yaml \
    --namespace production \
    --context prod-cluster
  
  # Notify team
  sq slack deployments \
    --message "✓ Deployed $APP_NAME:$VERSION to production" \
    --token $SLACK_TOKEN
fi
```

## 🎯 Deployment Strategies

### Blue-Green Deployment

```bash
#!/bin/bash
# Blue-Green deployment strategy

APP_NAME="myapp"
NEW_VERSION="v2.0"
NAMESPACE="production"

# 1. Deploy green (new version)
sq deploy k8s --apply \
  --file deployment-green.yaml \
  --namespace $NAMESPACE

# 2. Wait for green to be ready
kubectl wait --for=condition=available \
  deployment/myapp-green \
  -n $NAMESPACE \
  --timeout=300s

# 3. Test green deployment
if curl -f http://myapp-green-service/health; then
  echo "✓ Green deployment healthy"
  
  # 4. Switch traffic to green
  kubectl patch service myapp \
    -n $NAMESPACE \
    -p '{"spec":{"selector":{"version":"green"}}}'
  
  echo "✓ Traffic switched to green"
  
  # 5. Remove blue (old version) after cooldown
  sleep 300
  sq deploy k8s --delete \
    --name myapp-blue \
    --namespace $NAMESPACE
  
  echo "✓ Blue-Green deployment complete"
else
  echo "✗ Green deployment failed"
  sq deploy k8s --delete \
    --name myapp-green \
    --namespace $NAMESPACE
  exit 1
fi
```

### Canary Deployment

```bash
#!/bin/bash
# Canary deployment - gradual rollout

APP_NAME="myapp"
NEW_VERSION="v2.0"
NAMESPACE="production"

# 1. Deploy canary with 10% traffic
sq deploy k8s --apply \
  --file deployment-canary.yaml \
  --namespace $NAMESPACE

sq deploy k8s --scale 1 \
  --name myapp-canary \
  --namespace $NAMESPACE

echo "Canary deployed with 10% traffic"

# 2. Monitor for 10 minutes
sleep 600

# 3. Check error rate from monitoring
error_rate=$(curl -s http://monitoring/api/errors?service=myapp-canary | jq -r '.rate')

if (( $(echo "$error_rate < 0.01" | bc -l) )); then
  echo "✓ Canary looks good (error rate: $error_rate)"
  
  # 4. Gradually increase canary traffic
  for replicas in 3 5 10; do
    echo "Scaling canary to $replicas replicas..."
    sq deploy k8s --scale $replicas \
      --name myapp-canary \
      --namespace $NAMESPACE
    
    # Monitor each stage
    sleep 300
  done
  
  # 5. Promote canary to stable
  kubectl patch deployment myapp \
    -n $NAMESPACE \
    --patch "$(cat deployment-canary.yaml)"
  
  # 6. Remove canary deployment
  sq deploy k8s --delete \
    --name myapp-canary \
    --namespace $NAMESPACE
  
  echo "✓ Canary deployment successful"
else
  echo "✗ Canary has high error rate: $error_rate"
  echo "Rolling back..."
  
  sq deploy k8s --delete \
    --name myapp-canary \
    --namespace $NAMESPACE
  
  sq slack alerts \
    --message "❌ Canary deployment failed for $APP_NAME:$NEW_VERSION" \
    --token $SLACK_TOKEN
  
  exit 1
fi
```

### Rolling Update

```bash
#!/bin/bash
# Rolling update with monitoring

APP_NAME="myapp"
NEW_VERSION="v2.0"
NAMESPACE="production"

# 1. Update deployment
sq deploy k8s --update \
  --name $APP_NAME \
  --image myregistry.io/$APP_NAME:$NEW_VERSION \
  --namespace $NAMESPACE

# 2. Watch rollout
kubectl rollout status deployment/$APP_NAME -n $NAMESPACE

# 3. Verify deployment
if kubectl get deployment $APP_NAME -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Available")].status}' | grep -q "True"; then
  echo "✓ Deployment successful"
  
  # 4. Run smoke tests
  if ./run-smoke-tests.sh; then
    echo "✓ Smoke tests passed"
    
    sq slack deployments \
      --message "✓ Successfully deployed $APP_NAME:$NEW_VERSION" \
      --token $SLACK_TOKEN
  else
    echo "✗ Smoke tests failed, rolling back"
    sq deploy k8s --rollback --name $APP_NAME --namespace $NAMESPACE
    exit 1
  fi
else
  echo "✗ Deployment failed"
  sq deploy k8s --rollback --name $APP_NAME --namespace $NAMESPACE
  exit 1
fi
```

## 🐳 Docker Compose Examples

### Basic Compose Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    deploy:
      replicas: 3
  
  api:
    image: myapp:latest
    environment:
      - DATABASE_URL=postgres://db/myapp
    depends_on:
      - db
  
  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=myapp
    volumes:
      - db-data:/var/lib/postgresql/data

volumes:
  db-data:
```

```bash
# Deploy
sq deploy compose --apply \
  --file docker-compose.yml \
  --project myapp

# Scale web service
sq deploy compose --scale 5 \
  --name web \
  --project myapp

# Check status
sq deploy compose --status --project myapp

# View logs
docker-compose -p myapp logs -f web

# Stop
sq deploy compose --delete --project myapp
```

### Compose with Environment Files

```bash
# Production deployment
sq deploy compose --apply \
  --file docker-compose.prod.yml \
  --project myapp-prod

# Development deployment  
sq deploy compose --apply \
  --file docker-compose.dev.yml \
  --project myapp-dev
```

## 🔄 CI/CD Integration

### GitLab CI/CD

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

deploy_staging:
  stage: deploy
  script:
    - sq deploy k8s --update \
        --name myapp \
        --image $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA \
        --namespace staging \
        --context staging-cluster
  only:
    - develop

deploy_production:
  stage: deploy
  script:
    - sq deploy k8s --update \
        --name myapp \
        --image $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA \
        --namespace production \
        --context prod-cluster
  only:
    - main
  when: manual
```

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build image
        run: |
          docker build -t myregistry.io/myapp:${{ github.sha }} .
          docker push myregistry.io/myapp:${{ github.sha }}
      
      - name: Deploy to Kubernetes
        run: |
          sq deploy k8s --update \
            --name myapp \
            --image myregistry.io/myapp:${{ github.sha }} \
            --namespace production
      
      - name: Notify Slack
        if: success()
        run: |
          sq slack deployments \
            --message "✓ Deployed ${{ github.sha }} to production" \
            --token ${{ secrets.SLACK_TOKEN }}
```

### Jenkins Pipeline

```groovy
// Jenkinsfile
pipeline {
    agent any
    
    environment {
        IMAGE = "myregistry.io/myapp"
        VERSION = "${env.BUILD_NUMBER}"
    }
    
    stages {
        stage('Build') {
            steps {
                sh "docker build -t ${IMAGE}:${VERSION} ."
                sh "docker push ${IMAGE}:${VERSION}"
            }
        }
        
        stage('Deploy to Staging') {
            steps {
                sh """
                    sq deploy k8s --update \
                        --name myapp \
                        --image ${IMAGE}:${VERSION} \
                        --namespace staging
                """
            }
        }
        
        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                input 'Deploy to production?'
                sh """
                    sq deploy k8s --update \
                        --name myapp \
                        --image ${IMAGE}:${VERSION} \
                        --namespace production
                """
            }
        }
    }
    
    post {
        success {
            sh """
                sq slack deployments \
                    --message '✓ Deployed ${VERSION} to production' \
                    --token ${SLACK_TOKEN}
            """
        }
        failure {
            sh """
                sq slack alerts \
                    --message '❌ Deployment failed for ${VERSION}' \
                    --token ${SLACK_TOKEN}
            """
        }
    }
}
```

## 🔧 Advanced Configuration

### Kubernetes with Kustomize

```bash
# kustomization.yaml structure
base/
  ├── deployment.yaml
  ├── service.yaml
  └── kustomization.yaml

overlays/
  ├── dev/
  │   └── kustomization.yaml
  ├── staging/
  │   └── kustomization.yaml
  └── prod/
      └── kustomization.yaml

# Deploy with kustomize
kubectl apply -k overlays/prod
```

### Helm Charts

```bash
# Install Helm chart
helm install myapp ./charts/myapp \
  --namespace production \
  --values values-prod.yaml

# Upgrade
helm upgrade myapp ./charts/myapp \
  --namespace production \
  --values values-prod.yaml

# Rollback
helm rollback myapp --namespace production
```

## 📊 Monitoring Deployments

### Health Checks

```bash
#!/bin/bash
# Monitor deployment health

APP_NAME="myapp"
NAMESPACE="production"

# Check deployment status
status=$(sq deploy k8s --status --name $APP_NAME --namespace $NAMESPACE)

# Parse status
available=$(echo "$status" | jq -r '.data.status.availableReplicas')
desired=$(echo "$status" | jq -r '.data.spec.replicas')

if [[ "$available" == "$desired" ]]; then
  echo "✓ Deployment healthy: $available/$desired replicas"
else
  echo "⚠️  Deployment unhealthy: $available/$desired replicas"
  sq slack alerts \
    --message "⚠️  $APP_NAME: Only $available/$desired replicas available"
fi
```

### Log Monitoring

```bash
# Stream logs
sq deploy k8s --logs --name myapp --namespace production

# Or with kubectl
kubectl logs -f deployment/myapp -n production

# Search for errors
kubectl logs deployment/myapp -n production | grep ERROR
```

## 🐛 Troubleshooting

### Debug Failed Deployment

```bash
# Get deployment status
sq deploy k8s --status --name myapp --namespace production

# Check events
kubectl get events -n production | grep myapp

# Describe deployment
kubectl describe deployment myapp -n production

# Check pod status
kubectl get pods -n production -l app=myapp

# Get pod logs
kubectl logs -l app=myapp -n production --tail=100
```

### Rollback Options

```bash
# Quick rollback
sq deploy k8s --rollback --name myapp --namespace production

# Rollback to specific revision
kubectl rollout undo deployment/myapp -n production --to-revision=2

# Check rollout history
kubectl rollout history deployment/myapp -n production
```

---

**🚀 Happy deploying with Streamware!**
