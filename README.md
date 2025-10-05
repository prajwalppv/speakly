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

**Deploy to Fly.io in 30 minutes:**

👉 **See [DEPLOY.md](DEPLOY.md) for complete step-by-step instructions**

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
- **Fly.io** - Global edge deployment
- **PostgreSQL** - Production database
- **Docker** - Containerization

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
- **Fly.io:** ~$12/month after free tier
- **ElevenLabs:** Pay-as-you-go

---

## 📚 Documentation

- **[DEPLOY.md](DEPLOY.md)** - Complete production deployment guide
- **[.env.example](.env.example)** - Environment configuration template

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

# Or use pytest directly
cd backend
pytest tests/ -v
```

---

## 🔄 Updating Your Deployment

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

**Production:**
```bash
# See complete guide
open DEPLOY.md
```

---

**Built with ❤️ using modern AI technologies**
