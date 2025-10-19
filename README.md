# 🎙️ Speakly

**AI-powered voice transcription with automatic summaries, tags, and task extraction.**

---

## 🚀 Features

- 🎙️ **Voice Transcription** - ElevenLabs Scribe STT
- 🤖 **AI Summaries** - DeepSeek R1 Distill (70B) via Groq
- 🏷️ **Auto-tagging** - Smart content categorization
- ✅ **TODO Extraction** - Automatic task identification
- 🔄 **TickTick Integration** - Sync tasks automatically
- 👥 **Multi-user** - Secure Clerk authentication
- 📦 **Bulk Upload** - Process up to 50 files at once
- 📊 **Sessions Dashboard** - Beautiful UI with collapsible cards

---

## 📦 Quick Start

### Local Development

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Add your API keys to .env

# 3. Start the app
docker compose up --build backend frontend
```

Visit: http://localhost:5173

---

## 🚀 Production Deployment

### Recommended: Vercel + Railway (Easiest!)

**Deploy in 20 minutes with zero CLI setup:**

👉 **See [docs/VERCEL_RAILWAY_DEPLOYMENT.md](docs/VERCEL_RAILWAY_DEPLOYMENT.md)**

- ✅ Git-based deployments (push = deploy)
- ✅ Better free tier
- ✅ Superior dashboards and DX
- ✅ Managed PostgreSQL included

### Alternative: Fly.io

**Deploy to Fly.io in 30 minutes:**

👉 **See [DEPLOY.md](DEPLOY.md)**

- More control and flexibility
- CLI-based workflow

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM with PostgreSQL
- **ElevenLabs** - Voice transcription
- **Groq** - LLM inference (DeepSeek R1 Distill 70B)
- **Clerk** - Authentication
- **TickTick** - Task management integration

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Axios** - HTTP client

### Infrastructure
- **Vercel** - Frontend hosting with global CDN (recommended)
- **Railway** - Backend + PostgreSQL (recommended)
- **Fly.io** - Alternative deployment option
- **Docker** - Local development & containerization

### Continuous Integration
- **Backend CI** – Runs the FastAPI test suite on every push/PR
- **Frontend CI** – Builds the React app to ensure production assets compile cleanly

---

## 📁 Project Structure

```
speakly/
├── backend/
│   ├── app/
│   │   ├── routers/        # API endpoints
│   │   ├── services/       # Business logic (LLM, ElevenLabs)
│   │   ├── integrations/   # External integrations (TickTick)
│   │   ├── models.py       # Database models
│   │   └── config.py       # Configuration
│   └── tests/              # Test suite
│
├── frontend/
│   └── src/
│       ├── components/     # React components
│       └── api.ts          # API client
│
├── .env.example            # Environment template
├── DEPLOY.md               # 🚀 Deployment guide
└── docker-compose.yml      # Local development
```

---

## 🔑 Environment Variables

See [.env.example](.env.example) for all required variables.

**Required:**
- `GROQ_API_KEY` - Get from https://console.groq.com (FREE!)
- `CLERK_SECRET_KEY` - Get from https://clerk.com
- `ELEVENLABS_API_KEY` - Get from https://elevenlabs.io

**Optional:**
- `TICKTICK_CLIENT_ID` - For TickTick integration
- `OLLAMA_BASE_URL` - For local LLM development

---

## 💰 Cost Estimate

**FREE for development & small production:**
- **Groq:** FREE (14.4k requests/day)
- **Clerk:** FREE (10k users)
- **Vercel:** FREE (hobby tier)
- **Railway:** $5 free credit/month, then ~$5-10/month
- **Alternative (Fly.io):** ~$12/month after free tier
- **ElevenLabs:** Pay-as-you-go

**Total: ~$5-15/month with Vercel + Railway** (much cheaper than Fly.io!)

---

## 📚 Documentation

- **[docs/VERCEL_RAILWAY_DEPLOYMENT.md](docs/VERCEL_RAILWAY_DEPLOYMENT.md)** - 🌟 Recommended deployment guide (Vercel + Railway)
- **[DEPLOY.md](DEPLOY.md)** - Alternative deployment guide (Fly.io)
- **[.env.example](.env.example)** - Environment configuration template
- **[docs/ARCHITECTURE_REFACTOR.md](docs/ARCHITECTURE_REFACTOR.md)** - Architecture overview
- **[docs/BULK_UPLOAD_FEATURE.md](docs/BULK_UPLOAD_FEATURE.md)** - Bulk upload implementation details

---

## 🎯 What Makes Speakly Different

### AI Quality
- **DeepSeek R1 Distill 70B** - State-of-the-art reasoning model
- **Chain-of-thought** processing for better understanding
- **Context-aware** summaries and task extraction

### User Experience
- **Bulk upload** - Process many files at once
- **Real-time progress** - See processing status
- **Beautiful UI** - Modern, responsive design
- **Auto-refresh** - Sessions update automatically

### Integration-Ready
- **TickTick sync** - Tasks automatically added
- **Webhook support** - ElevenLabs async processing
- **OAuth flows** - Secure third-party connections

---

## 🧪 Testing

```bash
# Backend tests
docker compose run --rm --profile test backend-tests

# Or run locally with uv (after `uv sync --extra dev`)
cd backend
uv run pytest tests/ -v
```

## ✅ Pre-commit Hooks

- Install tooling once: install [uv](https://docs.astral.sh/uv/getting-started/install/) then run `uv sync --extra dev` inside `backend/`; run `npm install` inside `frontend/`.
- Register the git hooks: `uv run pre-commit install` and `uv run pre-commit install --hook-type pre-push`.
- Run `uv run pre-commit run --all-files` before opening a PR to bootstrap the hook environments.
- On commit the hooks format Python (isort + Black) and frontend assets (Prettier), upgrade syntax, and type-check the React code while Ruff handles linting; mypy runs to catch type issues with auto-installed stubs.
- Prettier runs via `npx`, so the first commit may download its toolchain (cached afterward).
- On push the backend test suite executes via `pytest` to catch regressions before CI.

---

## 🔄 Updating Your Deployment

### Vercel + Railway (Git-based)

```bash
# Just push to Git!
git add .
git commit -m "Update app"
git push

# Both Railway and Vercel auto-deploy 🎉
```

### Fly.io (CLI-based)

```bash
# Update backend
flyctl deploy --app speakly-backend

# Update frontend
cd frontend
flyctl deploy --app speakly-frontend \
  --build-arg VITE_CLERK_PUBLISHABLE_KEY="..." \
  --build-arg VITE_API_BASE_URL="https://speakly-backend.fly.dev"
```

---

## 🎉 Get Started

**Local:**
```bash
docker compose up
```

**Production (Recommended):**
```bash
# See Vercel + Railway guide
open docs/VERCEL_RAILWAY_DEPLOYMENT.md
```

**Production (Alternative):**
```bash
# See Fly.io guide
open DEPLOY.md
```

---

**Built with ❤️ using modern AI technologies**
