# TickTick Integration Testing Guide

## ✅ Implementation Complete!

The following components have been implemented:

1. **Configuration** - TickTick settings in `config.py`
2. **Database Models** - `TickTickToken` model and TODO sync fields
3. **Service Layer** - `TickTickClient` and `TickTickOAuth` classes
4. **API Routes** - OAuth endpoints and connection management
5. **Database Migration** - Successfully migrated database schema

---

## 🧪 Testing the OAuth Flow

### **Step 1: Check TickTick Status**

```bash
curl http://localhost:8000/api/ticktick/status?user_id=1
```

**Expected Response:**
```json
{
  "connected": false,
  "user_id": 1,
  "error": "No TickTick token found for user 1"
}
```

---

### **Step 2: Start OAuth Flow**

Open your browser and visit:

```
http://localhost:8000/api/ticktick/connect?user_id=1
```

This will:
1. Redirect you to TickTick's authorization page
2. Ask you to login to TickTick (if not already logged in)
3. Ask you to authorize Speakly to access your tasks
4. Redirect back to `http://localhost:8000/api/ticktick/callback` with an auth code

**Expected Result:**
```json
{
  "success": true,
  "message": "TickTick connected successfully!",
  "user_id": 1
}
```

---

### **Step 3: Verify Connection**

```bash
curl http://localhost:8000/api/ticktick/status?user_id=1
```

**Expected Response:**
```json
{
  "connected": true,
  "user_id": 1,
  "expires_at": "2025-03-30T...",
  "scope": "tasks:write tasks:read"
}
```

---

### **Step 4: Get TickTick Projects**

```bash
curl http://localhost:8000/api/ticktick/projects?user_id=1
```

**Expected Response:**
```json
{
  "success": true,
  "user_id": 1,
  "projects": [
    {
      "id": "inbox123",
      "name": "Inbox"
    },
    {
      "id": "proj456",
      "name": "Work"
    }
  ]
}
```

---

### **Step 5: Test Task Creation (Manual)**

You can test task creation by adding this temporary endpoint to `routers/ticktick.py`:

```python
@router.post("/test-create-task")
async def test_create_task(
    user_id: int = Query(default=1),
    title: str = Query(..., description="Task title"),
    db: Session = Depends(get_session),
):
    """Test endpoint to create a task."""
    client = TickTickClient(user_id, db)

    task = await client.create_task(
        title=title,
        content=f"Test task created from Speakly at {datetime.utcnow().isoformat()}",
        tags=["speakly", "test"],
    )

    return {"success": True, "task": task}
```

Then call:
```bash
curl -X POST "http://localhost:8000/api/ticktick/test-create-task?user_id=1&title=Test%20from%20Speakly"
```

Check your TickTick app - the task should appear!

---

### **Step 6: Disconnect**

```bash
curl -X POST http://localhost:8000/api/ticktick/disconnect?user_id=1
```

**Expected Response:**
```json
{
  "success": true,
  "message": "TickTick disconnected successfully",
  "user_id": 1
}
```

---

## 🔍 API Documentation

### **Available Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ticktick/connect` | Start OAuth flow |
| GET | `/api/ticktick/callback` | OAuth callback handler |
| GET | `/api/ticktick/status` | Check connection status |
| GET | `/api/ticktick/projects` | Get all projects/lists |
| POST | `/api/ticktick/disconnect` | Disconnect TickTick |

---

## 🐛 Troubleshooting

### **"TickTick integration is not enabled"**

**Solution:** Make sure your `.env` has:
```bash
TICKTICK_ENABLED=true
```

### **"TickTick credentials not configured"**

**Solution:** Verify your `.env` has valid credentials:
```bash
TICKTICK_CLIENT_ID=your_client_id
TICKTICK_CLIENT_SECRET=your_client_secret
```

### **"Token exchange failed"**

**Solution:**
1. Check that the redirect URI in TickTick app settings matches exactly: `http://localhost:8000/api/ticktick/callback`
2. Make sure you're using the authorization code immediately (it expires quickly)

### **Backend logs showing errors**

**Check logs:**
```bash
podman compose logs backend -f
```

---

## 🎯 Next Steps

1. **Test the OAuth flow manually** using the steps above
2. **Verify task creation** works in your TickTick account
3. **Integrate with TODO extraction** - When TODOs are extracted from sessions, automatically create TickTick tasks
4. **Add frontend UI** - Button to connect/disconnect TickTick in settings

---

## 📚 Key Files

- **Service:** `backend/app/services/ticktick.py`
- **Router:** `backend/app/routers/ticktick.py`
- **Models:** `backend/app/models.py` (TickTickToken, Todo updates)
- **Config:** `backend/app/config.py`
- **Migration:** `backend/scripts/migrate_ticktick.py`

---

**All systems ready! Start testing! 🚀**
