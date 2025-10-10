# 🎙️ Speech-to-Text Provider Options

Speakly supports multiple STT providers through a pluggable architecture, similar to the LLM provider system.

---

## 🎯 Available Providers

### 1. Groq Whisper (Recommended for most users)

**Best for:** Free tier users, fast transcription, general use

✅ **Pros:**
- **100% FREE** - Generous free tier
- **Fast** - Synchronous transcription (no webhook delays)
- **High quality** - Whisper-large-v3 model
- **Same API key as LLM** - Already configured if using Groq for summaries
- **No abuse detection issues** - Unlike ElevenLabs free tier

❌ **Cons:**
- **No speaker diarization** - Can't identify multiple speakers
- **Synchronous only** - Uses more server resources during processing

**Use when:**
- You're on a budget
- ElevenLabs is blocked or rate-limited
- Speaker diarization isn't critical
- You want simple, reliable transcription

---

### 2. ElevenLabs Scribe (Premium option)

**Best for:** Multi-speaker conversations, professional use

✅ **Pros:**
- **Speaker diarization** - Identifies who said what
- **High accuracy** - Premium speech recognition
- **Async processing** - Efficient for bulk uploads
- **Low latency** - Optimized for real-time transcription

❌ **Cons:**
- **Paid only** - Free tier often blocked by abuse detection
- **API key issues** - Requires separate key and can be restrictive
- **Webhook complexity** - Async callbacks add complexity

**Use when:**
- You need speaker identification
- Processing interviews or meetings
- Budget allows for paid API
- Already have paid ElevenLabs account

---

### 3. Mock (Development only)

**Best for:** Local development without API keys

✅ **Pros:**
- **No API keys needed** - Works offline
- **Instant** - Returns mock transcription immediately
- **Predictable** - Always returns same test data

❌ **Cons:**
- **Not real** - Returns hardcoded mock data
- **Dev only** - Auto-enabled when `SPEAKLY_DEVELOPER_MODE=true`

---

## ⚙️ Configuration

### Auto Mode (Recommended)

```bash
SPEAKLY_STT_PROVIDER=auto
```

**Behavior:**
1. If `GROQ_API_KEY` is set → Use Groq Whisper (free, fast)
2. Else if `ELEVENLABS_API_KEY` is set → Use ElevenLabs Scribe
3. Else if `SPEAKLY_DEVELOPER_MODE=true` → Use Mock
4. Otherwise → Error (no provider configured)

This is the recommended setting for most deployments.

---

### Manual Provider Selection

#### Force Groq Whisper

```bash
SPEAKLY_STT_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
```

#### Force ElevenLabs Scribe

```bash
SPEAKLY_STT_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=sk_your_key_here
ELEVENLABS_BASE_URL=https://api.elevenlabs.io
ELEVENLABS_WEBHOOK_SECRET=wsec_your_secret_here
ELEVENLABS_DIARIZATION_ENABLED=true
```

#### Developer Mode (Mock)

```bash
SPEAKLY_DEVELOPER_MODE=true
# STT provider automatically becomes 'mock'
```

---

## 🚀 Railway Deployment

### Using Groq (Recommended)

Set these environment variables in Railway:

```bash
# STT Configuration
SPEAKLY_STT_PROVIDER=groq  # or 'auto'
GROQ_API_KEY=gsk_your_groq_api_key

# LLM also uses same key
GROQ_MODEL=deepseek-r1-distill-llama-70b
```

**One key for both STT and LLM!** 🎉

### Using ElevenLabs

```bash
SPEAKLY_STT_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=sk_your_elevenlabs_key
ELEVENLABS_WEBHOOK_SECRET=wsec_your_secret
ELEVENLABS_DIARIZATION_ENABLED=true
```

**Important:** Make sure you have a paid ElevenLabs plan to avoid abuse detection issues.

---

## 📊 Comparison Matrix

| Feature | Groq Whisper | ElevenLabs | Mock |
|---------|--------------|------------|------|
| **Cost** | FREE | Paid | FREE |
| **Speed** | Fast (sync) | Medium (async) | Instant |
| **Quality** | High | High | N/A |
| **Diarization** | ❌ No | ✅ Yes | ✅ Yes (mock) |
| **Rate Limits** | Generous | Restrictive (free) | None |
| **API Key** | Groq | ElevenLabs | None |
| **Processing** | Synchronous | Asynchronous | Synchronous |
| **Best For** | General use | Meetings | Development |

---

## 🔧 Advanced Configuration

### Check Which Provider is Active

The backend logs will show which provider was selected on startup:

```
INFO: Using requested STT provider: groq
INFO: Auto-selected STT provider: groq
```

### Troubleshooting

#### "STT provider not configured"

**Solution:** Set at least one of:
- `GROQ_API_KEY` (for Groq Whisper)
- `ELEVENLABS_API_KEY` (for ElevenLabs)
- `SPEAKLY_DEVELOPER_MODE=true` (for Mock)

#### ElevenLabs "unusual activity detected"

**Solution:** Switch to Groq:
```bash
SPEAKLY_STT_PROVIDER=groq
GROQ_API_KEY=gsk_your_key
```

#### Groq rate limit exceeded

**Solution:** Switch to ElevenLabs (if you have a paid account):
```bash
SPEAKLY_STT_PROVIDER=elevenlabs
```

---

## 🎯 Recommendations

### For Personal Use / Testing
```bash
SPEAKLY_STT_PROVIDER=groq
GROQ_API_KEY=gsk_your_key
```
✅ Free, fast, reliable

### For Professional Use (Meetings/Interviews)
```bash
SPEAKLY_STT_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=sk_your_paid_key
ELEVENLABS_DIARIZATION_ENABLED=true
```
✅ Speaker identification, high quality

### For Development
```bash
SPEAKLY_DEVELOPER_MODE=true
```
✅ No API keys needed, instant mock responses

---

## 📝 Implementation Details

### Provider Architecture

The STT service uses a pluggable provider pattern similar to the LLM service:

```python
# All providers implement this interface
class SttProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is configured"""
    
    @abstractmethod
    def submit_transcription(...) -> dict:
        """Submit audio for transcription"""
    
    @abstractmethod
    def supports_diarization(self) -> bool:
        """Check if provider supports speaker identification"""
```

### Providers:
- `GroqSttProvider` - Uses Groq's Whisper API
- `ElevenLabsSttProvider` - Uses ElevenLabs Scribe API
- `MockSttProvider` - Returns hardcoded mock data

### Auto-Selection Logic:
1. Check requested provider (or 'auto')
2. Find all available providers (with API keys)
3. Select first available or requested provider
4. Fall back to mock if in developer mode

---

## 🔄 Migration Guide

### From ElevenLabs-only to Multi-Provider

**Before:**
```bash
ELEVENLABS_API_KEY=sk_your_key
ELEVENLABS_WEBHOOK_SECRET=wsec_secret
```

**After (using Groq):**
```bash
# Remove or keep ElevenLabs config as backup
SPEAKLY_STT_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_key
```

**No code changes required!** The provider abstraction handles everything.

---

## 💡 Tips

1. **Start with Groq** - Free and fast, perfect for getting started
2. **Upgrade to ElevenLabs** - Only if you need speaker diarization
3. **Keep both configured** - Easy to switch between providers
4. **Use auto mode** - Let the system choose the best available provider
5. **Monitor costs** - Groq free tier is generous, ElevenLabs charges per character

---

## 📚 Related Documentation

- [LLM Provider Configuration](./LLM_RATE_LIMITING.md)
- [Railway Deployment Guide](./VERCEL_RAILWAY_DEPLOYMENT.md)
- [Configuration Reference](../.env.example)

---

**Questions?** The STT provider system is designed to be simple and reliable. Start with Groq and switch providers as needed! 🚀
