# Deployment Guide — Pragna on Hostinger K3s

## Architecture

```
Developer Mac
  └── git push → GitHub
                    └── Actions (manual trigger)
                          ├── test-backend (pytest)
                          ├── test-frontend (vitest)
                          └── deploy to: staging | production

Staging (pragna-staging namespace)
─────────────────────────────────
Browser → Traefik (443 TLS)     pragna-staging.sgummallaworks.com
            ├── /api/*  → pragna-api pod
            ├── /auth/* → pragna-api pod
            └── /*      → pragna-ui pod
                              ↓
                        postgres pod (own DB, isolated)

Production (pragna namespace) — blue-green
──────────────────────────────────────────
Browser → Traefik (443 TLS)     pragna.sgummallaworks.com
            ├── /api/*  → Service pragna-api (slot: blue OR green)
            ├── /auth/* → Service pragna-api
            └── /*      → pragna-ui pod
                              ↓
              pragna-api-blue   pragna-api-green
              (one live, one    (other at 0 replicas
               serving traffic)  until next deploy)
```

**Blue-green explained:** Both `pragna-api-blue` and `pragna-api-green` Deployments exist permanently.
The `pragna-api` Service has a `slot` selector that points to whichever is live.
Deploying = update the inactive slot → wait for ready → flip the selector → scale down old.
Rollback = flip the selector back. Takes ~1 second.

---

## Repository structure (infra files)

```
.github/workflows/build-and-push.yml   ← CI/CD pipeline
k8s/
  pragna/                              ← production manifests
    namespace.yaml
    deployment-api-blue.yaml
    deployment-api-green.yaml
    deployment-ui.yaml
    service-api.yaml                   ← selector: slot: blue (patched on each deploy)
    service-ui.yaml
    ingress.yaml
    cluster-issuer.yaml
    secret.template.yaml
  pragna-staging/                      ← staging manifests
    namespace.yaml
    postgres.yaml                      ← Deployment + PVC + Service
    deployment-api.yaml
    deployment-ui.yaml
    service-api.yaml
    service-ui.yaml
    ingress.yaml
    secret.template.yaml
scripts/
  blue-green-deploy.sh                 ← runs on VPS during production deploy
```

---

## GitHub Actions secrets required

Add these in **GitHub repo → Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `VPS_HOST` | Your VPS IP address |
| `VPS_SSH_KEY` | Private SSH key that can log in as root |
| `VPS_REPO_PATH` | Absolute path to the repo on VPS (e.g. `/root/pragna`) |

`GITHUB_TOKEN` is injected automatically — no setup needed.

---

## Part 1 — One-time VPS setup

Do this once when you first get the server. SSH in as root.

### 1.1 — Update and install basics

```bash
ssh root@YOUR_VPS_IP

apt update && apt upgrade -y
apt install -y curl git ufw
```

### 1.2 — Configure firewall

```bash
ufw allow 22    # SSH
ufw allow 80    # HTTP (cert-manager needs this for ACME challenge)
ufw allow 443   # HTTPS
ufw allow 6443  # Kubernetes API (needed if you run kubectl from your Mac)
ufw --force enable
ufw status
```

### 1.3 — Install K3s

```bash
curl -sfL https://get.k3s.io | sh -

# Wait ~30s then verify the node is Ready
kubectl get nodes
```

Expected output:
```
NAME       STATUS   ROLES                  AGE   VERSION
vps-host   Ready    control-plane,master   30s   v1.x.x
```

### 1.4 — Install cert-manager

cert-manager handles automatic TLS certificates via Let's Encrypt for all apps on this cluster.

```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml

# Wait for all cert-manager pods to be Ready (~60 seconds)
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/instance=cert-manager \
  -n cert-manager --timeout=120s
```

### 1.5 — Clone the repo onto the VPS

```bash
git clone https://github.com/sgummalla79/sf-research-agent.git /root/pragna
cd /root/pragna
```

This path must match `VPS_REPO_PATH` in GitHub secrets.

### 1.6 — Allow your Mac to control the cluster (optional but recommended)

Lets you run `kubectl` commands from your Mac without SSHing in every time.

**On the VPS:**
```bash
cat /etc/rancher/k3s/k3s.yaml
```

Copy the full output. **On your Mac:**
```bash
mkdir -p ~/.kube
# Paste the content into this file:
nano ~/.kube/config-hostinger

# Replace 127.0.0.1 with your actual VPS IP
sed -i '' 's/127.0.0.1/YOUR_VPS_IP/g' ~/.kube/config-hostinger

# Add to your shell profile
echo 'export KUBECONFIG=~/.kube/config:~/.kube/config-hostinger' >> ~/.zshrc
source ~/.zshrc

# Test — should show your VPS node
kubectl get nodes
```

---

## Part 2 — One-time cluster setup (production)

Run from the VPS (or your Mac if you set up kubeconfig above).

### 2.1 — Apply production namespace and manifests

Files are prefixed so `00-namespace.yaml` always applies first:

```bash
cd /root/pragna
kubectl apply -f k8s/pragna/
```

### 2.2 — Create the GHCR image pull secret

Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**
and generate a token with only `read:packages` scope. Then on the VPS:

```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=sgummalla79 \
  --docker-password=YOUR_GITHUB_PAT \
  --namespace=pragna
```

### 2.3 — Create production secrets

**Never commit real secret values to git.** Fill in `k8s/pragna/secret.template.yaml`
on the VPS, apply it, then delete the file.

```bash
# Generate SETTINGS_SECRET (Fernet key):
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate JWT_SECRET:
openssl rand -hex 32

# Create the secrets file (never save this to disk long-term):
nano /tmp/pragna-secrets.yaml
# Fill in all REPLACE values from secret.template.yaml

kubectl apply -f /tmp/pragna-secrets.yaml -n pragna
rm /tmp/pragna-secrets.yaml

# Verify:
kubectl get secret pragna-secrets -n pragna
```

### 2.4 — Point DNS at the VPS

Add an **A record** in your DNS provider:

| Name | Type | Value |
|------|------|-------|
| `pragna` | A | `YOUR_VPS_IP` |

Wait for DNS to propagate (up to 30 min). Check from your Mac:
```bash
nslookup pragna.sgummallaworks.com
# Must return your VPS IP before continuing
```

### 2.5 — Run the first production deploy

Go to **GitHub → Actions → Build and Push → Run workflow**:
- Environment: `production`
- Bump: `patch`

This builds the images, pushes to GHCR, and runs `scripts/blue-green-deploy.sh`
on the VPS for the first time. Blue slot becomes live, green stays at 0 replicas.

### 2.6 — Verify production

```bash
# Pods should show Running
kubectl get pods -n pragna

# Certificate should be Ready within 2 minutes
kubectl get certificate -n pragna

# Health check
curl -s https://pragna.sgummallaworks.com/health
```

---

## Part 3 — One-time cluster setup (staging)

### 3.1 — Apply staging namespace and manifests

Files are prefixed so `00-namespace.yaml` always applies first:

```bash
cd /root/pragna
kubectl apply -f k8s/pragna-staging/

# Wait for postgres to be ready
kubectl wait --for=condition=ready pod -l app=postgres \
  -n pragna-staging --timeout=120s
```

### 3.2 — Create the GHCR pull secret for staging

```bash
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=sgummalla79 \
  --docker-password=YOUR_GITHUB_PAT \
  --namespace=pragna-staging
```

### 3.3 — Create staging secrets

Staging uses **different secret values** from production. Same structure as production
but separate SETTINGS_SECRET, JWT_SECRET, DATABASE_URL, and Auth0 credentials.

```bash
# Generate fresh keys for staging:
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
openssl rand -hex 32

nano /tmp/pragna-staging-secrets.yaml
# Fill in all REPLACE values from k8s/pragna-staging/secret.template.yaml
# Note: DATABASE_URL = postgresql://pragna:YOUR_PG_PASSWORD@postgres:5432/pragna_staging

kubectl apply -f /tmp/pragna-staging-secrets.yaml -n pragna-staging
rm /tmp/pragna-staging-secrets.yaml

# Verify:
kubectl get secret pragna-staging-secrets -n pragna-staging
```

### 3.4 — Point DNS for staging

Add another A record:

| Name | Type | Value |
|------|------|-------|
| `pragna-staging` | A | `YOUR_VPS_IP` (same IP, different subdomain) |

### 3.5 — Update Auth0 for staging (if using a separate Auth0 app)

Go to **manage.auth0.com → Applications → your staging app → Settings**:

| Field | Value |
|-------|-------|
| Allowed Callback URLs | `https://pragna-staging.sgummallaworks.com/auth/callback` |
| Allowed Logout URLs | `https://pragna-staging.sgummallaworks.com` |
| Allowed Web Origins | `https://pragna-staging.sgummallaworks.com` |

### 3.6 — Run the first staging deploy

Go to **GitHub → Actions → Build and Push → Run workflow**:
- Environment: `staging`
- Bump: ignored for staging

This builds `staging-<sha>` tagged images and deploys to `pragna-staging` namespace.

```bash
# Verify:
kubectl get pods -n pragna-staging
curl -s https://pragna-staging.sgummallaworks.com/health
```

---

## Part 4 — Day-to-day: deploying to staging

Use this to validate changes before promoting to production.

1. Commit and push your changes to `main`
2. Go to **GitHub → Actions → Build and Push → Run workflow**
3. Set **Environment** to `staging`
4. Click **Run workflow**

**What happens:**
```
test-backend  ──┐
                ├──► deploy-staging
test-frontend ──┘     ├── build pragna-api:staging-<sha>
                      ├── build pragna-ui:staging-<sha>
                      ├── push both to GHCR
                      └── SSH into VPS:
                            ├── run alembic migrations on staging DB
                            ├── kubectl set image pragna-api (staging namespace)
                            ├── kubectl set image pragna-ui (staging namespace)
                            ├── wait for rollout
                            └── health check probe
```

Check staging after deploy:
```bash
kubectl get pods -n pragna-staging
curl -s https://pragna-staging.sgummallaworks.com/health
```

---

## Part 5 — Day-to-day: deploying to production (blue-green)

Only do this after validating on staging.

1. Go to **GitHub → Actions → Build and Push → Run workflow**
2. Set **Environment** to `production`
3. Set **Bump** to `patch` / `minor` / `major`
4. Click **Run workflow**

**What happens:**
```
test-backend  ──┐
                ├──► build (production)
test-frontend ──┘     ├── bump VERSION file (e.g. 1.0.12 → 1.0.13)
                      ├── generate release notes
                      ├── commit version bump to main
                      ├── build pragna-api:1.0.13 + :latest
                      ├── build pragna-ui:1.0.13 + :latest
                      ├── push both to GHCR
                      └──► deploy-production (blue-green)
                            └── SSH into VPS, runs scripts/blue-green-deploy.sh:
                                  1. detect active slot (blue or green)
                                  2. update image on INACTIVE slot
                                  3. scale up inactive slot (replicas: 1)
                                  4. wait for readiness probe to pass
                                  5. run alembic migrations
                                  6. pre-switch health check on new pod
                                  7. patch Service selector → traffic switches (~1s)
                                  8. 2-minute health check window
                                  9. on success: scale down old slot (replicas: 0)
                                  10. on failure: patch selector back (instant rollback)
```

Watch it live on the VPS:
```bash
# See pods switching
kubectl get pods -n pragna -w

# See which slot the service is pointing at
kubectl get service pragna-api -n pragna \
  -o jsonpath='{.spec.selector.slot}'
```

---

## Part 6 — Rollback

### Production rollback (instant — ~1 second)

If something goes wrong after a production deploy, flip the Service selector back
to the previous slot. The old pod is still running (scaled to 0, not deleted):

```bash
# Scale the old slot back up first
kubectl scale deployment/pragna-api-blue -n pragna --replicas=1
# (or green, whichever was the previous active slot)

# Wait for it to be ready
kubectl rollout status deployment/pragna-api-blue -n pragna

# Flip traffic back
kubectl patch service pragna-api -n pragna \
  --type=merge \
  -p '{"spec":{"selector":{"app":"pragna-api","slot":"blue"}}}'

echo "Traffic restored to blue slot"
```

The deploy script prints the exact rollback command at the end of every deploy run —
copy it from the GitHub Actions log before you need it.

### Staging rollback

Staging uses standard rolling updates, so:
```bash
kubectl rollout undo deployment/pragna-api -n pragna-staging
kubectl rollout undo deployment/pragna-ui  -n pragna-staging
```

### Database rollback

Rolling back pods does **not** roll back the database schema. Alembic migrations
run forward-only in this setup. If a migration needs to be undone, write a new
compensating migration and deploy it forward — do not run `alembic downgrade`.

---

## Part 7 — Troubleshooting

### Check pod status

```bash
kubectl get pods -n pragna          # production
kubectl get pods -n pragna-staging  # staging
```

### See what's wrong with a pod

```bash
kubectl describe pod <pod-name> -n pragna
kubectl logs deployment/pragna-api -n pragna
kubectl logs deployment/pragna-api -n pragna-staging
```

### Health check

```bash
curl -s https://pragna.sgummallaworks.com/health
curl -s https://pragna-staging.sgummallaworks.com/health
```

### Certificate not issued

```bash
kubectl get certificate -n pragna
kubectl describe certificate pragna-tls -n pragna
kubectl describe challenge -n pragna   # if challenge exists
```

Most common cause: DNS not propagated yet. Check with `nslookup pragna.sgummallaworks.com`.

### Image pull failing

```bash
kubectl describe pod <pod-name> -n pragna | grep -A10 Events
```

Usually means the `ghcr-pull-secret` is missing or the PAT expired:
```bash
kubectl delete secret ghcr-pull-secret -n pragna
kubectl create secret docker-registry ghcr-pull-secret \
  --docker-server=ghcr.io \
  --docker-username=sgummalla79 \
  --docker-password=YOUR_NEW_PAT \
  --namespace=pragna
```

### Blue-green: check active slot

```bash
kubectl get service pragna-api -n pragna \
  -o jsonpath='{.spec.selector}' | python3 -m json.tool
```

### Force restart a pod

```bash
kubectl rollout restart deployment/pragna-api -n pragna
kubectl rollout restart deployment/pragna-api -n pragna-staging
```

### Common problems table

| Problem | Command to run |
|---------|---------------|
| Pod stuck in Pending | `kubectl describe pod <name> -n pragna` — check Events |
| Pod CrashLoopBackOff | `kubectl logs <pod-name> -n pragna --previous` |
| 502/503 from browser | `kubectl get pods -n pragna` — check all Running |
| Certificate pending | `kubectl describe challenge -n pragna` |
| Staging DB not ready | `kubectl get pods -n pragna-staging` — check postgres pod |
| Wrong models showing | Check `user_llm_models` table — inactive models shouldn't appear |
| Migration failed | Check CI logs for `alembic upgrade head` step |

---

## Part 8 — Database operations

### Connect to production DB

```bash
kubectl exec -it deployment/postgres -n pragna -- psql -U pragna pragna
```

> Production uses the external Neon DB specified in `DATABASE_URL` — adjust accordingly.

### Connect to staging DB

```bash
kubectl exec -it deployment/postgres -n pragna-staging -- \
  psql -U pragna pragna_staging
```

### Backup staging DB

```bash
kubectl exec deployment/postgres -n pragna-staging -- \
  pg_dump -U pragna pragna_staging | gzip > staging_$(date +%Y%m%d).sql.gz
```

### Restore staging DB

```bash
gunzip -c staging_20260516.sql.gz | \
  kubectl exec -i deployment/postgres -n pragna-staging -- \
  psql -U pragna pragna_staging
```

### Nightly backup cron (add on VPS)

```bash
crontab -e
# Add this line:
0 2 * * * kubectl exec deployment/postgres -n pragna-staging -- pg_dump -U pragna pragna_staging | gzip > /backups/staging_$(date +\%Y\%m\%d).sql.gz

mkdir -p /backups
```

---

## Resource usage on KVM 2 (8 GB RAM)

| Component | Memory |
|-----------|--------|
| K3s + Traefik | ~512 MB |
| cert-manager | ~128 MB |
| Production API (blue or green) | 256–512 MB |
| Production UI | 64–128 MB |
| Staging postgres | 256–512 MB |
| Staging API | 256–512 MB |
| Staging UI | 64–128 MB |
| OS overhead | ~400 MB |
| **Total** | **~2–3 GB** |
| **Headroom** | **~5 GB** |

---

## Quick reference

| Task | How |
|------|-----|
| Deploy to staging | Actions → Build and Push → environment: staging |
| Deploy to production | Actions → Build and Push → environment: production |
| Rollback production | `kubectl patch service pragna-api -n pragna --type=merge -p '{"spec":{"selector":{"app":"pragna-api","slot":"blue"}}}'` |
| Check active slot | `kubectl get svc pragna-api -n pragna -o jsonpath='{.spec.selector.slot}'` |
| Watch pods | `kubectl get pods -n pragna -w` |
| View logs | `kubectl logs deployment/pragna-api -n pragna` |
| Health check prod | `curl -s https://pragna.sgummallaworks.com/health` |
| Health check staging | `curl -s https://pragna-staging.sgummallaworks.com/health` |
