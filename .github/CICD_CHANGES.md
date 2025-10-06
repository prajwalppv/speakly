# CI/CD Pipeline Changes Summary

## Overview

Made the CI/CD pipeline more **reliable, robust, and controlled** with two major improvements:

1. ✅ **Release-based deployments** (not on every push)
2. ✅ **Robust polling with timeout** (not brittle one-time checks)

---

## Change 1: Trigger on GitHub Releases

### Before
```yaml
on:
  push:
    branches: [ main ]
```
- Deployed on every push to main
- No control over when deployments happen
- Hard to track which code version is deployed

### After
```yaml
on:
  release:
    types: [published]
```
- Deploys only when you create a GitHub release
- Full control over deployment timing
- Semantic versioning tied to deployments
- Easy rollback by creating release from old tag

### How to Deploy Now

```bash
# Option 1: Via GitHub CLI
gh release create v1.0.0 --title "Release v1.0.0" --notes "Bug fixes"

# Option 2: Via GitHub UI
# Go to Releases → Draft a new release → Publish

# Option 3: Manual trigger (bypass release)
gh workflow run "CI/CD Pipeline"
```

---

## Change 2: Robust Polling with Timeout

### The Problem You Reported

```
PROCESS ID              VERSION REGION STATE     ROLE CHECKS             LAST UPDATED         
app     1853064c5e2778  18      sjc    replacing      1 total, 1 warning 2025-10-06T02:02:39Z

Starting stopped backend machines...
Starting machine: 1853064c5e2778
```

**Issue**: The script only checked ONCE and didn't wait for the state to transition from `replacing` → `started`.

### The Solution: Intelligent Polling

```bash
TIMEOUT=600  # 10 minutes (configurable)
POLL_INTERVAL=15  # Check every 15 seconds

while [ $ELAPSED -lt $TIMEOUT ]; do
  # Get machine states
  started=$(echo "$status" | jq -r '[.Machines[] | select(.state == "started")] | length')
  replacing=$(echo "$status" | jq -r '[.Machines[] | select(.state == "replacing")] | length')
  starting=$(echo "$status" | jq -r '[.Machines[] | select(.state == "starting")] | length')
  
  echo "Total: $total | Started: $started | Starting: $starting | Replacing: $replacing"
  
  # Success: All machines started
  if [ "$started" -eq "$total" ]; then
    echo "✅ All machines running!"
    exit 0
  fi
  
  # Wait and retry
  sleep $POLL_INTERVAL
  ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

# Timeout
echo "❌ Timeout after ${TIMEOUT}s"
exit 1
```

### What It Does

1. **Polls every 15 seconds** (not just once)
2. **Tracks all states**: `started`, `starting`, `replacing`, `stopped`
3. **Auto-starts** stopped machines
4. **Waits for transitions**: `replacing` → `starting` → `started`
5. **Times out gracefully** after 10 minutes with clear error
6. **Provides visibility**: Shows state counts on each poll

### Example Output

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

---

## Configuration

### Adjust Timeout

Edit `.github/workflows/fly-deploy.yml`:

```bash
# Backend deployment verification (line ~167)
TIMEOUT=900  # Change to 15 minutes
POLL_INTERVAL=20  # Poll every 20 seconds

# Frontend deployment verification (line ~249)  
TIMEOUT=900  # Change to 15 minutes
POLL_INTERVAL=20  # Poll every 20 seconds
```

### Typical Deployment Times

Based on Fly.io:
- **Fast**: 30-60 seconds (small changes, warm machines)
- **Normal**: 1-3 minutes (code changes, rebuilds)
- **Slow**: 3-5 minutes (cold start, resource constraints)
- **Timeout**: 10 minutes (default) - Should never reach this

---

## Applied To

Both deployment verification steps now use robust polling:

1. **Backend deployment** (`speakly-backend`)
   - Lines 163-218 in `fly-deploy.yml`
   
2. **Frontend deployment** (`speakly-frontend`)
   - Lines 245-301 in `fly-deploy.yml`

---

## Files Changed

1. **`.github/workflows/fly-deploy.yml`**
   - Changed trigger: `push.branches` → `release.types`
   - Added polling logic to backend verification
   - Added polling logic to frontend verification

2. **`.github/DEPLOYMENT.md`** (NEW)
   - Complete deployment guide
   - Release management instructions
   - Troubleshooting guide

3. **`.github/CICD_SETUP.md`** (UPDATED)
   - Updated overview to reflect release trigger
   - Added references to DEPLOYMENT.md
   - Updated pipeline flow diagram
   - Updated testing instructions

4. **`.github/CICD_CHANGES.md`** (NEW - this file)
   - Summary of all changes
   - Before/after comparisons

---

## Testing the Changes

### Test 1: Create a Pre-Release

```bash
gh release create v0.0.1-test \
  --title "Test: CI/CD Pipeline" \
  --notes "Testing new polling mechanism" \
  --prerelease

gh run watch
```

**Expected behavior**:
- Workflow triggers automatically
- Tests run (484 tests)
- Backend deploys
- Polling shows state transitions
- Waits for "started" state
- Frontend deploys
- Polling shows state transitions
- Success message appears

### Test 2: Manual Trigger

```bash
gh workflow run "CI/CD Pipeline"
gh run watch
```

### Test 3: Monitor State Transitions

While deployment is running:

```bash
# In another terminal, watch machine states
watch -n 5 'flyctl status --app speakly-backend'
```

You should see states change:
- `replacing` (old machine being replaced)
- `starting` (new machine starting)
- `started` (new machine ready)

---

## Rollback

If you need to revert to the old workflow:

```bash
# Checkout the old version
git log --oneline .github/workflows/fly-deploy.yml
git checkout <commit-before-changes> .github/workflows/fly-deploy.yml

# Or manually edit:
# 1. Change trigger back to: push.branches: [main]
# 2. Remove polling logic from verification steps
```

---

## Benefits

### Before
- ❌ Deployed on every push (no control)
- ❌ Single check (missed state transitions)
- ❌ Failed when machines were "replacing"
- ❌ No timeout (hung indefinitely or failed quickly)
- ❌ No visibility into what's happening

### After
- ✅ Deploy on release (full control)
- ✅ Continuous polling (catches all transitions)
- ✅ Waits for "started" state (handles replacing)
- ✅ 10-minute timeout (fails gracefully)
- ✅ Clear output showing machine states
- ✅ Auto-recovery (starts stopped machines)
- ✅ Works reliably in CI environment

---

## Questions?

- **How to deploy?** → See [DEPLOYMENT.md](DEPLOYMENT.md)
- **How does polling work?** → See workflow lines 163-218, 245-301
- **How to customize timeout?** → Edit `TIMEOUT` variable in workflow
- **How to rollback?** → Create new release from old tag

## Support

If deployment fails:
1. Check Actions logs for detailed error
2. Review machine states: `flyctl status --app speakly-backend`
3. Check timeout value (default 10 mins)
4. Review Fly.io dashboard for resource issues
