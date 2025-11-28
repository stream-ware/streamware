#!/usr/bin/env python3
"""
Deployment Examples - Kubernetes, Docker Compose, Swarm

Demonstrates deployment to various platforms using Streamware Quick.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from streamware import flow
from streamware.components.deploy import deploy_k8s, deploy_compose, scale_k8s


def example_1_kubernetes_deploy():
    """Example 1: Kubernetes Deployment"""
    print("\n=== Example 1: Kubernetes Deployment ===")
    
    # Create simple deployment manifest
    manifest = """
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
        image: nginx:latest
        ports:
        - containerPort: 80
"""
    
    # Save manifest
    with open('/tmp/deployment.yaml', 'w') as f:
        f.write(manifest)
    
    print("Deploying to Kubernetes...")
    
    # Deploy
    result = deploy_k8s('/tmp/deployment.yaml', namespace='default')
    print(f"✓ Deployed: {result}")


def example_2_docker_compose():
    """Example 2: Docker Compose Deployment"""
    print("\n=== Example 2: Docker Compose ===")
    
    compose = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
  
  redis:
    image: redis:alpine
"""
    
    # Save compose file
    with open('/tmp/docker-compose.yml', 'w') as f:
        f.write(compose)
    
    print("Deploying with Docker Compose...")
    
    # Deploy
    result = deploy_compose('/tmp/docker-compose.yml', project='myproject')
    print(f"✓ Deployed: {result}")


def example_3_quick_cli():
    """Example 3: Quick CLI Commands"""
    print("\n=== Example 3: Quick CLI ===")
    
    print("""
    # Kubernetes
    sq deploy k8s --apply --file deployment.yaml --namespace production
    sq deploy k8s --scale 5 --name myapp --namespace production
    sq deploy k8s --update --name myapp --image myapp:v2.0
    sq deploy k8s --status --namespace production
    sq deploy k8s --logs --name myapp
    sq deploy k8s --rollback --name myapp
    sq deploy k8s --delete --file deployment.yaml
    
    # Docker Compose
    sq deploy compose --apply --file docker-compose.yml --project myapp
    sq deploy compose --scale 3 --name web --project myapp
    sq deploy compose --status --project myapp
    sq deploy compose --delete --project myapp
    
    # Docker Swarm
    sq deploy swarm --apply --file docker-compose.yml --stack mystack
    sq deploy swarm --delete --stack mystack
    """)


def example_4_kubernetes_full_workflow():
    """Example 4: Complete K8s Workflow"""
    print("\n=== Example 4: Kubernetes Full Workflow ===")
    
    print("""
    #!/bin/bash
    # Full Kubernetes deployment workflow
    
    APP_NAME="myapp"
    NAMESPACE="production"
    VERSION="v2.0"
    
    # 1. Apply deployment
    sq deploy k8s --apply \\
        --file k8s/deployment.yaml \\
        --namespace $NAMESPACE
    
    # 2. Check status
    sq deploy k8s --status \\
        --namespace $NAMESPACE
    
    # 3. Update image
    sq deploy k8s --update \\
        --name $APP_NAME \\
        --image myregistry/$APP_NAME:$VERSION \\
        --namespace $NAMESPACE
    
    # 4. Scale up
    sq deploy k8s --scale 5 \\
        --name $APP_NAME \\
        --namespace $NAMESPACE
    
    # 5. Check logs
    sq deploy k8s --logs \\
        --name $APP_NAME \\
        --namespace $NAMESPACE
    
    # 6. If issues, rollback
    if [[ $? -ne 0 ]]; then
        sq deploy k8s --rollback \\
            --name $APP_NAME \\
            --namespace $NAMESPACE
    fi
    """)


def example_5_multi_environment():
    """Example 5: Multi-Environment Deployment"""
    print("\n=== Example 5: Multi-Environment ===")
    
    print("""
    #!/bin/bash
    # Deploy to multiple environments
    
    APP_NAME="myapp"
    VERSION="v2.0"
    
    # Development
    sq deploy k8s --apply \\
        --file deployment.yaml \\
        --namespace dev \\
        --context dev-cluster
    
    # Staging
    sq deploy k8s --apply \\
        --file deployment.yaml \\
        --namespace staging \\
        --context staging-cluster
    
    # Production (with approval)
    read -p "Deploy to production? (yes/no) " confirm
    if [[ "$confirm" == "yes" ]]; then
        sq deploy k8s --apply \\
            --file deployment.yaml \\
            --namespace production \\
            --context prod-cluster
    fi
    """)


def example_6_blue_green_deployment():
    """Example 6: Blue-Green Deployment"""
    print("\n=== Example 6: Blue-Green Deployment ===")
    
    print("""
    #!/bin/bash
    # Blue-Green deployment strategy
    
    APP_NAME="myapp"
    NEW_VERSION="v2.0"
    NAMESPACE="production"
    
    # 1. Deploy green (new version)
    sq deploy k8s --apply \\
        --file deployment-green.yaml \\
        --namespace $NAMESPACE
    
    # 2. Wait for green to be ready
    kubectl wait --for=condition=available \\
        deployment/myapp-green \\
        -n $NAMESPACE
    
    # 3. Test green deployment
    if curl -f http://myapp-green/health; then
        echo "✓ Green deployment healthy"
        
        # 4. Switch traffic (update service)
        kubectl patch service myapp \\
            -n $NAMESPACE \\
            -p '{"spec":{"selector":{"version":"green"}}}'
        
        # 5. Remove blue (old version)
        sq deploy k8s --delete \\
            --name myapp-blue \\
            --namespace $NAMESPACE
    else
        echo "✗ Green deployment failed"
        sq deploy k8s --delete \\
            --name myapp-green \\
            --namespace $NAMESPACE
    fi
    """)


def example_7_canary_deployment():
    """Example 7: Canary Deployment"""
    print("\n=== Example 7: Canary Deployment ===")
    
    print("""
    #!/bin/bash
    # Canary deployment - gradual rollout
    
    APP_NAME="myapp"
    NEW_VERSION="v2.0"
    NAMESPACE="production"
    
    # 1. Deploy canary (10% traffic)
    sq deploy k8s --apply \\
        --file deployment-canary.yaml \\
        --namespace $NAMESPACE
    
    sq deploy k8s --scale 1 \\
        --name myapp-canary \\
        --namespace $NAMESPACE
    
    # 2. Monitor canary (wait 10 minutes)
    sleep 600
    
    # 3. Check error rate
    error_rate=$(curl -s http://monitoring/api/errors?service=myapp-canary)
    
    if [[ "$error_rate" < "0.01" ]]; then
        echo "✓ Canary looks good, scaling up..."
        
        # 4. Gradually increase canary
        for replicas in 3 5 10; do
            sq deploy k8s --scale $replicas \\
                --name myapp-canary \\
                --namespace $NAMESPACE
            sleep 300  # Wait 5 minutes between scales
        done
        
        # 5. Remove old version
        sq deploy k8s --delete \\
            --name myapp-stable \\
            --namespace $NAMESPACE
    else
        echo "✗ Canary has issues, rolling back"
        sq deploy k8s --delete \\
            --name myapp-canary \\
            --namespace $NAMESPACE
    fi
    """)


def example_8_compose_with_scaling():
    """Example 8: Docker Compose with Scaling"""
    print("\n=== Example 8: Compose with Scaling ===")
    
    print("""
    # Deploy and scale with Docker Compose
    
    # Start services
    sq deploy compose --apply \\
        --file docker-compose.yml \\
        --project myapp
    
    # Scale web service
    sq deploy compose --scale 3 \\
        --name web \\
        --project myapp
    
    # Check status
    sq deploy compose --status --project myapp
    
    # View logs
    docker-compose -p myapp logs -f web
    
    # Scale down
    sq deploy compose --scale 1 \\
        --name web \\
        --project myapp
    
    # Stop everything
    sq deploy compose --delete --project myapp
    """)


def example_9_swarm_stack():
    """Example 9: Docker Swarm Stack"""
    print("\n=== Example 9: Docker Swarm Stack ===")
    
    print("""
    # Docker Swarm deployment
    
    # Initialize swarm (if not already)
    docker swarm init
    
    # Deploy stack
    sq deploy swarm --apply \\
        --file docker-compose-swarm.yml \\
        --stack mystack
    
    # Check services
    docker stack services mystack
    
    # Update stack
    sq deploy swarm --apply \\
        --file docker-compose-swarm-v2.yml \\
        --stack mystack
    
    # Remove stack
    sq deploy swarm --delete --stack mystack
    """)


def example_10_ci_cd_integration():
    """Example 10: CI/CD Integration"""
    print("\n=== Example 10: CI/CD Integration ===")
    
    print("""
    #!/bin/bash
    # CI/CD Pipeline Script
    
    set -e
    
    # Configuration
    APP_NAME="myapp"
    VERSION=$(git describe --tags)
    REGISTRY="myregistry.io"
    
    echo "🚀 Deploying $APP_NAME version $VERSION"
    
    # 1. Build Docker image
    docker build -t $REGISTRY/$APP_NAME:$VERSION .
    docker push $REGISTRY/$APP_NAME:$VERSION
    
    # 2. Deploy to staging
    sq deploy k8s --update \\
        --name $APP_NAME \\
        --image $REGISTRY/$APP_NAME:$VERSION \\
        --namespace staging
    
    # 3. Run tests
    kubectl wait --for=condition=available \\
        deployment/$APP_NAME -n staging
    
    if ./run-integration-tests.sh staging; then
        echo "✓ Tests passed"
        
        # 4. Deploy to production
        sq deploy k8s --update \\
            --name $APP_NAME \\
            --image $REGISTRY/$APP_NAME:$VERSION \\
            --namespace production
        
        # 5. Notify team
        sq slack deployments \\
            --message "✓ Deployed $APP_NAME:$VERSION to production" \\
            --token $SLACK_TOKEN
    else
        echo "✗ Tests failed"
        
        # Rollback staging
        sq deploy k8s --rollback \\
            --name $APP_NAME \\
            --namespace staging
        
        # Notify failure
        sq slack alerts \\
            --message "❌ Deployment failed for $APP_NAME:$VERSION" \\
            --token $SLACK_TOKEN
        
        exit 1
    fi
    """)


def main():
    """Run all examples"""
    print("=" * 70)
    print("DEPLOYMENT EXAMPLES - K8s, Compose, Swarm")
    print("=" * 70)
    
    examples = [
        example_1_kubernetes_deploy,
        example_2_docker_compose,
        example_3_quick_cli,
        example_4_kubernetes_full_workflow,
        example_5_multi_environment,
        example_6_blue_green_deployment,
        example_7_canary_deployment,
        example_8_compose_with_scaling,
        example_9_swarm_stack,
        example_10_ci_cd_integration,
    ]
    
    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nNote: {example.__name__} - {e}")
            print("(Some examples show shell scripts, not Python execution)")
    
    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\n🚀 Quick Reference:")
    print("  sq deploy k8s --apply --file deployment.yaml")
    print("  sq deploy k8s --scale 5 --name myapp")
    print("  sq deploy compose --apply --file docker-compose.yml")
    print("  sq deploy swarm --apply --stack mystack")


if __name__ == "__main__":
    main()
