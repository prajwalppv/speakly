# Rate Limiting Setup Guide

## Quick Start

The rate limiting and retry mechanisms are now **enabled by default** with sensible defaults. No configuration required for basic usage.

## Environment Variables (Optional)

Add these to your `.env` file to customize behavior:

```bash
# Maximum concurrent LLM sessions (default: 3)
# Lower this if you're on a free tier or experiencing rate limits
SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=3

# Retry attempts for failed requests (default: 5)
SPEAKLY_LLM_RETRY_MAX_ATTEMPTS=5

# Min/max wait time between retries in seconds
SPEAKLY_LLM_RETRY_MIN_WAIT_SECONDS=1
SPEAKLY_LLM_RETRY_MAX_WAIT_SECONDS=60
```

## For Production Deployment

### Fly.io Secrets

Set these secrets for your production environment:

```bash
# Set based on your API tier
fly secrets set SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=3

# Optional: adjust retry behavior
fly secrets set SPEAKLY_LLM_RETRY_MAX_ATTEMPTS=5
fly secrets set SPEAKLY_LLM_RETRY_MIN_WAIT_SECONDS=1
fly secrets set SPEAKLY_LLM_RETRY_MAX_WAIT_SECONDS=60
```

### Recommended Settings by API Tier

**Groq Free Tier:**
```bash
SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=2
SPEAKLY_LLM_RETRY_MAX_ATTEMPTS=5
```

**Groq Pro Tier:**
```bash
SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=5
SPEAKLY_LLM_RETRY_MAX_ATTEMPTS=3
```

**Groq Enterprise:**
```bash
SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=10
SPEAKLY_LLM_RETRY_MAX_ATTEMPTS=3
```

## How It Works

### During Bulk Uploads

When you upload 5 audio files:

1. **All 5 files** are accepted and saved immediately
2. **Only 3 files** (default) process LLM operations simultaneously
3. **Files 4-5** wait in queue for an available slot
4. **If rate limits hit**, requests automatically retry with exponential backoff
5. **All files** eventually complete successfully

### Monitoring

Watch your logs for these indicators:

```bash
# Good - normal operation
INFO: Acquired LLM semaphore for session 123
INFO: Released LLM semaphore for session 123

# Warning - hitting rate limits but recovering
WARNING: Groq API rate limit hit (429). Retry-After: 5
WARNING: Retrying in 1.0 seconds

# Error - all retries exhausted (may need to lower concurrency)
ERROR: Groq API request failed after 5 attempts
```

## Troubleshooting

### Still Getting Rate Limited?

1. **Reduce concurrency:**
   ```bash
   SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=1
   ```

2. **Increase retry wait times:**
   ```bash
   SPEAKLY_LLM_RETRY_MIN_WAIT_SECONDS=2
   SPEAKLY_LLM_RETRY_MAX_WAIT_SECONDS=120
   ```

3. **Check your API limits:** Verify your Groq API tier and adjust accordingly

### Testing Locally

```bash
# Test with minimal concurrency
SPEAKLY_DEVELOPER_MODE=true \
SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=1 \
uv run uvicorn app.main:app --reload
```

## Installation

Dependencies are already included in `pyproject.toml`:

```bash
uv sync --extra dev
```

The key dependency is:
- **tenacity** (>=8.0,<9.0): Provides retry logic with exponential backoff

## Testing

Run the rate limiting tests:

```bash
# Run all rate limiting tests
uv run pytest tests/test_llm_rate_limiting.py -v

# Run specific test
uv run pytest tests/test_llm_rate_limiting.py::TestGroqProviderRetry::test_retry_on_429_rate_limit -v
```

All 11 tests should pass, covering:
- ✅ Retry on 429 rate limit errors
- ✅ Retry on 5xx server errors
- ✅ Retry on timeout/network errors
- ✅ No retry on auth errors (401)
- ✅ Semaphore-based concurrency limiting
- ✅ Integration with bulk uploads
- ✅ Configuration validation

## Further Reading

For detailed technical documentation, see:
- **[LLM_RATE_LIMITING.md](./LLM_RATE_LIMITING.md)** - Complete technical guide
- **Architecture diagrams** and error handling details
- **Best practices** for different deployment scenarios
