# Deploying Pragna to Hostinger KVM 2 — Docker + K3s

## Architecture

```
Your Mac
  └── git push → GitHub repo
                    └── Actions (manual trigger, version input)
                          ├── Build ghcr.io/you/pragna-ui:1.0.0
                          └── Build ghcr.io/you/pragna-api:1.0.0
                                        ↓
                              GitHub Container Registry (GHCR)

Browser → Traefik (443, TLS)  ← runs inside K3s on KVM 2
              ├── /api/*   →  pragna-api pod  (FastAPI, has all secrets)
              ├── /auth/*  →  pragna-api pod
              └── /*       →  pragna-ui pod   (Caddy static files, zero secrets)
```

**Why two containers:**
- `pragna-ui` holds only the built HTML/CSS/JS — no secrets, no DB access
- `pragna-api` holds all secrets (DB, Auth0, JWT) and is never directly reachable from the internet
- Compromising the frontend container gives an attacker nothing useful

**Stack:**
- **K3s** — lightweight Kubernetes, single-node, ~512MB overhead
- **Traefik** — built into K3s, handles routing and automatic TLS
- **cert-manager** — manages Let's Encrypt certificates the Kubernetes-native way
- **GHCR** — GitHub Container Registry, free, no pull rate limits

---

## What you need before starting

| Thing | Where to get it |
|---|---|
| VPS IP address | Hostinger dashboard → VPS → Manage |
| VPS root password | Hostinger dashboard → VPS → Manage |
| Domain name | You should already have this |
| GitHub repo URL | GitHub → your repo → green Code button → HTTPS URL |
| GitHub username | Your GitHub profile |

---

## Files this guide creates in your repo

```
pragna/
├── docker/
│   ├── Dockerfile.ui          ← builds the Vue frontend image
│   ├── Dockerfile.api         ← builds the FastAPI backend image
│   ├── Caddyfile.ui           ← Caddy config for static file serving
│   └── .dockerignore          ← excludes node_modules, .env etc from build
├── k8s/
│   └── pragna/
│       ├── namespace.yaml
│       ├── secret.template.yaml   ← template only, real secret never committed
│       ├── deployment-ui.yaml
│       ├── deployment-api.yaml
│       ├── service-ui.yaml
│       ├── service-api.yaml
│       ├── ingress.yaml
│       └── cluster-issuer.yaml    ← Let's Encrypt issuer (one per cluster)
└── .github/
    └── workflows/
        └── build-and-push.yml
```

---

## Part 1 — Project files (do this on your Mac first)

### 1.1 — Docker ignore

Create `docker/.dockerignore`. This file tells Docker what to exclude from the
build so images stay small and your `.env` is never baked in:

```
node_modules
frontend/node_modules
backend/.venv
backend/__pycache__
**/__pycache__
**/*.pyc
.git
.env
*.env
docs
```

> Place this at `docker/.dockerignore`. For the build to pick it up you will
> pass it explicitly in the GitHub Actions step (shown later).

### 1.2 — Caddy config for the UI container

Create `docker/Caddyfile.ui`:

```
:80 {
    root * /usr/share/caddy
    try_files {path} /index.html
    file_server
}
```

This is all Caddy needs to serve a Vue SPA — it falls back to `index.html` for
client-side routes.

### 1.3 — Dockerfile for the frontend

Create `docker/Dockerfile.ui`:

```dockerfile
# Stage 1 — build the Vue app
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2 — serve with Caddy (no Node, no Python, no secrets)
FROM caddy:alpine
COPY --from=build /app/dist /usr/share/caddy
COPY docker/Caddyfile.ui /etc/caddy/Caddyfile
EXPOSE 80
```

### 1.4 — Dockerfile for the backend

Create `docker/Dockerfile.api`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install dependencies first (cached layer — rebuilds only when requirements change)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

EXPOSE 8000
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 1.5 — GitHub Actions workflow

Create `.github/workflows/build-and-push.yml`:

```yaml
name: Build and Push

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version tag  (e.g.  1.0.0)'
        required: true
        type: string

env:
  REGISTRY: ghcr.io
  OWNER: ${{ github.repository_owner }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push pragna-ui
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/Dockerfile.ui
          push: true
          tags: |
            ghcr.io/${{ env.OWNER }}/pragna-ui:${{ inputs.version }}
            ghcr.io/${{ env.OWNER }}/pragna-ui:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push pragna-api
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/Dockerfile.api
          push: true
          tags: |
            ghcr.io/${{ env.OWNER }}/pragna-api:${{ inputs.version }}
            ghcr.io/${{ env.OWNER }}/pragna-api:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Summary
        run: |
          echo "### Images published" >> $GITHUB_STEP_SUMMARY
          echo "- \`ghcr.io/${{ env.OWNER }}/pragna-ui:${{ inputs.version }}\`" >> $GITHUB_STEP_SUMMARY
          echo "- \`ghcr.io/${{ env.OWNER }}/pragna-api:${{ inputs.version }}\`" >> $GITHUB_STEP_SUMMARY
```

> **`GITHUB_TOKEN` is automatic** — GitHub injects it into every Actions run.
> You do not need to create any secrets for this workflow.

### 1.6 — Kubernetes manifests

Create each file below inside `k8s/pragna/`.

**`namespace.yaml`**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: pragna
```

---

**`secret.template.yaml`** — commit this template, but never commit the real secret

```yaml
# TEMPLATE ONLY — do not commit with real values
# Create the real secret on the cluster with:
#   kubectl apply -f k8s/pragna/secret.yaml -n pragna
#
apiVersion: v1
kind: Secret
metadata:
  name: pragna-secrets
  namespace: pragna
type: Opaque
stringData:
  SETTINGS_SECRET: "REPLACE"
  DATABASE_URL: "REPLACE"
  JWT_SECRET: "REPLACE"
  FRONTEND_URL: "https://yourdomain.com"
  ALLOWED_ORIGINS: "https://yourdomain.com"
  AUTH0_DOMAIN: "REPLACE"
  AUTH0_CLIENT_ID: "REPLACE"
  AUTH0_CLIENT_SECRET: "REPLACE"
  AUTH0_CALLBACK_URL: "https://yourdomain.com/auth/callback"
```

---

**`deployment-ui.yaml`** — replace `YOUR_GITHUB_USERNAME`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pragna-ui
  namespace: pragna
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pragna-ui
  template:
    metadata:
      labels:
        app: pragna-ui
    spec:
      imagePullSecrets:
        - name: ghcr-pull-secret
      containers:
        - name: pragna-ui
          image: ghcr.io/YOUR_GITHUB_USERNAME/pragna-ui:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 80
          resources:
            requests:
              memory: "64Mi"
              cpu: "50m"
            limits:
              memory: "128Mi"
              cpu: "200m"
```

---

**`deployment-api.yaml`** — replace `YOUR_GITHUB_USERNAME`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pragna-api
  namespace: pragna
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pragna-api
  template:
    metadata:
      labels:
        app: pragna-api
    spec:
      imagePullSecrets:
        - name: ghcr-pull-secret
      containers:
        - name: pragna-api
          image: ghcr.io/YOUR_GITHUB_USERNAME/pragna-api:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: pragna-secrets
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          readinessProbe:
            httpGet:
              path: /auth/me
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
```

---

**`service-ui.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: pragna-ui
  namespace: pragna
spec:
  selector:
    app: pragna-ui
  ports:
    - port: 80
      targetPort: 80
```

---

**`service-api.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: pragna-api
  namespace: pragna
spec:
  selector:
    app: pragna-api
  ports:
    - port: 8000
      targetPort: 8000
```

---

**`ingress.yaml`** — replace `yourdomain.com`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: pragna
  namespace: pragna
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - yourdomain.com
      secretName: pragna-tls
  rules:
    - host: yourdomain.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: pragna-api
                port:
                  number: 8000
          - path: /auth
            pathType: Prefix
            backend:
              service:
                name: pragna-api
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: pragna-ui
                port:
                  number: 80
```

---

**`cluster-issuer.yaml`** — replace `your@email.com` — applied once per cluster, not per app

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your@email.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            ingressClassName: traefik
```

---

### 1.7 — Commit and push everything

```bash
git add docker/ k8s/ .github/
git commit -m "feat: Docker images, K8s manifests, GitHub Actions workflow"
git push
```

---

## Part 2 — One-time server setup

### 2.1 — SSH into the VPS

```bash
ssh root@YOUR_VPS_IP
```

### 2.2 — Update the server

```bash
apt update && apt upgrade -y
apt install -y curl git ufw
```

### 2.3 — Firewall

```bash
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable
ufw status
```

### 2.4 — Install K3s

```bash
curl -sfL https://get.k3s.io | sh -
```

Wait about 30 seconds, then verify:

```bash
kubectl get nodes
# Should show your node with STATUS = Ready
```

### 2.5 — Install cert-manager

cert-manager handles automatic TLS certificate renewal for all your apps:

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

# Wait for cert-manager pods to be ready (takes ~60 seconds)
kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=cert-manager \
  -n cert-manager --timeout=120s
```

### 2.6 — Allow your Mac to control the cluster (optional but recommended)

This lets you run `kubectl` from your Mac without SSHing in every time.

On the **server**, copy the kubeconfig:

```bash
cat /etc/rancher/k3s/k3s.yaml
```

Copy that entire output. On your **Mac**, open a new terminal:

```bash
mkdir -p ~/.kube
nano ~/.kube/config-hostinger
# Paste the content, save

# Replace 127.0.0.1 with your actual VPS IP — e.g. if your IP is 1.2.3.4:
#   sed -i '' 's/127.0.0.1/1.2.3.4/g' ~/.kube/config-hostinger
sed -i '' "s/127.0.0.1/$(echo YOUR_ACTUAL_VPS_IP)/g" ~/.kube/config-hostinger

# Verify the file now contains your real IP
grep server ~/.kube/config-hostinger
# Expected output: server: https://1.2.3.4:6443

# Add to your shell profile
echo 'export KUBECONFIG=~/.kube/config:~/.kube/config-hostinger' >> ~/.zshrc
source ~/.zshrc

# Test
kubectl get nodes --context=default
```

---

## Part 3 — One-time GitHub setup

### 3.1 — Create a Personal Access Token for image pulls

The cluster needs credentials to pull private images from GHCR.

1. Go to GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **Generate new token (classic)**
3. Name: `hostinger-k3s-pull`
4. Expiration: 1 year (or No expiration)
5. Tick only: `read:packages`
6. Click **Generate token** — copy it immediately, it is shown only once

### 3.2 — Create the image pull secret on the cluster

Run this on the server (or from your Mac if you set up kubeconfig above).
Replace `YOUR_GITHUB_USERNAME` and `YOUR_PAT`:

```bash
# You need to apply the namespace first
kubectl apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: pragna
EOF

kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_PAT \
  --namespace=pragna
```

> When you add more apps later, create the same secret in their namespace too.

---

## Part 4 — First build

Go to your GitHub repo in the browser:

1. Click the **Actions** tab
2. Click **Build and Push** in the left sidebar
3. Click **Run workflow**
4. Type version: `1.0.0`
5. Click the green **Run workflow** button

Watch it run. Both images will be pushed to GHCR. Takes 3–5 minutes the first time, faster after that due to layer caching.

---

## Part 5 — First deployment on the cluster

Run these from the server (or your Mac if you set up kubeconfig):

### 5.1 — Apply the namespace

```bash
kubectl apply -f k8s/pragna/namespace.yaml
```

### 5.2 — Create the secret with real values

Copy `secret.template.yaml` to `secret.yaml` locally, fill in your real values,
then apply it. **Never commit `secret.yaml` to git.**

```bash
# On the server — create the file
nano /tmp/pragna-secret.yaml
```

Paste your filled-in secret YAML, save. Then:

```bash
kubectl apply -f /tmp/pragna-secret.yaml
rm /tmp/pragna-secret.yaml   # delete after applying
```

Verify it was created:

```bash
kubectl get secret pragna-secrets -n pragna
```

### 5.3 — Apply the cert-manager ClusterIssuer

This is one per cluster — not per app:

```bash
kubectl apply -f k8s/pragna/cluster-issuer.yaml

# Verify it becomes Ready
kubectl describe clusterissuer letsencrypt-prod
```

### 5.4 — Point DNS at the VPS

Before applying the ingress, your domain must point at the VPS IP. Go to your
DNS provider and set an A record for `yourdomain.com` → your VPS IP.

Check propagation from your Mac:

```bash
nslookup yourdomain.com
```

Wait until it returns your VPS IP (5–60 minutes).

### 5.5 — Apply all remaining manifests

```bash
kubectl apply -f k8s/pragna/deployment-ui.yaml
kubectl apply -f k8s/pragna/deployment-api.yaml
kubectl apply -f k8s/pragna/service-ui.yaml
kubectl apply -f k8s/pragna/service-api.yaml
kubectl apply -f k8s/pragna/ingress.yaml
```

### 5.6 — Verify everything is running

```bash
# Pods should show Running
kubectl get pods -n pragna

# Ingress should show your domain
kubectl get ingress -n pragna

# Certificate should become Ready within 2 minutes
kubectl get certificate -n pragna
```

---

## Part 6 — Update Auth0 allowed URLs

Go to [manage.auth0.com](https://manage.auth0.com) → Applications → your app → Settings:

| Field | Value |
|---|---|
| Allowed Callback URLs | `https://yourdomain.com/auth/callback` |
| Allowed Logout URLs | `https://yourdomain.com` |
| Allowed Web Origins | `https://yourdomain.com` |

Click **Save Changes**.

Open `https://yourdomain.com` — you should see the Pragna login page with a padlock.

---

## Part 7 — Normal deploy workflow (every future release)

1. Make your changes on Mac, commit and push to GitHub
2. Go to GitHub → Actions → **Build and Push** → **Run workflow**
3. Enter the new version (e.g. `1.1.0`) → **Run workflow**
4. Wait for Actions to finish (images pushed to GHCR)
5. On the server (or from Mac):

```bash
# Update both deployments to the new version
kubectl set image deployment/pragna-ui \
  pragna-ui=ghcr.io/YOUR_GITHUB_USERNAME/pragna-ui:1.1.0 \
  -n pragna

kubectl set image deployment/pragna-api \
  pragna-api=ghcr.io/YOUR_GITHUB_USERNAME/pragna-api:1.1.0 \
  -n pragna

# Watch the rollout
kubectl rollout status deployment/pragna-ui -n pragna
kubectl rollout status deployment/pragna-api -n pragna
```

K3s pulls the new image and replaces pods one by one — zero downtime.

To roll back if something goes wrong:

```bash
kubectl rollout undo deployment/pragna-api -n pragna
kubectl rollout undo deployment/pragna-ui -n pragna
```

---

## Part 8 — Adding a second site

For each new app, the pattern is the same:

1. Add `docker/Dockerfile.yourapp` to the repo
2. Add a new job in the GitHub Actions workflow to build `yourapp` image
3. Create `k8s/yourapp/` with the same set of manifests (different namespace, domain, image name)
4. Create the `ghcr-pull-secret` in the new namespace
5. Create the app's secret with `kubectl apply`
6. Apply the manifests
7. The same `ClusterIssuer` (letsencrypt-prod) is reused — do not create it again

The `cluster-issuer.yaml` is a **cluster-wide resource** — one instance serves all namespaces.

---

## Troubleshooting

| Problem | Command |
|---|---|
| Pod not starting | `kubectl describe pod -n pragna` |
| Backend logs | `kubectl logs deployment/pragna-api -n pragna` |
| Frontend logs | `kubectl logs deployment/pragna-ui -n pragna` |
| Certificate stuck | `kubectl describe certificate -n pragna` |
| Certificate challenge | `kubectl describe challenge -n pragna` |
| Image pull error | `kubectl describe pod -n pragna \| grep -A5 Events` |
| Ingress not routing | `kubectl describe ingress -n pragna` |
| Restart a pod | `kubectl rollout restart deployment/pragna-api -n pragna` |
| Watch all pods | `kubectl get pods -n pragna -w` |

---

## Resource usage on KVM 2 (8GB RAM)

| Component | Memory |
|---|---|
| K3s + Traefik | ~512MB |
| cert-manager | ~128MB |
| pragna-api | 256–512MB |
| pragna-ui | 64–128MB |
| OS overhead | ~400MB |
| **Total (1 app)** | **~1.4–1.7GB** |
| **Headroom for 4 more apps** | **~6GB remaining** |

You have comfortable room for 4–5 apps on this node.
