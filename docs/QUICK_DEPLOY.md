# ⚡ Quick Deploy - TL;DR

**Get Speakly live in 20 minutes**

---

## 🚀 One-Time Setup

### 1. Push to GitHub
```bash
cd /Users/pj/dev/speakly
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/speakly.git
git push -u origin main
```

### 2. Deploy Backend (Railway)
1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo" → Select `speakly`
3. Railway auto-detects Python using `nixpacks.toml` (already in repo)
4. Add PostgreSQL: Click "+ New" → "Database" → "PostgreSQL"
5. Set environment variables (see below)
6. Wait for deployment (2-3 min)
7. Copy your backend URL: `https://YOUR-BACKEND.up.railway.app`

### 3. Deploy Frontend (Vercel)
1. Go to https://vercel.com/new
2. Import Git repo → Select `speakly`
3. Root directory: `frontend`
4. Add environment variables (see below)
5. Deploy
6. Copy your frontend URL: `https://YOUR-FRONTEND.vercel.app`

### 4. Update CORS
In Railway, update these variables:
```bash
SPEAKLY_CORS_ORIGINS=https://YOUR-FRONTEND.vercel.app,http://localhost:5173
SPEAKLY_FRONTEND_URL=https://YOUR-FRONTEND.vercel.app
```

### 5. Configure Clerk
At https://clerk.com:
- Set all URLs to: `https://YOUR-FRONTEND.vercel.app`
- Add to allowed origins: Your frontend + backend URLs

---

## 🔑 Environment Variables

### Railway (Backend)
```bash
SPEAKLY_ENVIRONMENT=prod
SPEAKLY_LOG_LEVEL=INFO
PORT=8000
DATABASE_URL=${{Postgres.DATABASE_URL}}
CLERK_SECRET_KEY=sk_test_***
ELEVENLABS_API_KEY=sk_***
ELEVENLABS_BASE_URL=https://api.elevenlabs.io
ELEVENLABS_WEBHOOK_SECRET=wsec_***
ELEVENLABS_DIARIZATION_ENABLED=true
GROQ_API_KEY=gsk_***
GROQ_MODEL=deepseek-r1-distill-llama-70b
SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=2
SPEAKLY_CORS_ORIGINS=http://localhost:5173
SPEAKLY_FRONTEND_URL=http://localhost:5173
SPEAKLY_AUDIO_DIR=/app/backend/storage/audio
SPEAKLY_DEVELOPER_MODE=false
```

### Vercel (Frontend)
```bash
VITE_CLERK_PUBLISHABLE_KEY=pk_test_***
VITE_API_BASE_URL=https://YOUR-BACKEND.up.railway.app
```

---

## 🔄 Future Updates

**Just push to Git - auto-deploys!**

```bash
git add .
git commit -m "Update"
git push
```

Both Railway and Vercel auto-deploy on push 🎉

---

## 📋 Checklist

- [ ] Code pushed to GitHub
- [ ] Railway backend deployed
- [ ] PostgreSQL database added
- [ ] Railway env vars set
- [ ] Vercel frontend deployed
- [ ] Vercel env vars set
- [ ] CORS updated in Railway
- [ ] Clerk configured
- [ ] Test: Sign in works
- [ ] Test: Audio upload works

---

## 📚 Full Guides

- **Complete Guide:** [VERCEL_RAILWAY_DEPLOYMENT.md](VERCEL_RAILWAY_DEPLOYMENT.md)
- **Checklist:** [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

---

## 💡 Pro Tips

1. **Test locally first:** `docker compose up`
2. **Use preview deployments:** Every PR gets its own URL
3. **Monitor logs:** Railway + Vercel dashboards
4. **Keep secrets safe:** Never commit `.env` files
5. **Start with test keys:** Use Clerk test keys first

---

## 🆘 Quick Fixes

**Backend won't start?**
→ Check Railway logs for missing env vars

**Frontend won't load?**
→ Check Vercel build logs

**CORS errors?**
→ Update `SPEAKLY_CORS_ORIGINS` in Railway

**Auth not working?**
→ Check Clerk allowed origins

---

**Need help?** See the full deployment guide!
