# Deployment Guide

## Overview

The CI/CD pipeline automatically tests and deploys Speakly when you create a GitHub release.

## Trigger: GitHub Releases

**Deployments now trigger on release creation, not on every push to main.**

### Why?
- **Control**: You decide exactly when to deploy
- **Stability**: Only release tested, stable versions
- **Versioning**: Semantic versioning tied to deployments
- **Rollback**: Easy to track which release caused issues

## How to Deploy

### 1. Create a Release on GitHub

```bash
# Option A: Via GitHub UI
# 1. Go to https://github.com/prajwalppv/speakly/releases/new
# 2. Create a new tag (e.g., v1.0.0, v1.0.1)
# 3. Enter release title and description
# 4. Click "Publish release"

# Option B: Via GitHub CLI
gh release create v1.0.0 --title "Release v1.0.0" --notes "Bug fixes and improvements"

# Option C: Via Git tags (pushes tag and triggers workflow_dispatch)
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
# Then create release from tag in GitHub UI
```

### 2. Automatic Pipeline Execution

Once you publish the release, the CI/CD pipeline automatically:

1. ✅ **Tests Backend** - Runs full pytest suite (484 tests)
2. ✅ **Tests Frontend** - Builds and validates frontend
3. ✅ **Ensures Postgres** - Wakes up database if sleeping
4. 🚀 **Deploys Backend** - With robust health checks
5. 🚀 **Deploys Frontend** - With robust health checks

## Deployment Health Checks

### New Robust Polling Mechanism

Both backend and frontend deployments now use **intelligent polling** with:

#### Configuration
- **Timeout**: 10 minutes (600 seconds) - configurable
- **Poll Interval**: 15 seconds
- **States Monitored**: `started`, `starting`, `replacing`, `stopped`

#### What It Does
1. **Polls** machine status every 15 seconds
2. **Tracks** state transitions (`replacing` → `starting` → `started`)
3. **Auto-starts** any stopped machines
4. **Waits** for ALL machines to reach `started` state
5. **Fails gracefully** with clear error messages if timeout reached

#### Example Output
```
Checking status (0s elapsed)...
  Total: 1 | Started: 0 | Starting: 0 | Replacing: 1 | Stopped: 0
  Machines still transitioning. Waiting 15s...

Checking status (15s elapsed)...
  Total: 1 | Started: 0 | Starting: 1 | Replacing: 0 | Stopped: 0
  Machines still transitioning. Waiting 15s...

Checking status (30s elapsed)...
  Total: 1 | Started: 1 | Starting: 0 | Replacing: 0 | Stopped: 0
✅ All 1 backend machines are running!
```

## Manual Deployment

You can still trigger deployments manually:

### Via GitHub UI
1. Go to **Actions** tab
2. Select **CI/CD Pipeline** workflow
3. Click **Run workflow** button
4. Select branch and run

### Via GitHub CLI
```bash
gh workflow run "CI/CD Pipeline" --ref main
```

## Customizing Timeout

To change the deployment timeout, edit `.github/workflows/fly-deploy.yml`:

```yaml
- name: Verify backend deployment
  run: |
    TIMEOUT=900  # Change to 15 minutes (900 seconds)
    POLL_INTERVAL=20  # Change polling interval to 20 seconds
    # ... rest of script
```

## Monitoring Deployments

### View Live Logs
```bash
# Watch workflow in real-time
gh run watch

# View specific run logs
gh run view <run-id> --log
```

### Check App Status
```bash
# Backend
flyctl status --app speakly-backend

# Frontend  
flyctl status --app speakly-frontend

# Database
flyctl status --app speakly-db
```

## Troubleshooting

### Deployment Times Out

**Symptom**: "Timeout after 600s waiting for machines to start"

**Solutions**:
1. Check Fly.io dashboard for deployment errors
2. Increase `TIMEOUT` in workflow (default: 10 min)
3. Check machine health: `flyctl logs --app speakly-backend`
4. Verify resources: `flyctl scale show --app speakly-backend`

### Machines Stuck in "Replacing" State

**Symptom**: Machines never transition from `replacing` to `started`

**Solutions**:
1. Check deployment logs: `flyctl logs --app speakly-backend`
2. Manually restart: `flyctl machine restart <machine-id> --app speakly-backend`
3. Check for build errors in Actions logs

### Database Connection Issues

**Symptom**: Backend starts but can't connect to database

**Solutions**:
1. Ensure Postgres is running: `flyctl status --app speakly-db`
2. Check connection string in secrets
3. Review database logs: `flyctl logs --app speakly-db`

## Rollback Strategy

### Quick Rollback
```bash
# List recent releases
gh release list

# Deploy specific version (create new release or use workflow_dispatch)
# 1. Tag the commit you want to rollback to
# 2. Create a new release from that tag
# 3. Pipeline will automatically deploy that version
```

### Manual Rollback
```bash
# Rollback to previous image
flyctl deploy --app speakly-backend --image <previous-image>
```

## Best Practices

### Release Versioning

Use semantic versioning:
- **v1.0.0** - Major release (breaking changes)
- **v1.1.0** - Minor release (new features)
- **v1.1.1** - Patch release (bug fixes)

### Pre-Release Testing

1. Create a **pre-release** for testing:
   ```bash
   gh release create v1.0.0-rc1 --prerelease --title "Release Candidate 1"
   ```

2. Test thoroughly before full release

3. Promote to full release:
   ```bash
   gh release edit v1.0.0-rc1 --latest --prerelease=false
   ```

### Release Notes Template

```markdown
## 🚀 Features
- New audio upload improvements
- Enhanced transcription accuracy

## 🐛 Bug Fixes  
- Fixed session filtering by user
- Resolved authentication bypass in tests

## 🔧 Improvements
- Optimized database queries
- Improved error handling

## 📝 Testing
- All 484 tests passing
- 73% code coverage

## 🔄 Breaking Changes
- None
```

## Environment Variables

The workflow uses these secrets/variables (configured in GitHub Settings):

### Secrets (Settings → Secrets and variables → Actions)
- `FLY_API_TOKEN` - Fly.io API token
- `VITE_CLERK_PUBLISHABLE_KEY` - Clerk authentication key

### Variables
- `VITE_API_BASE_URL` - Backend API URL

## Support

For issues with deployments:
1. Check GitHub Actions logs
2. Review Fly.io dashboard
3. Check application logs: `flyctl logs`
4. Open GitHub issue with deployment logs
