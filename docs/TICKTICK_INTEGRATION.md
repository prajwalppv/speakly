# TickTick Integration for Speakly

## 🎯 Overview

Direct TickTick integration will automatically sync extracted TODOs from voice sessions to your TickTick account. No N8N complexity - just a simple, reliable integration built into the backend.

---

## 🔑 TickTick OpenAPI Setup

### **Step 1: Register Your App**

1. Go to https://developer.ticktick.com/docs
2. Click **"Manage Apps"** in the top right (login with your TickTick credentials)
3. Click **"+App Name"** to create a new app
4. Fill in:
   - **Name**: `Speakly`
   - **OAuth Redirect URL**: `http://localhost:8000/api/ticktick/callback`
5. Save and copy your **Client ID** and **Client Secret**

### **Step 2: Add Credentials to `.env`**

```bash
# TickTick Integration
TICKTICK_CLIENT_ID=your_client_id_here
TICKTICK_CLIENT_SECRET=your_client_secret_here
TICKTICK_REDIRECT_URI=http://localhost:8000/api/ticktick/callback
TICKTICK_ENABLED=true
```

---

## 📚 TickTick OpenAPI Documentation

### **Base URL**
```
https://api.ticktick.com/open/v1
```

### **Authentication: OAuth 2.0**

**Authorization URL:**
```
https://ticktick.com/oauth/authorize?client_id={CLIENT_ID}&scope=tasks:write tasks:read&redirect_uri={REDIRECT_URI}&state={STATE}&response_type=code
```

**Token Exchange:**
```http
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

client_id={CLIENT_ID}
&client_secret={CLIENT_SECRET}
&code={AUTHORIZATION_CODE}
&redirect_uri={REDIRECT_URI}
&grant_type=authorization_code
```

**Response:**
```json
{
  "access_token": "xxx",
  "token_type": "bearer",
  "expires_in": 15552000,  // ~6 months
  "scope": "tasks:write tasks:read"
}
```

---

## 🔧 API Endpoints We'll Use

### **1. Create Task**

```http
POST /open/v1/task
Authorization: Bearer {ACCESS_TOKEN}
Content-Type: application/json

{
  "title": "Review budget proposal",
  "content": "From Speakly session #123\n\nExtracted context: Discussed in morning planning meeting",
  "projectId": "inbox123",
  "startDate": "2025-10-01T09:00:00+0000",
  "dueDate": "2025-10-05T17:00:00+0000",
  "priority": 3,
  "tags": ["speakly", "work"]
}
```

**Response:**
```json
{
  "id": "abc123",
  "title": "Review budget proposal",
  "projectId": "inbox123",
  "status": 0,
  "createdTime": "2025-09-30T18:30:00+0000"
}
```

### **2. Get Projects (Lists)**

```http
GET /open/v1/project
Authorization: Bearer {ACCESS_TOKEN}
```

**Response:**
```json
[
  {
    "id": "inbox123",
    "name": "Inbox"
  },
  {
    "id": "proj456",
    "name": "Work"
  }
]
```

### **3. Get Task by ID**

```http
GET /open/v1/task/{taskId}
Authorization: Bearer {ACCESS_TOKEN}
```

---

## 🏗️ Implementation Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Speakly Backend                        │
│                                                         │
│  ┌──────────────┐    ┌────────────────────────┐       │
│  │   TODO       │───→│  TickTick Service      │       │
│  │  Extraction  │    │  (services/ticktick.py)│       │
│  │   (Ollama)   │    └──────────┬─────────────┘       │
│  └──────────────┘               │                      │
│                                  │                      │
│                           OAuth2 Token                  │
│                         + HTTP Requests                 │
└──────────────────────────────────┼──────────────────────┘
                                   │
                                   ↓
                    ┌──────────────────────────┐
                    │   TickTick OpenAPI       │
                    │  api.ticktick.com        │
                    └──────────────────────────┘
```

---

## 💻 Implementation Plan

### **Phase 1: OAuth Setup** ✅ (Priority)

**Files to create:**
1. `backend/app/services/ticktick.py` - TickTick API client
2. `backend/app/routers/ticktick.py` - OAuth callback endpoint
3. `backend/app/models.py` - Add TickTickToken model
4. Update `config.py` - Add TickTick settings

**OAuth Flow:**
```python
# 1. User clicks "Connect TickTick" in frontend
#    → Redirects to TickTick authorization page

# 2. User approves permissions
#    → TickTick redirects to callback URL with code

# 3. Backend exchanges code for access token
#    → Stores token in database

# 4. Future API calls use stored token
```

### **Phase 2: Task Creation** ✅ (Priority)

**Automatic Sync:**
```python
# When TODO is extracted from session:
async def sync_todo_to_ticktick(todo: TODO, session: Session):
    """
    Automatically creates TickTick task when TODO is detected
    """
    ticktick = TickTickClient(user_id=session.user_id)
    
    task = await ticktick.create_task(
        title=todo.title,
        content=f"From Speakly session #{session.id}\n\n{todo.source_excerpt}",
        due_date=todo.due_hint,
        tags=["speakly"],
        project_id=get_user_default_project()
    )
    
    # Store task_id in database for future reference
    todo.ticktick_task_id = task.id
```

### **Phase 3: Settings UI** (Optional - Later)

- User preferences page
- Connect/disconnect TickTick account
- Select default project/list
- Enable/disable auto-sync
- Manual sync button

---

## 📦 Database Schema Changes

### **New Model: TickTickToken**

```python
class TickTickToken(Base):
    __tablename__ = "ticktick_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    scope = Column(String, default="tasks:write tasks:read")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", back_populates="ticktick_token")
```

### **Update TODO Model**

```python
class TODO(Base):
    # ... existing fields ...
    
    # Add TickTick sync tracking
    ticktick_task_id = Column(String, nullable=True, unique=True)
    ticktick_synced_at = Column(DateTime, nullable=True)
    ticktick_sync_status = Column(String, default="pending")  # pending, synced, error
```

---

## 🔒 Security Best Practices

1. **Store tokens encrypted** - Use Fernet or similar
2. **Token refresh** - Auto-refresh before expiration
3. **Error handling** - Graceful degradation if TickTick is down
4. **User control** - Easy enable/disable sync
5. **Rate limiting** - Respect TickTick API limits

---

## 🚀 Quick Start (Manual Testing)

### **Test OAuth Flow:**

```bash
# 1. Start backend
podman compose up backend

# 2. Visit authorization URL in browser
https://ticktick.com/oauth/authorize?client_id=YOUR_CLIENT_ID&scope=tasks:write%20tasks:read&redirect_uri=http://localhost:8000/api/ticktick/callback&state=test123&response_type=code

# 3. After approval, you'll be redirected with a code
http://localhost:8000/api/ticktick/callback?code=ABC123&state=test123

# 4. Backend exchanges code for token and stores it
```

### **Test Task Creation:**

```python
# Using httpx directly
import httpx

async def test_create_task():
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "title": "Test from Speakly",
        "content": "This is a test task",
        "tags": ["speakly", "test"]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.ticktick.com/open/v1/task",
            headers=headers,
            json=data
        )
        print(response.json())
```

---

## 📊 Benefits vs N8N

| Feature | Direct Integration | N8N |
|---------|-------------------|-----|
| **Setup Complexity** | Simple | Complex |
| **Dependencies** | None | Extra service |
| **Reliability** | High | Medium |
| **Latency** | Low | Medium |
| **Maintenance** | Easy | Hard |
| **User Experience** | Seamless | Requires tunnel setup |

---

## 🎯 Next Steps

1. **Add credentials to `.env`** - Get Client ID/Secret from TickTick
2. **Implement OAuth flow** - Create callback endpoint
3. **Build TickTick client** - API wrapper service
4. **Auto-sync TODOs** - Hook into TODO extraction
5. **Test thoroughly** - Verify token refresh and error handling

---

## 📚 Resources

- **TickTick OpenAPI Docs:** https://developer.ticktick.com/docs
- **OAuth 2.0 Spec:** https://oauth.net/2/
- **Unofficial Python Library:** https://github.com/lazeroffmichael/ticktick-py
- **FastAPI OAuth:** https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/

---

**Simple, direct, reliable. That's the way! 🎯**
