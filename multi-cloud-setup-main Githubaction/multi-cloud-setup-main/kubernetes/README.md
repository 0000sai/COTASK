# Kubernetes Configurations

This directory contains Kubernetes manifests for deploying and managing the application.

## Directory Structure

```
kubernetes/
├── deployment.yaml    # Main application deployment
├── rbac.yaml         # RBAC configurations
└── README.md         # This file
```

## Configuration Details

### deployment.yaml
- Defines the main application deployment
- Configures Linkerd service mesh integration
- Sets up monitoring with Prometheus
- Configures horizontal pod autoscaling
- Implements security contexts and network policies

### rbac.yaml
- Defines ServiceAccount for the application
- Sets up Role with least-privilege access
- Configures RoleBinding

## Deployment Instructions

1. Apply RBAC configuration:
```bash
kubectl apply -f rbac.yaml
```

2. Deploy the application:
```bash
kubectl apply -f deployment.yaml
```

## Monitoring

The deployment includes:
- Prometheus metrics endpoint on port 8443
- Linkerd service mesh integration
- Resource usage monitoring
- Health check endpoints

## Auto-scaling

HorizontalPodAutoscaler is configured to:
- Scale based on CPU and memory usage
- Maintain between 3-10 pods
- Scale up at 70% CPU utilization
- Scale up at 80% memory utilization

## Security Features

1. **Pod Security**:
   - Non-root user execution
   - Read-only root filesystem
   - Dropped capabilities
   - Resource limits

2. **Network Security**:
   - Network policies for ingress/egress
   - TLS encryption
   - Service mesh integration

3. **Access Control**:
   - RBAC with least privilege
   - ServiceAccount for pod identity
   - Resource quotas

## Troubleshooting

1. Check pod status:
```bash
kubectl get pods
kubectl describe pod <pod-name>
```

2. View logs:
```bash
kubectl logs <pod-name>
kubectl logs -f <pod-name>  # Follow logs
```

3. Check autoscaling:
```bash
kubectl get hpa
kubectl describe hpa demo-app-hpa
```

## Best Practices

1. Always use resource limits
2. Implement readiness/liveness probes
3. Use network policies
4. Enable monitoring and logging
5. Implement pod disruption budgets
6. Use node affinity for high availability
