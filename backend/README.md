# 🎙️ Speakly Backend

**Privacy-first voice transcription app with AI-powered summaries and task extraction.**

[![Tests](https://img.shields.io/badge/tests-499%20passing-success)]()
[![Coverage](https://img.shields.io/badge/coverage-74.65%25-success)]()
[![Python](https://img.shields.io/badge/python-3.11-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688)]()

---

## ✨ Features

- 🎤 **Audio Transcription** - ElevenLabs Scribe STT integration
- 🤖 **AI Summaries** - Automatic meeting summaries with Ollama
- ✅ **Task Extraction** - Auto-detect todos with context
- 🔄 **TickTick Sync** - Automatic task synchronization
- 👥 **Speaker Diarization** - Identify multiple speakers
- 📦 **Bulk Upload** - Process multiple files in timestamp order
- 🔐 **Privacy-First** - Audio files deleted after transcription
- 🧪 **Well-Tested** - 499 tests, 74.65% coverage

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (for production)
- ElevenLabs API key
- ffmpeg (required for Groq STT chunking of large audio files)
- Ollama (for AI features)

### Local Development

```bash
# 1. Install dependencies
pip install -r requirements-dev.txt

# 2. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run database migrations
alembic upgrade head

# 4. Start server
uvicorn app.main:app --reload --port 8000

# 5. Run tests
pytest tests/

# 6. Check coverage
pytest tests/ --cov=app --cov-report=html
```

### Docker Development

```bash
# Build and run with Docker Compose
docker compose up --build backend frontend

# Run tests
docker compose run --rm backend-tests
```

---

## 📦 Deployment

### Railway (Recommended)

```bash
# 1. Install Railway CLI
npm install -g @railway/cli
railway login

# 2. Initialize and deploy
railway init
railway add postgresql
railway up

# 3. Set environment variables
railway variables set ELEVENLABS_API_KEY=your_key
railway variables set SPEAKLY_DEVELOPER_MODE=false

# 4. Run migrations
railway run alembic upgrade head
```

See [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) for complete deployment guide.

---

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
│  (React)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌──────────────┐
│   FastAPI   │─────▶│  PostgreSQL  │
│   Backend   │      │   Database   │
└──────┬──────┘      └──────────────┘
       │
       ├─────────────▶ ElevenLabs STT
       ├─────────────▶ Ollama LLM
       └─────────────▶ TickTick API
```

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── routers/          # API endpoints
│   ├── services/         # Business logic
│   ├── integrations/     # External integrations
│   ├── models.py         # Database models
│   ├── schemas.py        # Pydantic schemas
│   ├── config.py         # Configuration
│   └── main.py           # FastAPI app
├── tests/                # Test suite (499 tests)
├── alembic/              # Database migrations
├── Dockerfile            # Container configuration
└── requirements.txt      # Dependencies
```

---

## 🔧 Configuration

### Environment Variables

See [`.env.example`](.env.example) for all configuration options.

**Required:**
- `DATABASE_URL` - PostgreSQL connection string
- `ELEVENLABS_API_KEY` - ElevenLabs API key

**Optional:**
- `OLLAMA_BASE_URL` - Ollama server URL
- `TICKTICK_CLIENT_ID` - TickTick OAuth credentials
- `SPEAKLY_DEVELOPER_MODE` - Enable mock responses

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_audio_router.py

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run integration tests only
pytest tests/ -k "integration"

# Run unit tests only
pytest tests/ -k "not integration"
```

**Test Coverage:**
- ✅ Router endpoints: 50-68%
- ✅ Services: 76-100%
- ✅ Business logic: 74.65%
- ✅ Critical paths: All covered

---

## 📊 API Documentation

Once running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

```
POST   /api/audio              # Upload single audio file
POST   /api/audio/bulk         # Upload multiple files
GET    /api/sessions           # List all sessions
GET    /api/sessions/{id}      # Get session details
GET    /api/todos              # List todos
POST   /api/ticktick/auth      # Start TickTick OAuth
```

---

## 🔐 Security

- ✅ Audio files auto-deleted after transcription
- ✅ Webhook signature validation (HMAC-SHA256)
- ✅ Environment-based configuration
- ✅ CORS configuration
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ Input validation (Pydantic)

---

## 🎯 Performance

- **API Response**: < 200ms
- **File Upload**: Streaming multipart
- **Database**: Connection pooling
- **Async Processing**: Background tasks for LLM
- **Timestamp Ordering**: Maintains task context

---

## 📝 Database

### Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Models

- **User** - User accounts
- **Session** - Recording sessions
- **Transcription** - Transcribed text
- **Todo** - Extracted tasks
- **LlmRun** - AI processing runs
- **SpeakerSegment** - Diarization data
- **TickTickToken** - OAuth tokens

---

## 🤝 Contributing

1. Run tests: `pytest tests/`
2. Check coverage: `pytest --cov=app`
3. Follow PEP 8 style guide
4. Add type hints
5. Update tests for new features

---

## 📄 License

Proprietary - All rights reserved

---

## 🆘 Support

- **Documentation**: See [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)
- **Issues**: Check logs in `logs/` directory
- **API Docs**: Visit `/docs` endpoint

---

## 🎉 Production Ready!

✅ 499 passing tests  
✅ 74.65% code coverage  
✅ Privacy-first architecture  
✅ Scalable deployment  
✅ Comprehensive error handling  
✅ Beautiful UI  

**Deploy with confidence! 🚀**
