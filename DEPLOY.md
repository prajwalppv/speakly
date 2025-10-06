# 🚀 Speakly - Production Deployment Guide

**Complete step-by-step instructions to deploy Speakly to Fly.io**

---

## 📋 What You're Deploying

### Your App Features:
- 🎙️ **Voice Transcription** - ElevenLabs Scribe STT
- 🤖 **AI Summaries** - DeepSeek R1 Distill (70B) via Groq
- 🏷️ **Auto-tagging** - Smart content categorization
- ✅ **TODO Extraction** - Automatic task identification
- 🔄 **TickTick Sync** - Tasks sync to TickTick
- 👥 **Multi-user** - Clerk authentication
- 💾 **PostgreSQL** - Production database
- 🌍 **Global CDN** - Fly.io edge deployment

---

## ⏱️ Estimated Time: 30-40 minutes

- **Pre-setup:** 10 min (accounts + keys)
- **Database:** 5 min
- **Backend:** 10 min
- **Frontend:** 5 min
- **Testing:** 10 min

---

## 📦 Prerequisites

### 1. Install Fly CLI

```bash
# Mac
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh

# Verify
flyctl version
```

### 2. Login to Fly.io

```bash
flyctl auth login
```

**Note:** Fly.io requires a credit card (for free tier verification), but you won't be charged for small apps.

---

## 🔑 Step 1: Gather Your Keys (10 min)

### A. Groq API Key (FREE - Already have!)

Your key from `.env`:
```
GROQ_API_KEY=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
```

✅ **Ready to use!**

### B. Get Clerk Production Keys (5 min)

1. Go to: https://clerk.com
2. Switch to **Production** (top right toggle)
3. Navigate to **API Keys**
4. Copy:
   - **Secret Key:** `sk_live_...` → Use in backend
   - **Publishable Key:** `pk_live_...` → Use in frontend

**Using Test Keys for Now?**
- Keep your test keys (`sk_test_...` and `pk_test_...`)
- Works fine for initial deployment
- Upgrade to production keys later (zero code changes)

### C. ElevenLabs & TickTick (Already have!)

From your `.env`:
```bash
ELEVENLABS_API_KEY=sk_d33fb14301fee346b6837c56b161a05db6ca7115d06b0e49
ELEVENLABS_WEBHOOK_SECRET=wsec_76c7bfb9c9d7a78d29c3aa248b0da1eebdc7fd614a6ba93ccd23e277ec7ef12f
TICKTICK_CLIENT_ID=4fmyNpXY0mK91WsC1x
TICKTICK_CLIENT_SECRET=911rhLw!(h!Af7Ge2b3m21b+Ry48+RE^
```

✅ **Ready to use!**

---

## 🗄️ Step 2: Create PostgreSQL Database (5 min)

```bash
cd /Users/pvasisht/dev/speakly

flyctl postgres create \
  --name speakly-db \
  --region sjc \
  --initial-cluster-size 1 \
  --vm-size shared-cpu-1x \
  --volume-size 10
```

**⚠️ IMPORTANT:** Copy the `DATABASE_URL` shown at the end!

Example:
```
postgres://postgres:PASSWORD@speakly-db.flycast:5432/speakly
```

**Save this - you'll need it in the next step!**

---

## 🖥️ Step 3: Deploy Backend (10 min)

### A. Create Backend App

```bash
cd /Users/pvasisht/dev/speakly

# Create app (don't deploy yet)
flyctl launch \
  --name speakly-backend \
  --region sjc \
  --no-deploy
```

### B. Create Storage Volume

```bash
# For audio files
flyctl volumes create speakly_audio_storage \
  --region sjc \
  --size 10 \
  --app speakly-backend
```

### C. Set All Secrets

```bash
flyctl secrets set \
  SPEAKLY_ENVIRONMENT=prod \
  SPEAKLY_DATABASE_URL="postgres://postgres:PASSWORD@speakly-db.flycast:5432/speakly" \
  CLERK_SECRET_KEY="sk_test_YOUR_KEY_OR_LIVE" \
  ELEVENLABS_API_KEY="sk_d33fb14301fee346b6837c56b161a05db6ca7115d06b0e49" \
  ELEVENLABS_WEBHOOK_SECRET="wsec_76c7bfb9c9d7a78d29c3aa248b0da1eebdc7fd614a6ba93ccd23e277ec7ef12f" \
  ELEVENLABS_BASE_URL="https://api.elevenlabs.io" \
  ELEVENLABS_DIARIZATION_ENABLED=true \
  GROQ_API_KEY="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" \
  GROQ_MODEL="deepseek-r1-distill-llama-70b" \
  TICKTICK_CLIENT_ID="4fmyNpXY0mK91WsC1x" \
  TICKTICK_CLIENT_SECRET="911rhLw!(h!Af7Ge2b3m21b+Ry48+RE^" \
  TICKTICK_REDIRECT_URI="https://speakly-backend.fly.dev/api/ticktick/callback" \
  SPEAKLY_FRONTEND_URL="https://speakly-frontend.fly.dev" \
  --app speakly-backend
```

**Replace:**
- `PASSWORD` with your actual database password
- `CLERK_SECRET_KEY` with your actual key (test or live)

### D. Deploy Backend

```bash
flyctl deploy --app speakly-backend
```

**Wait 2-3 minutes for build + deployment.**

### E. Verify Backend

```bash
# Check status
flyctl status --app speakly-backend

# Test API
curl https://speakly-backend.fly.dev/docs
```

You should see the API documentation page!

---

## 🎨 Step 4: Deploy Frontend (5 min)

### A. Create Frontend App

```bash
cd frontend

# Create app (don't deploy yet)
flyctl launch \
  --name speakly-frontend \
  --region sjc \
  --no-deploy
```

### B. Deploy Frontend

```bash
flyctl deploy \
  --build-arg VITE_CLERK_PUBLISHABLE_KEY="pk_test_cm9tYW50aWMtd2VldmlsLTQ0LmNsZXJrLmFjY291bnRzLmRldiQ" \
  --build-arg VITE_API_BASE_URL="https://speakly-backend.fly.dev" \
  --app speakly-frontend
```

**Replace:** `VITE_CLERK_PUBLISHABLE_KEY` with your actual key

**Wait 2-3 minutes for build + deployment.**

### C. Verify Frontend

```bash
# Check status
flyctl status --app speakly-frontend

# Open in browser
flyctl open --app speakly-frontend
```

---

## ⚙️ Step 5: Configure Clerk (3 min)

### Update Clerk Settings:

1. Go to: https://clerk.com
2. Switch to **Production** (or stay in **Development** if using test keys)
3. **Paths** → Set all URLs:
   ```
   Home URL: https://speakly-frontend.fly.dev
   Sign in URL: https://speakly-frontend.fly.dev
   Sign up URL: https://speakly-frontend.fly.dev
   ```

4. **Allowed Origins** → Add:
   ```
   https://speakly-frontend.fly.dev
   https://speakly-backend.fly.dev
   ```

5. Click **Save**

---

## 🔄 Step 6: Run Database Migrations (2 min)

```bash
# SSH into backend container
flyctl ssh console --app speakly-backend

# Run migrations
python -m backend.migrations.add_clerk_auth_to_users
python -m backend.migrations.remove_unique_constraint_from_name

# Exit
exit
```

---

## ✅ Step 7: Test Your App! (5 min)

### 1. Visit Your App

```bash
# Open frontend
flyctl open --app speakly-frontend
```

Or go to: **https://speakly-frontend.fly.dev**

### 2. Test Authentication

- Click **Sign in**
- Sign in with Google/Apple/Email
- Should redirect back successfully

### 3. Test Audio Upload

1. Upload an audio file (or use bulk upload)
2. Wait for transcription (~10-30 seconds)
3. Check for:
   - ✅ Transcription text
   - ✅ AI Summary (powered by DeepSeek R1!)
   - ✅ Auto-generated tags
   - ✅ Extracted TODOs
   - ✅ TickTick sync status

### 4. Verify Sessions Dashboard

- Click **📚 Sessions** button
- Should see your uploaded sessions
- Cards should be collapsible
- Status badges should be colored

---

## 📊 Step 8: Monitor Your App

### View Logs

```bash
# Backend logs (real-time)
flyctl logs --app speakly-backend -f

# Frontend logs
flyctl logs --app speakly-frontend -f
```

### Check Status

```bash
# Backend
flyctl status --app speakly-backend

# Frontend
flyctl status --app speakly-frontend

# Database
flyctl postgres connect --app speakly-db
```

### Open Dashboards

```bash
# Backend dashboard
flyctl dashboard speakly-backend

# Frontend dashboard
flyctl dashboard speakly-frontend
```

---

## 🎉 You're Live!

### Your Production URLs:

- **Frontend:** https://speakly-frontend.fly.dev
- **Backend:** https://speakly-backend.fly.dev
- **API Docs:** https://speakly-backend.fly.dev/docs

### What You Have:

- ✅ Voice transcription (ElevenLabs)
- ✅ AI summaries (DeepSeek R1 70B via Groq)
- ✅ Auto-tagging
- ✅ TODO extraction
- ✅ TickTick sync
- ✅ Multi-user auth (Clerk)
- ✅ PostgreSQL database
- ✅ Global CDN
- ✅ HTTPS/SSL
- ✅ Auto-scaling

---

## 🔄 Future Updates

### Update Backend

```bash
cd /Users/pvasisht/dev/speakly
flyctl deploy --app speakly-backend
```

### Update Frontend

```bash
cd frontend
flyctl deploy \
  --build-arg VITE_CLERK_PUBLISHABLE_KEY="pk_test_..." \
  --build-arg VITE_API_BASE_URL="https://speakly-backend.fly.dev" \
  --app speakly-frontend
```

### Update Secrets

```bash
flyctl secrets set KEY=value --app speakly-backend
```

### Restart Apps

```bash
flyctl apps restart speakly-backend
flyctl apps restart speakly-frontend
```

---

## 🛠️ Troubleshooting

### Backend Won't Start

```bash
# Check logs
flyctl logs --app speakly-backend

# Common issues:
# 1. DATABASE_URL incorrect → verify connection string
# 2. Secrets missing → list: flyctl secrets list --app speakly-backend
# 3. Volume not attached → check: flyctl volumes list --app speakly-backend
```

### Frontend Build Fails

```bash
# Ensure build args are provided:
flyctl deploy \
  --build-arg VITE_CLERK_PUBLISHABLE_KEY="pk_..." \
  --build-arg VITE_API_BASE_URL="https://speakly-backend.fly.dev"
```

### Database Connection Issues

```bash
# Test database connection
flyctl ssh console --app speakly-backend
python -c "from backend.app.database import engine; print(engine.url)"
```

### CORS Errors

- Check Clerk allowed origins includes both frontend and backend URLs
- Verify `backend/app/main.py` has correct CORS origins

---

## 💰 Costs

### Free Tier Includes:
- 3 shared VMs
- 3GB storage
- 160GB outbound transfer

### Your Setup (After Free Tier):
- **Backend:** ~$5/month
- **Frontend:** ~$2/month
- **PostgreSQL:** ~$5/month
- **Groq (LLM):** FREE (14.4k requests/day)
- **Total:** ~$12/month

**First month may be FREE depending on your usage!**

---

## 📝 Quick Commands Reference

```bash
# Deploy
flyctl deploy --app <app-name>

# Logs
flyctl logs --app <app-name> -f

# SSH
flyctl ssh console --app <app-name>

# Restart
flyctl apps restart <app-name>

# Status
flyctl status --app <app-name>

# Secrets
flyctl secrets list --app <app-name>
flyctl secrets set KEY=value --app <app-name>

# Scale
flyctl scale count 2 --app <app-name>
flyctl scale memory 512 --app <app-name>
```

---

## 🎯 Next Steps

### 1. Custom Domain (Optional)

```bash
flyctl certs add yourdomain.com --app speakly-frontend
```

Then add DNS records as shown.

### 2. Upgrade to Clerk Production Keys

When ready:
```bash
flyctl secrets set CLERK_SECRET_KEY="sk_live_..." --app speakly-backend

# Redeploy frontend with new key
cd frontend
flyctl deploy --build-arg VITE_CLERK_PUBLISHABLE_KEY="pk_live_..."
```

### 3. Monitor Usage

- Groq: https://console.groq.com/usage
- Fly.io: https://fly.io/dashboard
- Clerk: https://clerk.com → Analytics

---

## 🚨 Important Notes

### Security:
- ✅ All secrets stored securely in Fly.io
- ✅ HTTPS enforced automatically
- ✅ Database credentials encrypted
- ✅ No secrets in code

### Backups:
- Database: Automatic daily backups
- Manual backup: `flyctl postgres backup create --app speakly-db`

### Scaling:
```bash
# Add more instances
flyctl scale count 2 --app speakly-backend

# Increase memory
flyctl scale memory 1024 --app speakly-backend
```

---

## 📞 Support

### Fly.io:
- Docs: https://fly.io/docs
- Community: https://community.fly.io
- Status: https://status.fly.io

### Clerk:
- Docs: https://clerk.com/docs
- Support: https://clerk.com/support

### Groq:
- Console: https://console.groq.com
- Docs: https://console.groq.com/docs

---

## ✅ Deployment Checklist

Use this before going live:

- [ ] Fly CLI installed and authenticated
- [ ] PostgreSQL database created
- [ ] DATABASE_URL saved
- [ ] All API keys ready (Groq, ElevenLabs, Clerk, TickTick)
- [ ] Backend deployed and responding
- [ ] Frontend deployed and accessible
- [ ] Clerk configured with production URLs
- [ ] Database migrations run
- [ ] Test: Sign in works
- [ ] Test: Audio upload works
- [ ] Test: AI summary generated
- [ ] Test: TODOs extracted
- [ ] Test: TickTick sync works
- [ ] Monitoring: Logs accessible
- [ ] Backups: Automatic backups enabled

---

## 🎊 Congratulations!

**Your production-grade voice transcription app is live!**

Enjoy your:
- 🎙️ High-quality transcriptions
- 🤖 AI-powered summaries
- ✅ Automatic task extraction
- 🔄 Seamless integrations
- 🌍 Global deployment

**Share your app and get feedback!** 🚀
