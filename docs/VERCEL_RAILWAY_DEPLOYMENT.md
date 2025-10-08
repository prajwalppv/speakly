# 🚀 Speakly - Vercel + Railway Deployment Guide

**Simple and fast deployment with Vercel (frontend) and Railway (backend + database)**

---

## 🎯 Why Vercel + Railway?

### Advantages over Fly.io:
- ✅ **Easier setup** - No CLI required, deploy via Git
- ✅ **Better free tier** - More generous limits for testing
- ✅ **Auto-deployments** - Push to Git = instant deployment
- ✅ **Railway database** - Managed PostgreSQL with zero config
- ✅ **Better DX** - Superior dashboard and logging interfaces
- ✅ **Vercel optimizations** - Best-in-class frontend performance

### What You Get:
- 🎨 **Vercel** - Lightning-fast frontend with global CDN
- 🔧 **Railway** - Auto-scaling backend with managed PostgreSQL
- 🔄 **Git sync** - Automatic deployments on push
- 📊 **Great dashboards** - Easy monitoring and logs
- 💰 **Generous free tier** - Perfect for getting started

---

## ⏱️ Estimated Time: 20-25 minutes

- **Pre-setup:** 5 min (accounts + keys)
- **Railway backend:** 10 min
- **Vercel frontend:** 5 min
- **Testing:** 5 min

---

## 📦 Prerequisites

### 1. GitHub Repository

Push your code to GitHub (if you haven't already):

```bash
cd /Users/pj/dev/speakly

# Initialize git if needed
git init
git add .
git commit -m "Initial commit"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/speakly.git
git push -u origin main
```

### 2. Create Accounts (Free)

- **Railway:** https://railway.app (Sign in with GitHub)
- **Vercel:** https://vercel.com (Sign in with GitHub)

---

## 🔑 Step 1: Gather Your API Keys (5 min)

You'll need these keys from your `.env` file:

### Required Keys:

```bash
# Groq (FREE - for AI summaries)
GROQ_API_KEY=gsk_********************************

# Clerk (Authentication)
CLERK_SECRET_KEY=sk_test_********************************
# For frontend:
VITE_CLERK_PUBLISHABLE_KEY=pk_test_********************************

# ElevenLabs (Speech-to-Text)
ELEVENLABS_API_KEY=sk_********************************
ELEVENLABS_WEBHOOK_SECRET=wsec_********************************

# TickTick (Optional - for task sync)
TICKTICK_CLIENT_ID=********************************
TICKTICK_CLIENT_SECRET=********************************
```

**Tip:** Keep these handy in a text file - you'll paste them into Railway/Vercel in the next steps.

---

## 🚂 Step 2: Deploy Backend on Railway (10 min)

### A. Create New Project

1. Go to: https://railway.app/new
2. Click **"Deploy from GitHub repo"**
3. Select your `speakly` repository
4. Railway will auto-detect it as a Python app using the `nixpacks.toml` config

**Note:** The repository includes Railway config files at the root:
- `nixpacks.toml` - Build configuration
- `Procfile` - Start command
- `railway.json` - Railway settings

### B. Add PostgreSQL Database

1. In your Railway project, click **"+ New"**
2. Select **"Database"** → **"PostgreSQL"**
3. Railway will automatically create a database and provide `DATABASE_URL`

### C. Configure Environment Variables

Click on your backend service → **"Variables"** tab → Add these:

```bash
# Core Settings
SPEAKLY_ENVIRONMENT=prod
SPEAKLY_LOG_LEVEL=INFO
PORT=8000

# Database (Railway auto-provides this, but verify it exists)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Clerk Auth
CLERK_SECRET_KEY=sk_test_********************************

# ElevenLabs STT
ELEVENLABS_API_KEY=sk_********************************
ELEVENLABS_BASE_URL=https://api.elevenlabs.io
ELEVENLABS_WEBHOOK_SECRET=wsec_********************************
ELEVENLABS_DIARIZATION_ENABLED=true

# Groq LLM
GROQ_API_KEY=gsk_********************************
GROQ_MODEL=deepseek-r1-distill-llama-70b

# LLM Rate Limiting
SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=2
SPEAKLY_LLM_RETRY_MAX_ATTEMPTS=5
SPEAKLY_LLM_RETRY_MIN_WAIT_SECONDS=2
SPEAKLY_LLM_RETRY_MAX_WAIT_SECONDS=60

# TickTick (Optional)
TICKTICK_CLIENT_ID=********************************
TICKTICK_CLIENT_SECRET=********************************
TICKTICK_REDIRECT_URI=https://speakly-backend.up.railway.app/api/ticktick/callback

# CORS (we'll update this after deploying frontend)
SPEAKLY_CORS_ORIGINS=http://localhost:5173
SPEAKLY_FRONTEND_URL=http://localhost:5173

# Storage
SPEAKLY_AUDIO_DIR=/app/backend/storage/audio

# Developer Mode
SPEAKLY_DEVELOPER_MODE=false
```

**Note:** Replace `********************************` with your actual keys!

### D. Verify Build Settings (Auto-configured)

Railway will automatically use the configuration files in your repo:

- **Build Command:** `pip install -r backend/requirements-dev.txt` (from `railway.json`)
- **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`

You shouldn't need to change these, but if needed:
1. Go to your backend service → **"Settings"** tab
2. Scroll to **"Deploy"** section
3. Verify the commands match above

### E. Deploy Backend

1. Click **"Deploy"** (Railway will build and deploy automatically)
2. Wait 2-3 minutes for deployment
3. Once deployed, Railway will show you a URL like:
   ```
   https://speakly-backend.up.railway.app
   ```

### F. Verify Backend

Test your backend:
```bash
curl https://YOUR-BACKEND-URL.up.railway.app/docs
```

You should see the FastAPI documentation page!

### G. Generate Domain (Optional but Recommended)

1. Go to your backend service → **"Settings"** → **"Networking"**
2. Click **"Generate Domain"**
3. Copy the generated URL (e.g., `speakly-backend-production.up.railway.app`)

---

## 🎨 Step 3: Deploy Frontend on Vercel (5 min)

### A. Import Project

1. Go to: https://vercel.com/new
2. Click **"Import Git Repository"**
3. Select your `speakly` repository
4. Vercel will auto-detect it as a Vite app

### B. Configure Project

**Framework Preset:** Vite
**Root Directory:** `frontend`
**Build Command:** `npm run build` (auto-detected)
**Output Directory:** `dist` (auto-detected)

### C. Add Environment Variables

Click **"Environment Variables"** and add:

```bash
# Clerk Public Key
VITE_CLERK_PUBLISHABLE_KEY=pk_test_********************************

# Backend API URL (use your Railway URL)
VITE_API_BASE_URL=https://YOUR-BACKEND-URL.up.railway.app
```

**Important:** Replace `YOUR-BACKEND-URL` with your actual Railway backend URL from Step 2!

### D. Deploy Frontend

1. Click **"Deploy"**
2. Wait 1-2 minutes for build and deployment
3. Vercel will show you a URL like:
   ```
   https://speakly-YOUR-PROJECT.vercel.app
   ```

### E. Verify Frontend

Visit your Vercel URL - you should see the Speakly login page!

---

## 🔄 Step 4: Update CORS Settings (2 min)

Now that both are deployed, update your backend CORS settings:

1. Go to Railway → Your backend service → **"Variables"**
2. Update these variables:

```bash
SPEAKLY_CORS_ORIGINS=https://YOUR-FRONTEND.vercel.app,http://localhost:5173
SPEAKLY_FRONTEND_URL=https://YOUR-FRONTEND.vercel.app
TICKTICK_REDIRECT_URI=https://YOUR-BACKEND.up.railway.app/api/ticktick/callback
```

3. Click **"Save"** - Railway will automatically redeploy

---

## ⚙️ Step 5: Configure Clerk (3 min)

Update Clerk settings to work with your production URLs:

1. Go to: https://clerk.com/dashboard
2. Select your application
3. Navigate to **"Paths"**
4. Update URLs:
   ```
   Home URL: https://YOUR-FRONTEND.vercel.app
   Sign in URL: https://YOUR-FRONTEND.vercel.app
   Sign up URL: https://YOUR-FRONTEND.vercel.app
   After sign in: https://YOUR-FRONTEND.vercel.app
   After sign up: https://YOUR-FRONTEND.vercel.app
   ```

5. Navigate to **"API Keys"** → **"CORS"**
6. Add allowed origins:
   ```
   https://YOUR-FRONTEND.vercel.app
   https://YOUR-BACKEND.up.railway.app
   ```

7. Click **"Save Changes"**

---

## ✅ Step 6: Test Your Deployment! (5 min)

### 1. Visit Your App

Go to: `https://YOUR-FRONTEND.vercel.app`

### 2. Test Authentication

- Click **"Sign In"**
- Sign in with Google/Apple/Email
- Should redirect back successfully

### 3. Test Audio Upload

1. Upload an audio file
2. Wait for transcription (~10-30 seconds)
3. Verify:
   - ✅ Transcription appears
   - ✅ AI Summary generated (DeepSeek R1!)
   - ✅ Tags auto-created
   - ✅ TODOs extracted

### 4. Check Sessions Dashboard

- Navigate to **"📚 Sessions"**
- Verify your uploaded sessions appear
- Test collapsible cards and filters

---

## 📊 Step 7: Monitoring & Logs

### Railway Dashboard

View backend logs:
1. Go to: https://railway.app
2. Select your project → backend service
3. Click **"Deployments"** tab → View logs

### Vercel Dashboard

View frontend logs:
1. Go to: https://vercel.com/dashboard
2. Select your project
3. Click on a deployment → **"Logs"** tab

### Database Access

Access PostgreSQL:
1. Railway → Your PostgreSQL service
2. Click **"Data"** tab to browse tables
3. Or use **"Connect"** tab to get connection details for local access

---

## 🎉 You're Live!

### Your Production URLs:

- **Frontend:** https://YOUR-FRONTEND.vercel.app
- **Backend:** https://YOUR-BACKEND.up.railway.app
- **API Docs:** https://YOUR-BACKEND.up.railway.app/docs

### What You Have Running:

- ✅ Voice transcription (ElevenLabs Scribe)
- ✅ AI summaries (DeepSeek R1 70B via Groq)
- ✅ Auto-tagging & TODO extraction
- ✅ TickTick integration
- ✅ Multi-user auth (Clerk)
- ✅ PostgreSQL database
- ✅ Global CDN (Vercel)
- ✅ Auto-scaling backend (Railway)
- ✅ HTTPS/SSL everywhere
- ✅ Git-based deployments

---

## 🔄 Future Updates

### Update Backend

Just push to Git:
```bash
git add .
git commit -m "Update backend"
git push
```

Railway will automatically deploy! 🎉

### Update Frontend

Same thing:
```bash
git add .
git commit -m "Update frontend"
git push
```

Vercel will automatically deploy! 🎉

### Update Environment Variables

**Railway:**
1. Go to your service → **"Variables"**
2. Update values
3. Click **"Save"** (auto-redeploys)

**Vercel:**
1. Go to your project → **"Settings"** → **"Environment Variables"**
2. Update values
3. Trigger a redeploy from **"Deployments"** tab

---

## 🛠️ Troubleshooting

### Backend Won't Start

**Check Railway logs:**
1. Railway → Your backend → **"Deployments"** → Click latest deployment
2. Look for errors in the build/deploy logs

**Common issues:**
- Missing environment variables → Check **"Variables"** tab
- Database connection failed → Verify `DATABASE_URL` is set
- Wrong start command → Check in **"Settings"** → **"Deploy"**

### Frontend Build Fails

**Check Vercel logs:**
1. Vercel → Your project → Latest deployment → **"Building"** tab

**Common issues:**
- Missing `VITE_*` env vars → Add in **"Settings"** → **"Environment Variables"**
- Wrong root directory → Should be `frontend`
- Build command failed → Check `package.json` scripts

### CORS Errors

**Symptoms:** Frontend can't connect to backend

**Fix:**
1. Check `SPEAKLY_CORS_ORIGINS` includes your Vercel URL
2. Verify Clerk allowed origins includes both frontend and backend URLs
3. Make sure `VITE_API_BASE_URL` points to correct Railway URL

### Database Connection Issues

**Test connection:**
1. Railway → PostgreSQL service → **"Connect"** tab
2. Copy connection string
3. Test locally:
   ```bash
   psql "YOUR_DATABASE_URL"
   ```

### Authentication Not Working

**Check Clerk configuration:**
1. Verify `CLERK_SECRET_KEY` in Railway matches your Clerk dashboard
2. Verify `VITE_CLERK_PUBLISHABLE_KEY` in Vercel matches
3. Check Clerk allowed origins and redirect URLs

---

## 💰 Costs

### Free Tier Includes:

**Railway:**
- $5 credit per month (no credit card required for trial)
- After trial: ~$5-10/month for small apps

**Vercel:**
- 100 GB bandwidth/month
- Unlimited static deployments
- Serverless function executions
- Free for hobby projects!

### Estimated Monthly Cost:

- **Railway Backend + DB:** ~$5-10/month
- **Vercel Frontend:** FREE (hobby tier)
- **Groq LLM:** FREE (generous rate limits)
- **ElevenLabs:** Pay-as-you-go (based on usage)
- **Total:** ~$5-15/month

**Much cheaper than Fly.io for small projects!**

---

## 🚀 Advanced Features

### Custom Domain (Vercel)

1. Vercel → Your project → **"Settings"** → **"Domains"**
2. Add your domain (e.g., `speakly.com`)
3. Update DNS records as shown
4. Vercel auto-provisions SSL certificate

### Custom Domain (Railway)

1. Railway → Your backend → **"Settings"** → **"Networking"**
2. Click **"Custom Domain"**
3. Add domain (e.g., `api.speakly.com`)
4. Update DNS records

### Environment-Specific Deployments

**Preview Branches (Vercel):**
- Push to any branch → Vercel creates preview deployment
- Perfect for testing before merging to main

**Railway Environments:**
1. Railway → Your project → **"+ New Environment"**
2. Create `staging` environment
3. Configure with different variables

### Database Backups (Railway)

Railway provides automatic backups, but you can also:
1. PostgreSQL service → **"Data"** tab
2. Export database as SQL dump
3. Or use `pg_dump` with connection string

---

## 📝 Quick Reference

### Railway Commands (Optional CLI)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link project
railway link

# View logs
railway logs

# Run command in production
railway run <command>
```

### Vercel Commands (Optional CLI)

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Link project
vercel link

# View logs
vercel logs

# Deploy manually
vercel --prod
```

---

## 🎯 Next Steps

### 1. Set Up Monitoring

**Railway:**
- Built-in metrics in dashboard
- Consider adding Sentry for error tracking

**Vercel:**
- Built-in Web Analytics (enable in settings)
- Consider Vercel Speed Insights

### 2. Optimize Performance

**Backend:**
- Enable Railway's edge locations
- Add Redis for caching (Railway Marketplace)

**Frontend:**
- Enable Vercel's Edge Network (default)
- Add Vercel Analytics for performance monitoring

### 3. Set Up CI/CD

**GitHub Actions:**
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run backend tests
        run: |
          cd backend
          pip install -r requirements-dev.txt
          pytest
```

### 4. Configure Alerts

**Railway:**
1. Project → **"Settings"** → **"Notifications"**
2. Enable deployment notifications
3. Connect Slack/Discord webhook

**Vercel:**
1. Project → **"Settings"** → **"Notifications"**
2. Enable deployment and error notifications

---

## ✅ Deployment Checklist

- [ ] GitHub repository created and pushed
- [ ] Railway account created
- [ ] Vercel account created
- [ ] All API keys gathered
- [ ] Railway PostgreSQL database created
- [ ] Backend deployed on Railway
- [ ] Backend environment variables configured
- [ ] Backend URL accessible
- [ ] Frontend deployed on Vercel
- [ ] Frontend environment variables configured
- [ ] Frontend URL accessible
- [ ] CORS settings updated in backend
- [ ] Clerk configured with production URLs
- [ ] Test: Sign in works
- [ ] Test: Audio upload and transcription works
- [ ] Test: AI summary generated
- [ ] Test: TODOs and tags created
- [ ] Monitoring dashboards accessible

---

## 📞 Support Resources

### Railway:
- Docs: https://docs.railway.app
- Discord: https://discord.gg/railway
- Status: https://status.railway.app

### Vercel:
- Docs: https://vercel.com/docs
- Community: https://github.com/vercel/vercel/discussions
- Status: https://vercel-status.com

### Groq:
- Console: https://console.groq.com
- Docs: https://console.groq.com/docs

### Clerk:
- Docs: https://clerk.com/docs
- Support: https://clerk.com/support

---

## 🎊 Congratulations!

**You've successfully deployed Speakly with modern, developer-friendly tools!**

Enjoy:
- 🚀 Automatic Git-based deployments
- 📊 Beautiful monitoring dashboards
- 💰 Generous free tiers
- ⚡ Lightning-fast performance
- 🔄 Zero-downtime updates

**Share your app and start transcribing!** 🎙️

---

## 💡 Pro Tips

1. **Use Preview Deployments:** Every PR gets its own URL on Vercel
2. **Monitor Logs Regularly:** Catch issues early
3. **Set Up Alerts:** Get notified of deployment failures
4. **Database Backups:** Download periodic backups of your Railway DB
5. **Environment Variables:** Never commit secrets - always use Railway/Vercel env vars
6. **Custom Domains:** Makes your app look professional
7. **Edge Functions:** Consider Vercel Edge Functions for low-latency API calls

---

**Need help?** Check the troubleshooting section or reach out to the communities! 🤝
