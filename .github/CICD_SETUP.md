# CI/CD Pipeline Setup - Simple Guide

## ⚡ Quick Start

**3 things you need to configure:**

1. Get Fly.io token: `flyctl auth token`
2. Add GitHub Secrets: `FLY_API_TOKEN`, `VITE_CLERK_PUBLISHABLE_KEY`
3. Add GitHub Variable: `VITE_API_BASE_URL`

👉 **[Jump to detailed setup instructions](#-setup-instructions-5-minutes)**

👉 **[Jump to deployment guide](DEPLOYMENT.md)** for release management

---

## Overview

Your GitHub Actions CI/CD pipeline automatically:
1. ✅ **Triggers** when you create a GitHub release (not on every push)
2. ✅ **Build and test** backend (484 tests) and frontend
3. ✅ **Ensure Postgres DB** is running (`speakly-db`)
4. ✅ **Deploy backend and frontend** with robust health checks
5. ✅ **Polls machine status** until healthy or timeout (10 mins)

**Controlled deployments** - Deploy when YOU create a release!

## Workflow Structure

### Workflows Created/Modified

1. **`fly-deploy.yml`** - Main CI/CD pipeline (runs on GitHub release)
2. **`backend-ci.yml`** - Backend tests (runs only on pull requests)
3. **`frontend-ci.yml`** - Frontend tests (runs only on pull requests)

### Pipeline Flow

```
Create GitHub Release
    ↓
┌───────────────────────────────┐
│  Build & Test (Parallel)     │
│  - Backend (484 tests)        │
│  - Frontend (npm build)       │
└───────────┬───────────────────┘
            ↓
    ┌─────────────────────┐
    │ Ensure Postgres DB  │
    │ (speakly-db)        │
    └─────────┬───────────┘
              ↓
    ┌──────────────────────┐
    │  Deploy (Parallel)   │
    │  - Backend           │
    │  - Frontend          │
    └──────────┬───────────┘
               ↓
    ┌─────────────────────────┐
    │  Health Checks          │
    │  - Poll every 15s       │
    │  - Timeout: 10 mins     │
    │  - Wait for "started"   │
    └─────────────────────────┘
```

---

## 🚀 Setup Instructions (5 minutes)

### Step 1: Get Your Fly.io API Token

1. Run this command in your terminal:
   ```bash
   flyctl auth token
   ```

2. Copy the token that appears (starts with `fly_...`)

### Step 2: Configure GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** (top right)
3. Click **Secrets and variables** → **Actions** (left sidebar)
4. Click **Secrets** tab
5. Click **New repository secret** button

Add these **2 secrets**:

#### Secret 1: `FLY_API_TOKEN`
- **Name:** `FLY_API_TOKEN`
- **Value:** Paste your Fly.io token from Step 1
- Click **Add secret**

#### Secret 2: `VITE_CLERK_PUBLISHABLE_KEY`
- **Name:** `VITE_CLERK_PUBLISHABLE_KEY`
- **Value:** Your Clerk publishable key (e.g., `pk_test_...` or `pk_live_...`)
- Click **Add secret**

### Step 3: Configure GitHub Variables

1. Still in **Settings → Secrets and variables → Actions**
2. Click **Variables** tab (next to Secrets)
3. Click **New repository variable**

#### Variable: `VITE_API_BASE_URL`
- **Name:** `VITE_API_BASE_URL`
- **Value:** `https://speakly-backend.fly.dev`
- Click **Add variable**

### ✅ Setup Complete!

Your CI/CD pipeline is now ready. When you create a GitHub release:
- Build and test your code
- Deploy to Fly.io if tests pass
- Wait for all machines to be healthy (with 10-min timeout)

**See [DEPLOYMENT.md](DEPLOYMENT.md) for how to create releases and deploy!**

## How It Works

### On GitHub Release

**Trigger**: When you publish a release on GitHub (e.g., `v1.0.0`)

1. **Backend Build & Test**
   - Sets up Python 3.11
   - Installs dependencies from `backend/requirements-dev.txt`
   - Runs full pytest suite (484 tests)
   - Uses SQLite for testing (no external dependencies)
   - 73% code coverage enforced

2. **Frontend Build & Test**
   - Sets up Node.js 20
   - Installs npm dependencies
   - Runs production build
   - Uses dummy credentials for build

3. **Ensure Postgres DB**
   - Checks `speakly-db` machine status
   - Starts any stopped machines
   - Waits for machines to be healthy

4. **Deploy Backend**
   - Deploys to `speakly-backend` app
   - Uses `fly.toml` configuration
   - **NEW**: Robust polling mechanism (10 min timeout)
     - Polls every 15 seconds
     - Tracks state transitions: `replacing` → `starting` → `started`
     - Auto-starts stopped machines
     - Fails gracefully with clear errors

5. **Deploy Frontend** (runs in parallel with backend)
   - Deploys to `speakly-frontend` app
   - Uses `frontend/fly.toml` configuration
   - Passes build args for Clerk and API URL
   - **NEW**: Same robust health checks as backend

### On Pull Requests

- `backend-ci.yml` runs backend tests only
- `frontend-ci.yml` runs frontend build only
- No deployment occurs

### Manual Trigger

You can also trigger manually:
- Via GitHub Actions UI: "Run workflow" button
- Via CLI: `gh workflow run "CI/CD Pipeline"`

## Flyctl Commands Used

The workflows use corrected `flyctl` syntax:

```bash
# Check status
flyctl status --app <app-name> --json

# Start machine
flyctl machine start <machine-id> --app <app-name>

# Deploy with build args
flyctl deploy \
  --app <app-name> \
  --config <path-to-fly.toml> \
  --remote-only \
  --strategy immediate \
  --build-arg KEY=value
```

## Key Fixes from Previous Workflow

### Fixed Syntax Errors:
1. ✅ Corrected `flyctl machines start` → `flyctl machine start`
2. ✅ Fixed JSON parsing: `.State` → `.state`, `.ID` → `.id`
3. ✅ Proper handling of `--app` flag placement
4. ✅ Correct `--build-arg` syntax for frontend build args
5. ✅ Added error handling for Postgres status checks
6. ✅ Removed unused `FLY_POSTGRES_APP` variable (hardcoded to `speakly-db`)

## Testing the Pipeline

### Method 1: Create a Test Release
```bash
# Create and publish a test release
gh release create v0.0.1-test \
  --title "Test Release" \
  --notes "Testing CI/CD pipeline" \
  --prerelease

# Watch the workflow
gh run watch
```

### Method 2: Manual Workflow Trigger
```bash
# Trigger workflow manually (bypass release requirement)
gh workflow run "CI/CD Pipeline"

# Watch it run
gh run watch
```

### Method 3: Via GitHub UI
1. Go to your repository on GitHub
2. Click **Releases** → **Draft a new release**
3. Create a new tag (e.g., `v0.0.1-test`)
4. Mark as "pre-release" if testing
5. Click **Publish release**
6. Go to **Actions** tab to watch the workflow

## Monitoring Deployments

- **GitHub Actions UI**: See all steps and logs
- **Fly.io Dashboard**: Monitor app health and metrics
- **Fly.io CLI**: 
  ```bash
  flyctl status --app speakly-backend
  flyctl status --app speakly-frontend
  flyctl status --app speakly-db
  ```

## Troubleshooting

### Pipeline fails at "Ensure Postgres DB"
- Verify `FLY_API_TOKEN` is set correctly
- Check that `speakly-db` app exists: `flyctl apps list`

### Backend deployment fails
- Check secrets are set: `flyctl secrets list --app speakly-backend`
- Review logs: `flyctl logs --app speakly-backend`

### Frontend deployment fails
- Ensure `VITE_CLERK_PUBLISHABLE_KEY` and `VITE_API_BASE_URL` are set
- Check build args in workflow logs

### Deployment happens immediately (no approval)
- This is expected! The workflow deploys automatically after tests pass
- To manually control deployments, use `workflow_dispatch` to trigger manually

## Testing Your Pipeline

### Quick Test: Create a Test Release

```bash
# Create a pre-release for testing
gh release create v0.0.1-test \
  --title "Test Release v0.0.1" \
  --notes "Testing the CI/CD pipeline" \
  --prerelease

# Watch it run in real-time
gh run watch

# Or view logs after completion
gh run view --log
```

### Monitor the Deployment

```bash
# Watch backend logs during deployment
flyctl logs --app speakly-backend -f

# Check deployment status with detailed machine states
flyctl status --app speakly-backend
flyctl status --app speakly-frontend

# Verify all machines are "started"
flyctl status --app speakly-backend --json | jq '.Machines[] | {id, state}'
```

---

## Summary

✅ **Release-triggered deployments** - deploy when YOU create a release  
✅ **484 tests enforced** - deployment only happens if all tests pass  
✅ **Robust health checks** - polls machine status for 10 mins until healthy  
✅ **Parallel deployments** - backend and frontend deploy simultaneously  
✅ **Auto-recovery** - automatically starts stopped machines  
✅ **Graceful failures** - clear error messages with timeout handling

**Need to deploy?** See [DEPLOYMENT.md](DEPLOYMENT.md) for release management guide  
**Questions?** Review the workflow file at `.github/workflows/fly-deploy.yml`
