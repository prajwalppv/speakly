# ✅ Speakly Deployment Checklist

**Use this checklist when deploying to Vercel + Railway**

---

## 🎯 Pre-Deployment

### Accounts & Access
- [ ] GitHub account created
- [ ] Code pushed to GitHub repository
- [ ] Railway account created (sign in with GitHub)
- [ ] Vercel account created (sign in with GitHub)

### API Keys Ready
- [ ] Groq API key (from console.groq.com)
- [ ] Clerk Secret Key (from clerk.com)
- [ ] Clerk Publishable Key (from clerk.com)
- [ ] ElevenLabs API Key (from elevenlabs.io)
- [ ] ElevenLabs Webhook Secret (from elevenlabs.io)
- [ ] TickTick Client ID (optional)
- [ ] TickTick Client Secret (optional)

---

## 🚂 Railway Backend Deployment

### Project Setup
- [ ] New Railway project created
- [ ] GitHub repository linked
- [ ] Auto-deployment enabled

### Database
- [ ] PostgreSQL database added to project
- [ ] DATABASE_URL automatically provided
- [ ] Database connection verified

### Environment Variables Set
- [ ] SPEAKLY_ENVIRONMENT=prod
- [ ] SPEAKLY_LOG_LEVEL=INFO
- [ ] PORT=8000
- [ ] DATABASE_URL (auto-provided)
- [ ] CLERK_SECRET_KEY
- [ ] ELEVENLABS_API_KEY
- [ ] ELEVENLABS_BASE_URL=https://api.elevenlabs.io
- [ ] ELEVENLABS_WEBHOOK_SECRET
- [ ] ELEVENLABS_DIARIZATION_ENABLED=true
- [ ] GROQ_API_KEY
- [ ] GROQ_MODEL=deepseek-r1-distill-llama-70b
- [ ] SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=2
- [ ] SPEAKLY_LLM_RETRY_MAX_ATTEMPTS=5
- [ ] SPEAKLY_LLM_RETRY_MIN_WAIT_SECONDS=2
- [ ] SPEAKLY_LLM_RETRY_MAX_WAIT_SECONDS=60
- [ ] TICKTICK_CLIENT_ID (if using)
- [ ] TICKTICK_CLIENT_SECRET (if using)
- [ ] TICKTICK_REDIRECT_URI (update after deploy)
- [ ] SPEAKLY_CORS_ORIGINS (update after frontend deploy)
- [ ] SPEAKLY_FRONTEND_URL (update after frontend deploy)
- [ ] SPEAKLY_AUDIO_DIR=/app/backend/storage/audio
- [ ] SPEAKLY_DEVELOPER_MODE=false

### Build Configuration
- [ ] Root directory verified (empty or `/`)
- [ ] Build command: `pip install -r backend/requirements-dev.txt`
- [ ] Start command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`

### Deployment
- [ ] Backend deployed successfully
- [ ] Deployment logs checked (no errors)
- [ ] Backend URL noted down
- [ ] API docs accessible (https://YOUR-BACKEND.up.railway.app/docs)

---

## 🎨 Vercel Frontend Deployment

### Project Setup
- [ ] New Vercel project created
- [ ] GitHub repository linked
- [ ] Auto-deployment enabled

### Configuration
- [ ] Framework preset: Vite
- [ ] Root directory: `frontend`
- [ ] Build command: `npm run build`
- [ ] Output directory: `dist`

### Environment Variables Set
- [ ] VITE_CLERK_PUBLISHABLE_KEY
- [ ] VITE_API_BASE_URL (Railway backend URL)

### Deployment
- [ ] Frontend deployed successfully
- [ ] Deployment logs checked (no errors)
- [ ] Frontend URL noted down
- [ ] Application loads in browser

---

## 🔧 Post-Deployment Configuration

### Update Railway Backend
- [ ] SPEAKLY_CORS_ORIGINS updated with Vercel URL
- [ ] SPEAKLY_FRONTEND_URL updated with Vercel URL
- [ ] TICKTICK_REDIRECT_URI updated with Railway URL
- [ ] Backend redeployed with new variables

### Configure Clerk
- [ ] Home URL set to Vercel URL
- [ ] Sign in URL set to Vercel URL
- [ ] Sign up URL set to Vercel URL
- [ ] After sign in URL set to Vercel URL
- [ ] After sign up URL set to Vercel URL
- [ ] Allowed origins include Vercel URL
- [ ] Allowed origins include Railway URL

### ElevenLabs Webhook (if using)
- [ ] Webhook URL set to: `https://YOUR-BACKEND.up.railway.app/api/webhooks/elevenlabs`
- [ ] Webhook secret matches ELEVENLABS_WEBHOOK_SECRET
- [ ] Webhook tested and working

---

## ✅ Testing

### Authentication
- [ ] Sign in with email works
- [ ] Sign in with Google works (if configured)
- [ ] Sign out works
- [ ] User session persists on refresh

### Core Features
- [ ] Audio file upload works
- [ ] Transcription completes successfully
- [ ] AI summary generated
- [ ] Tags auto-created
- [ ] TODOs extracted
- [ ] Session appears in dashboard

### Bulk Upload
- [ ] Multiple files can be uploaded
- [ ] All files process successfully
- [ ] Progress indicators work
- [ ] Rate limiting prevents throttling

### TickTick Integration (if enabled)
- [ ] TickTick authorization flow works
- [ ] Tasks sync to TickTick
- [ ] Task status updates correctly

---

## 📊 Monitoring

### Railway Dashboard
- [ ] Backend deployment successful
- [ ] Logs accessible and readable
- [ ] No error spikes in logs
- [ ] Database connected and healthy
- [ ] Resource usage within limits

### Vercel Dashboard
- [ ] Frontend deployment successful
- [ ] Build logs clean (no errors)
- [ ] Analytics enabled (optional)
- [ ] Performance metrics good

### Application Health
- [ ] API responds quickly (<1s)
- [ ] Frontend loads fast (<2s)
- [ ] No console errors in browser
- [ ] All features working as expected

---

## 🔐 Security

### Secrets Management
- [ ] No secrets committed to Git
- [ ] All secrets stored in Railway/Vercel env vars
- [ ] API keys rotated if accidentally exposed
- [ ] Database credentials secure

### CORS & Auth
- [ ] CORS only allows your domains
- [ ] Clerk authentication working
- [ ] API endpoints protected
- [ ] No public access to sensitive data

---

## 📝 Documentation

### URLs Documented
- [ ] Frontend URL saved
- [ ] Backend URL saved
- [ ] Database connection string saved (securely)
- [ ] API docs URL bookmarked

### Access Credentials
- [ ] Railway project access confirmed
- [ ] Vercel project access confirmed
- [ ] All team members invited (if applicable)

---

## 🎉 Final Steps

### Share & Test
- [ ] Share app URL with test users
- [ ] Gather initial feedback
- [ ] Monitor for any issues
- [ ] Fix bugs as they arise

### Optional Enhancements
- [ ] Custom domain configured (Vercel)
- [ ] Custom domain configured (Railway)
- [ ] Error tracking added (Sentry)
- [ ] Analytics configured
- [ ] Monitoring alerts set up

---

## 🚨 Troubleshooting Reference

### If backend won't start:
1. Check Railway logs for errors
2. Verify all environment variables set
3. Confirm DATABASE_URL is correct
4. Check build command succeeded

### If frontend won't load:
1. Check Vercel build logs
2. Verify VITE_* env vars are set
3. Confirm build command succeeded
4. Check browser console for errors

### If API calls fail:
1. Verify VITE_API_BASE_URL is correct
2. Check CORS settings in backend
3. Confirm backend is running
4. Check network tab in browser devtools

### If authentication fails:
1. Verify Clerk keys match
2. Check Clerk dashboard settings
3. Confirm allowed origins include both URLs
4. Test in incognito mode

---

## 📞 Support Resources

- **Railway Docs:** https://docs.railway.app
- **Vercel Docs:** https://vercel.com/docs
- **Deployment Guide:** [VERCEL_RAILWAY_DEPLOYMENT.md](VERCEL_RAILWAY_DEPLOYMENT.md)

---

**Deployment Complete!** 🎊

Remember:
- Push to Git = Auto-deploy
- Check logs regularly
- Monitor costs
- Keep API keys secure

---

*Last updated: 2025-10-07*
