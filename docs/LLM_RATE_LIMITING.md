# LLM Rate Limiting and Retry Mechanisms

## Overview

This document describes the rate limiting and retry mechanisms implemented to prevent API throttling issues when processing multiple audio files simultaneously.

## Problem

When uploading multiple audio files in bulk (e.g., 5 files), all files trigger transcription webhooks simultaneously. Each webhook then triggers multiple LLM operations (title generation, summary, TODO extraction), resulting in 15+ concurrent API calls to Groq. This quickly exceeds rate limits and causes 429 (Too Many Requests) errors.

## Solution

We implemented a two-layer approach to handle this:

### 1. Concurrency Limiting (Semaphore-based Rate Limiting)

**Implementation**: Global asyncio semaphore in `app/services/llm.py`

**How it works**:
- A semaphore limits the number of concurrent LLM processing sessions
- Default: 3 concurrent sessions (configurable via `SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS`)
- When bulk uploading 5 files, only 3 will process LLM operations simultaneously
- The remaining 2 will queue and wait for a slot to become available

**Configuration**:
```bash
# Max concurrent LLM sessions (default: 3)
SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=3
```

**Code location**: 
- Semaphore initialization: `_get_llm_semaphore()` function
- Applied in: `schedule_summary_and_todos()` function

### 2. Retry with Exponential Backoff

**Implementation**: Using `tenacity` library in `GroqProvider.generate()`

**How it works**:
- Automatically retries failed requests with exponential backoff
- Specifically handles:
  - Rate limit errors (429)
  - Server errors (5xx)
  - Network timeouts and connection errors
- Each retry waits progressively longer: 1s, 2s, 4s, 8s, 16s...
- Respects `Retry-After` header from API responses

**Configuration**:
```bash
# Maximum retry attempts (default: 5)
SPEAKLY_LLM_RETRY_MAX_ATTEMPTS=5

# Minimum wait time between retries in seconds (default: 1)
SPEAKLY_LLM_RETRY_MIN_WAIT_SECONDS=1

# Maximum wait time between retries in seconds (default: 60)
SPEAKLY_LLM_RETRY_MAX_WAIT_SECONDS=60
```

**Retry logic**:
1. First attempt fails with 429 → wait 1 second
2. Second attempt fails → wait 2 seconds
3. Third attempt fails → wait 4 seconds
4. Fourth attempt fails → wait 8 seconds
5. Fifth attempt fails → wait 16 seconds
6. If all 5 attempts fail → raise LlmError

## Error Handling

### Retryable Errors
These errors trigger automatic retries:
- `429 Too Many Requests` (rate limiting)
- `5xx Server Errors` (temporary server issues)
- `httpx.TimeoutException` (request timeout)
- `httpx.NetworkError` (network connectivity issues)

### Non-Retryable Errors
These errors fail immediately without retry:
- `401 Unauthorized` (invalid API key)
- `400 Bad Request` (malformed request)
- `403 Forbidden` (insufficient permissions)
- Unexpected response format

## Monitoring

All retry attempts are logged with the following information:
- Session ID and transcription ID
- Retry attempt number
- Wait time before next retry
- Error details and status codes
- Final success/failure status

**Log examples**:
```
WARNING: Groq API rate limit hit (429). Retry-After: 5
WARNING: Retrying in 1 seconds
INFO: Acquired LLM semaphore for session 123
INFO: Released LLM semaphore for session 123
ERROR: Groq API request failed after 5 attempts: Rate limit exceeded
```

## Best Practices

### For Production
1. **Set appropriate concurrency limits** based on your API tier:
   - Free tier: `SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=2`
   - Pro tier: `SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=5`
   - Enterprise: `SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=10`

2. **Configure retry attempts** based on expected load:
   - Low traffic: Keep default (5 attempts)
   - High traffic: Reduce to 3 attempts to fail faster

3. **Monitor logs** for rate limit patterns and adjust accordingly

### For Development
- Use `SPEAKLY_DEVELOPER_MODE=true` to use mock webhooks
- Set `SPEAKLY_LLM_MAX_CONCURRENT_REQUESTS=1` to test queueing behavior
- Set `SPEAKLY_LLM_RETRY_MAX_ATTEMPTS=2` to test retry logic quickly

## Testing

### Manual Testing
```bash
# Upload 5 files simultaneously
curl -X POST http://localhost:8000/api/audio/bulk \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "files=@file1.wav" \
  -F "files=@file2.wav" \
  -F "files=@file3.wav" \
  -F "files=@file4.wav" \
  -F "files=@file5.wav"
```

### Expected Behavior
1. First 3 files start processing immediately
2. Files 4-5 wait in queue
3. As files complete, queued files begin processing
4. If rate limits hit, automatic retry with backoff
5. All files eventually complete successfully

## Dependencies

- **tenacity** (>=8.0,<9.0): Retry library with exponential backoff
  - Install: `pip install tenacity`
  - Automatically installed via `requirements.txt`

## Architecture Diagram

```
┌─────────────────────────────────────┐
│   Bulk Upload (5 audio files)      │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   Transcription Webhooks (5)        │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   LLM Semaphore (max: 3)           │◄─── Rate Limiting Layer 1
│   ┌─────────────────────────┐      │
│   │ Session 1: Processing    │      │
│   │ Session 2: Processing    │      │
│   │ Session 3: Processing    │      │
│   │ Session 4: Queued       │      │
│   │ Session 5: Queued       │      │
│   └─────────────────────────┘      │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   GroqProvider.generate()           │
│   ┌─────────────────────────┐      │
│   │ Retry Logic             │◄────── Rate Limiting Layer 2
│   │ - Attempt 1: 429        │      │
│   │ - Wait 1s               │      │
│   │ - Attempt 2: 429        │      │
│   │ - Wait 2s               │      │
│   │ - Attempt 3: Success    │      │
│   └─────────────────────────┘      │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   Groq API                          │
└─────────────────────────────────────┘
```

## Future Enhancements

1. **Adaptive rate limiting**: Automatically adjust concurrency based on API responses
2. **Per-user rate limiting**: Different limits for free vs paid users
3. **Request queuing with priority**: Prioritize interactive requests over batch
4. **Circuit breaker**: Temporarily disable LLM if API is consistently failing
5. **Metrics and alerts**: Track retry rates and alert on excessive retries
