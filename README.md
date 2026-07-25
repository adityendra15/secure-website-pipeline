# Automated Secure Website Deployment Pipeline

A CI/CD pipeline that takes a code push and turns it into a running,
health-checked Kubernetes deployment — with container vulnerability scanning
and SBOM generation gated in front of the registry push.

**Stack:** Docker · Kubernetes · GitHub Actions · Trivy

---

## What happens on every push to `main`

| # | Stage | Detail |
|---|-------|--------|
| 1 | Build | Multi-stage-free slim Python image, running as a non-root user |
| 2 | Scan | Trivy scans the image for HIGH and CRITICAL CVEs in OS and Python packages |
| 3 | Inventory | Trivy emits a CycloneDX SBOM listing every component in the image |
| 4 | Publish | Both reports are uploaded as build artifacts, then the image is pushed to GitHub Container Registry |
| 5 | Deploy | A disposable Kubernetes cluster is created in the runner and the manifests are applied |
| 6 | Verify | The rollout is watched to completion and the live service is smoke-tested |

Scanning and SBOM generation happen **before** the registry push, so an image
is never published without a vulnerability record attached to the build.

## Repository layout

```
.
├── app/
│   ├── app.py               Flask app: home page, /healthz, /readyz
│   └── requirements.txt     Pinned dependencies
├── Dockerfile               Slim base image, non-root user, gunicorn
├── k8s/
│   ├── deployment.yaml      Probes, rolling update, security context, limits
│   └── service.yaml         ClusterIP fronting the pods
├── .github/workflows/
│   └── pipeline.yml         The pipeline
└── scripts/
    └── local-deploy.sh      Run the same flow against a local cluster
```

## Health endpoints

| Path | Probe | Behaviour on failure |
|------|-------|----------------------|
| `/healthz` | Liveness | Kubernetes restarts the container |
| `/readyz` | Readiness | Kubernetes removes the pod from the Service, container keeps running |
| `/demo/toggle-ready` | — | Demo-only: flips one pod's readiness so probe behaviour can be observed |

## Running it locally

Prerequisites: Docker Desktop, `kind`, `kubectl`.

```bash
kind create cluster --name devsecops
chmod +x scripts/local-deploy.sh
./scripts/local-deploy.sh
kubectl port-forward svc/secure-website 8080:80
```

Then open <http://localhost:8080>.

## Running it in CI

Push to `main`. No secrets or configuration are required — the workflow
authenticates to the registry with the automatically provided `GITHUB_TOKEN`.

## Security decisions

- **Non-root container.** The image creates and switches to UID 10001; the
  Deployment enforces `runAsNonRoot` so the pod is rejected if that ever regresses.
- **Read-only root filesystem**, with a writable `emptyDir` mounted only at `/tmp`.
- **All Linux capabilities dropped**, `allowPrivilegeEscalation: false`,
  and the `RuntimeDefault` seccomp profile applied.
- **Least-privilege CI.** The workflow declares `permissions: {}` at the top
  level, so the job token starts with nothing and is granted only
  `contents: read` and `packages: write`.
- **Resource limits** on every container, so one workload cannot starve the node.
- **Scan before publish**, so no unscanned artifact reaches the registry.

## Known scope

Vulnerability findings are recorded but do not block the build in this project.
Blocking policy gates — Trivy, Snyk, OPA/Rego and Kubescape as hard
promotion gates — are implemented in the companion Zero-Trust pipeline project.
