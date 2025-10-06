# CI/CD Pipeline Setup - Simple Guide

## ⚡ Quick Start

**3 things you need to configure:**

1. Get Fly.io token: `flyctl auth token`
2. Add GitHub Secrets: `FLY_API_TOKEN`, `VITE_CLERK_PUBLISHABLE_KEY`
3. Add GitHub Variable: `VITE_API_BASE_URL`

👉 **[Jump to detailed setup instructions](#-setup-instructions-5-minutes)**

---

## Overview

Your GitHub Actions CI/CD pipeline automatically:
1. ✅ **Build and test** backend and frontend on every push to `main`
2. ✅ **Ensure Postgres DB** is running (`speakly-db`)
3. ✅ **Deploy backend and frontend in parallel** to Fly.io

**No manual approval needed** - deploys happen automatically after tests pass!

## Workflow Structure

### Workflows Created/Modified

1. **`fly-deploy.yml`** - Main CI/CD pipeline (runs on push to `main`)
2. **`backend-ci.yml`** - Backend tests (runs only on pull requests)
3. **`frontend-ci.yml`** - Frontend tests (runs only on pull requests)

### Pipeline Flow

```
Push to main
    ↓
┌───────────────────────────────┐
│  Build & Test (Parallel)     │
│  - Backend (pytest)           │
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
    └──────────────────────┘
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

Your CI/CD pipeline is now ready. Every push to `main` will automatically:
- Build and test your code
- Deploy to Fly.io if tests pass

## How It Works

### On Push to Main

1. **Backend Build & Test**
   - Sets up Python 3.11
   - Installs dependencies from `backend/requirements-dev.txt`
   - Runs pytest suite
   - Uses SQLite for testing (no external dependencies)

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
   - Verifies machines are running after deployment

5. **Deploy Frontend** (runs in parallel with backend)
   - Deploys to `speakly-frontend` app
   - Uses `frontend/fly.toml` configuration
   - Passes build args for Clerk and API URL
   - Verifies machines are running after deployment

### On Pull Requests

- `backend-ci.yml` runs backend tests only
- `frontend-ci.yml` runs frontend build only
- No deployment occurs

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

### Manual Test
```bash
# Trigger workflow manually
gh workflow run "CI/CD Pipeline"
```

### Automatic Test
1. Make a change to any file
2. Commit and push to `main`:
   ```bash
   git add .
   git commit -m "Test CI/CD pipeline"
   git push origin main
   ```
3. Go to **Actions** tab in GitHub
4. Watch the workflow run
5. Approve deployment when prompted

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

### Quick Test

Make a small change and push to `main`:

```bash
# Make a small change (e.g., add a comment to README)
echo "# Testing CI/CD" >> README.md

# Commit and push
git add README.md
git commit -m "Test CI/CD pipeline"
git push origin main
```

Then watch it run:
1. Go to your GitHub repository
2. Click **Actions** tab
3. Watch the "CI/CD Pipeline" workflow run
4. See each step execute (build → test → deploy)

### Monitor the Deployment

```bash
# Watch backend logs
flyctl logs --app speakly-backend -f

# Check status
flyctl status --app speakly-backend
flyctl status --app speakly-frontend
```

---

## Summary

✅ **Automatic deployments** on every push to `main`  
✅ **Tests run first** - deployment only happens if tests pass  
✅ **Parallel deployments** - backend and frontend deploy simultaneously  
✅ **No manual approval needed** - perfect for personal projects

**Questions?** Review the workflow file at `.github/workflows/fly-deploy.yml`
