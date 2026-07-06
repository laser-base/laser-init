# Geodata Services — AKS Deployment Guide

All five geodata microservices deploy into the existing `laser-ai` namespace.
Each gets its own LoadBalancer IP (matching the jenner-mcp pattern).
Each service mounts a PVC at `/cache` for persistent raster/shapefile storage
that survives pod restarts and redeployments.

## Services

| Name | Image | Port | Cache PVC | Notes |
|---|---|---|---|---|
| `laser-unwpp-svc` | `laser-unwpp-service` | 80 | 2 Gi | WPP CSVs; downloads on startup |
| `laser-gadm-svc` | `laser-gadm-service` | 80 | 20 Gi | GADM GDB per country; on-demand |
| `laser-geoboundaries-svc` | `laser-geoboundaries-service` | 80 | 10 Gi | geoBoundaries ZIPs; on-demand |
| `laser-unocha-svc` | `laser-unocha-service` | 80 | 5 Gi | UNOCHA global GDB (~2 GB); on first request |
| `laser-worldpop-svc` | `laser-worldpop-service` | 80 | 100 Gi | WorldPop rasters; on-demand or pre-warmed |

Registry: `idm-docker-staging.packages.idmod.org/`

---

## Quick Start

### 1. Push images

```bash
cd services/
make push-all-geodata TAG=v0.5.1a
```

### 2. Deploy PVCs, Deployments, and Services

```bash
make k8s-deploy
# or directly:
kubectl apply -f AKS/geodata-services.yaml --kubeconfig AKS/kube.conf
```

### 3. Wait for all pods to be Ready

```bash
make k8s-status
# or:
kubectl get deployment,svc,pvc -n laser-ai -l app.kubernetes.io/part-of=laser-geodata \
  --kubeconfig AKS/kube.conf
```

### 4. Pre-warm the WorldPop raster cache (optional but recommended)

Wait for `laser-worldpop-svc` to be Ready, then:

```bash
make k8s-prewarm
# or directly:
kubectl apply -f AKS/worldpop-prewarm-job.yaml --kubeconfig AKS/kube.conf

# Monitor progress (~50 countries, 4 parallel workers):
kubectl logs -f job/laser-worldpop-prewarm -n laser-ai --kubeconfig AKS/kube.conf
```

The Job downloads ~50 commonly-used country rasters (~2–500 MB each) in parallel.
Total time ~15–30 min depending on network. Completes once, then stays in a
terminal state (safe to leave or delete).

---

## Get service IPs

After deployment, retrieve LoadBalancer IPs:

```bash
kubectl get svc -n laser-ai -l app.kubernetes.io/part-of=laser-geodata \
  --kubeconfig AKS/kube.conf \
  -o custom-columns='NAME:.metadata.name,IP:.status.loadBalancer.ingress[0].ip'
```

Use those IPs in `generate.py`:

```bash
python services/generate.py NGA 1 2015 2020 \
  --shape-source unocha \
  --shapes-url   http://<unocha-ip> \
  --worldpop-url http://<worldpop-ip> \
  --unwpp-url    http://<unwpp-ip> \
  --emit-scripts
```

---

## Update a service

```bash
make push-worldpop TAG=v0.5.2a
kubectl set image deployment/laser-worldpop-svc \
  laser-worldpop-svc=idm-docker-staging.packages.idmod.org/laser-worldpop-service:v0.5.2a \
  -n laser-ai --kubeconfig AKS/kube.conf
kubectl rollout status deployment/laser-worldpop-svc -n laser-ai --kubeconfig AKS/kube.conf
```

## Rollback

```bash
kubectl rollout undo deployment/laser-worldpop-svc -n laser-ai --kubeconfig AKS/kube.conf
```

## Tail logs

```bash
kubectl logs -f deployment/laser-worldpop-svc -n laser-ai --kubeconfig AKS/kube.conf
```

## Tear down (preserves PVCs and cached data)

```bash
kubectl delete deployments,services \
  laser-unwpp-svc laser-gadm-svc laser-geoboundaries-svc laser-unocha-svc laser-worldpop-svc \
  -n laser-ai --kubeconfig AKS/kube.conf
```

To also delete the cached data (irreversible):

```bash
kubectl delete pvc \
  laser-unwpp-cache laser-gadm-cache laser-geoboundaries-cache \
  laser-unocha-cache laser-worldpop-cache \
  -n laser-ai --kubeconfig AKS/kube.conf
```

---

## Image Tagging Convention

Matches the jenner-mcp pattern: `v0.<month>.<day><letter>`

Examples: `v0.5.1a`, `v0.5.7b`
