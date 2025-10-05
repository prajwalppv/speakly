#!/bin/bash
# Speakly Production Deployment Script
# Run this to deploy both backend and frontend to Fly.io

set -e  # Exit on any error

echo "🚀 Speakly Production Deployment"
echo "================================"
echo ""

# Check if flyctl is installed
if ! command -v flyctl &> /dev/null; then
    echo "❌ flyctl not found. Install it first:"
    echo "   curl -L https://fly.io/install.sh | sh"
    exit 1
fi

# Check if logged in
if ! flyctl auth whoami &> /dev/null; then
    echo "❌ Not logged in to Fly.io"
    echo "   Run: flyctl auth login"
    exit 1
fi

echo "✅ flyctl installed and authenticated"
echo ""

# =============================================================================
# Configuration
# =============================================================================

# Get Groq API key from .env
if [ -f .env ]; then
    GROQ_API_KEY=$(grep "^GROQ_API_KEY=" .env | cut -d '=' -f2)
else
    echo "❌ .env file not found"
    exit 1
fi

if [ -z "$GROQ_API_KEY" ]; then
    echo "❌ GROQ_API_KEY not set in .env"
    echo "   Get a free key from: https://console.groq.com"
    exit 1
fi

echo "✅ Groq API key found"
echo ""

# =============================================================================
# Gather Production Secrets
# =============================================================================

echo "📝 Production Configuration"
echo "============================"
echo ""
echo "You need to provide production secrets for deployment."
echo ""

# Database URL
echo "1️⃣  PostgreSQL Database URL"
echo "   Format: postgres://user:pass@speakly-db.flycast:5432/speakly"
read -p "   DATABASE_URL: " DATABASE_URL

# Clerk Keys
echo ""
echo "2️⃣  Clerk Production Keys (from https://clerk.com)"
echo "   Switch to Production in Clerk dashboard first!"
read -p "   CLERK_SECRET_KEY (sk_live_...): " CLERK_SECRET_KEY
read -p "   CLERK_PUBLISHABLE_KEY (pk_live_...): " CLERK_PUBLISHABLE_KEY

# ElevenLabs Keys (from .env)
ELEVENLABS_API_KEY=$(grep "^ELEVENLABS_API_KEY=" .env | cut -d '=' -f2)
ELEVENLABS_WEBHOOK_SECRET=$(grep "^ELEVENLABS_WEBHOOK_SECRET=" .env | cut -d '=' -f2)

echo ""
echo "3️⃣  Using ElevenLabs keys from .env"
echo "   API Key: ${ELEVENLABS_API_KEY:0:20}..."
echo "   Webhook Secret: ${ELEVENLABS_WEBHOOK_SECRET:0:20}..."

# TickTick (optional)
TICKTICK_CLIENT_ID=$(grep "^TICKTICK_CLIENT_ID=" .env | cut -d '=' -f2)
TICKTICK_CLIENT_SECRET=$(grep "^TICKTICK_CLIENT_SECRET=" .env | cut -d '=' -f2 | tr -d '"')

echo ""
echo "4️⃣  Using TickTick keys from .env"
echo "   Client ID: $TICKTICK_CLIENT_ID"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Confirm
read -p "Ready to deploy? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

echo ""
echo "🚀 Starting deployment..."
echo ""

# =============================================================================
# Deploy Backend
# =============================================================================

echo "📦 Deploying Backend..."
echo "======================="
echo ""

cd "$(dirname "$0")"

# Set backend secrets
echo "🔒 Setting backend secrets..."
flyctl secrets set \
  SPEAKLY_ENVIRONMENT=prod \
  SPEAKLY_LOG_LEVEL=INFO \
  SPEAKLY_DATABASE_URL="$DATABASE_URL" \
  CLERK_SECRET_KEY="$CLERK_SECRET_KEY" \
  ELEVENLABS_API_KEY="$ELEVENLABS_API_KEY" \
  ELEVENLABS_WEBHOOK_SECRET="$ELEVENLABS_WEBHOOK_SECRET" \
  ELEVENLABS_BASE_URL="https://api.elevenlabs.io" \
  ELEVENLABS_DIARIZATION_ENABLED=true \
  GROQ_API_KEY="$GROQ_API_KEY" \
  GROQ_MODEL="deepseek-r1-distill-llama-70b" \
  TICKTICK_ENABLED=true \
  TICKTICK_CLIENT_ID="$TICKTICK_CLIENT_ID" \
  TICKTICK_CLIENT_SECRET="$TICKTICK_CLIENT_SECRET" \
  TICKTICK_REDIRECT_URI="https://speakly-backend.fly.dev/api/ticktick/callback" \
  --app speakly-backend

echo ""
echo "🏗️  Building and deploying backend..."
flyctl deploy --app speakly-backend

echo ""
echo "✅ Backend deployed!"
echo ""

# Get backend URL
BACKEND_URL=$(flyctl info --app speakly-backend | grep "Hostname" | awk '{print $3}' | head -1)
if [ -z "$BACKEND_URL" ]; then
    BACKEND_URL="speakly-backend.fly.dev"
fi

echo "🌐 Backend URL: https://$BACKEND_URL"
echo ""

# =============================================================================
# Deploy Frontend
# =============================================================================

echo "📦 Deploying Frontend..."
echo "========================"
echo ""

cd frontend

# Deploy frontend with build args
echo "🏗️  Building and deploying frontend..."
flyctl deploy \
  --build-arg VITE_CLERK_PUBLISHABLE_KEY="$CLERK_PUBLISHABLE_KEY" \
  --build-arg VITE_API_BASE_URL="https://$BACKEND_URL" \
  --app speakly-frontend

echo ""
echo "✅ Frontend deployed!"
echo ""

# Get frontend URL
FRONTEND_URL=$(flyctl info --app speakly-frontend | grep "Hostname" | awk '{print $3}' | head -1)
if [ -z "$FRONTEND_URL" ]; then
    FRONTEND_URL="speakly-frontend.fly.dev"
fi

echo "🌐 Frontend URL: https://$FRONTEND_URL"
echo ""

# =============================================================================
# Post-Deployment
# =============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎉 Deployment Complete!"
echo ""
echo "📝 Next Steps:"
echo ""
echo "1️⃣  Update Clerk Settings:"
echo "   → Go to: https://clerk.com"
echo "   → Switch to Production"
echo "   → Paths → Set all URLs to: https://$FRONTEND_URL"
echo "   → Allowed Origins → Add:"
echo "      • https://$FRONTEND_URL"
echo "      • https://$BACKEND_URL"
echo ""
echo "2️⃣  Run Database Migrations:"
echo "   flyctl ssh console --app speakly-backend"
echo "   python -m backend.migrations.add_clerk_auth_to_users"
echo "   python -m backend.migrations.remove_unique_constraint_from_name"
echo "   exit"
echo ""
echo "3️⃣  Test Your App:"
echo "   → Visit: https://$FRONTEND_URL"
echo "   → Sign in with Google/Apple"
echo "   → Upload audio files"
echo "   → Check AI summaries (powered by Groq!)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔗 Quick Links:"
echo "   Frontend:  https://$FRONTEND_URL"
echo "   Backend:   https://$BACKEND_URL"
echo "   API Docs:  https://$BACKEND_URL/docs"
echo ""
echo "📊 Monitor Logs:"
echo "   Backend:   flyctl logs --app speakly-backend"
echo "   Frontend:  flyctl logs --app speakly-frontend"
echo ""
echo "🚀 Your app is now live with Groq-powered AI!"
echo ""
