# MCP Map Server - K8s Deployment Guide

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured
- Docker for building image
- Ingress controller (nginx recommended)

## Quick Start

### 1. Build Docker Image

```bash
# Build the image
docker build -t mcp-map-server:latest .

# Tag for your registry (if pushing to remote)
docker tag mcp-map-server:latest your-registry/mcp-map-server:latest
docker push your-registry/mcp-map-server:latest
```

### 2. Update K8s Configuration

Edit `k8s/deployment.yaml`:

```yaml
# Line 95 - Update image reference
image: your-registry/mcp-map-server:latest

# Line 157 - Update domain
host: mcp-map.your-domain.com
```

### 3. Deploy to K8s

```bash
# Apply all resources
kubectl apply -f k8s/deployment.yaml

# Check status
kubectl get all -n mcp-map-server

# View logs
kubectl logs -n mcp-map-server -l app=mcp-map-server -f
```

### 4. Access the Service

```bash
# Get ingress IP
kubectl get ingress -n mcp-map-server

# Or use port-forward for testing
kubectl port-forward -n mcp-map-server svc/mcp-map-server 8081:80

# Then visit: http://localhost:8081
```

## Architecture

```
                    ┌─────────────────┐
                    │   Ingress       │
                    │  (nginx)        │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Service       │
                    │  ClusterIP:80   │
                    └────────┬────────┘
                             │
         ┌───────────────────┴───────────────────┐
         │                                       │
    ┌────▼────┐                            ┌────▼────┐
    │  Pod 1  │                            │  Pod 2  │
    │  :8081  │                            │  :8081  │
    └────┬────┘                            └────┬────┘
         │                                       │
         └───────────────────┬───────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Redis         │
                    │  ClusterIP:6379 │
                    └─────────────────┘
```

## Production Considerations

### 1. Persistent Redis Storage

Replace `emptyDir` with `PersistentVolumeClaim` in deployment.yaml:

```yaml
# Create PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: mcp-map-server
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
  storageClassName: standard  # Adjust for your cluster

# Update deployment
volumes:
- name: redis-data
  persistentVolumeClaim:
    claimName: redis-pvc
```

### 2. Redis High Availability

For production, use Redis Sentinel or Redis Cluster:

```bash
# Using Bitnami Helm chart
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install redis bitnami/redis \
  --namespace mcp-map-server \
  --set auth.enabled=false \
  --set sentinel.enabled=true \
  --set replica.replicaCount=3
```

### 3. TLS/HTTPS

Generate TLS certificate:

```bash
# Using cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create issuer and certificate
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: mcp-map-tls
  namespace: mcp-map-server
spec:
  secretName: mcp-map-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - mcp-map.your-domain.com
EOF
```

Then uncomment TLS section in deployment.yaml.

### 4. Horizontal Pod Autoscaling

```bash
kubectl apply -f - <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-map-server
  namespace: mcp-map-server
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-map-server
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
EOF
```

### 5. Monitoring

Add Prometheus annotations to deployment:

```yaml
spec:
  template:
    metadata:
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8081"
        prometheus.io/path: "/metrics"
```

### 6. Resource Limits

Adjust based on load testing:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n mcp-map-server
kubectl describe pod -n mcp-map-server <pod-name>
kubectl logs -n mcp-map-server <pod-name>
```

### Check Redis Connection

```bash
# Get Redis pod
kubectl get pods -n mcp-map-server -l app=redis

# Test connection
kubectl exec -it -n mcp-map-server <redis-pod> -- redis-cli ping
# Should return: PONG

# Check keys
kubectl exec -it -n mcp-map-server <redis-pod> -- redis-cli keys "map_state:*"
```

### Test SSE Endpoint

```bash
# Port-forward to pod
kubectl port-forward -n mcp-map-server <pod-name> 8081:8081

# Test SSE
curl -N http://localhost:8081/events
# Should stream JSON data

# Test health
curl http://localhost:8081/health
```

### Common Issues

**Issue: Pods crashlooping**
```bash
# Check logs
kubectl logs -n mcp-map-server -l app=mcp-map-server --previous

# Common causes:
# - Redis not ready (check REDIS_HOST env)
# - Port already in use
# - Missing dependencies
```

**Issue: SSE not working**
```bash
# Check ingress annotations for proxy-buffering: off
kubectl describe ingress -n mcp-map-server

# Test without ingress
kubectl port-forward -n mcp-map-server svc/mcp-map-server 8081:80
```

**Issue: Session not persisting**
```bash
# Check Redis storage
kubectl exec -it -n mcp-map-server <redis-pod> -- redis-cli
> KEYS map_state:*
> GET map_state:<session-id>
```

## Cleanup

```bash
# Delete all resources
kubectl delete namespace mcp-map-server

# Or individual resources
kubectl delete -f k8s/deployment.yaml
```

## Next Steps

1. Set up monitoring (Prometheus + Grafana)
2. Configure backup for Redis
3. Set up CI/CD pipeline
4. Add authentication/authorization
5. Configure rate limiting
