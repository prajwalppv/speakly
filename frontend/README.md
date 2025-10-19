# 🎙️ Speakly Frontend

**Beautiful React + TypeScript frontend for privacy-first voice transcription.**

[![React](https://img.shields.io/badge/React-18.2-blue)]()
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-blue)]()
[![Vite](https://img.shields.io/badge/Vite-5.0-646CFF)]()

---

## ✨ Features

- 🎤 **Audio Upload** - Drag & drop or click to upload
- 🎧 **Voice Recorder** - Capture a note in-browser and queue it instantly
- 📦 **Bulk Upload** - Process up to 50 files with timestamp ordering
- 📊 **Sessions Dashboard** - View all recordings with AI summaries
- ✅ **Task Management** - Auto-extracted todos with TickTick sync
- 🎨 **Beautiful UI** - Gold/teal premium theme
- 🔄 **Real-time Updates** - Auto-refresh and progress tracking
- 📱 **Responsive Design** - Works on all devices
- 🎯 **Speaker Diarization** - Visualize who said what

---

## 🚀 Quick Start

### Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Visit http://localhost:5173
```

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

---

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── BulkUploader.tsx       # Multi-file upload
│   │   ├── SessionsDashboard.tsx  # Sessions list/detail
│   │   └── SettingsModal.tsx      # Settings UI
│   ├── api.ts                     # Backend API client
│   ├── App.tsx                    # Main app component
│   ├── App.css                    # Global styles
│   └── main.tsx                   # App entry point
├── public/                        # Static assets
├── index.html                     # HTML template
├── vite.config.ts                 # Vite configuration
└── package.json                   # Dependencies
```

---

## 🎨 Design System

### Colors

- **Background**: `#0a0a0a` (deep black)
- **Gold**: `#d4af37` (primary accent)
- **Teal**: `#2dd4bf` (success states)
- **Blue**: `#3b82f6` (interactive)
- **Bone**: `#e8dcc8` (text)

### Components

- **Cards**: Glassmorphism with gold borders
- **Buttons**: Blue gradient with hover lift
- **Badges**: Color-coded status indicators
- **Modals**: Backdrop blur with smooth animations

---

## 🔧 Configuration

### Environment Variables

Create `.env.local`:

```bash
# Development (uses proxy)
VITE_API_BASE_URL=proxy
VITE_BACKEND_URL_INTERNAL=http://localhost:8000

# Production (direct connection)
# VITE_API_BASE_URL=https://your-backend.railway.app
```

### API Client

The app automatically handles dev vs production:

- **Dev**: Uses Vite proxy (`/api/*` → `http://localhost:8000/api/*`)
- **Production**: Direct connection to backend URL

---

## 📦 Key Components

### BulkUploader

**Features:**

- Drag & drop multiple files
- Real-time upload progress
- Timestamp-based ordering
- Error handling per file
- Auto-clear on success
- Integrated browser-based voice recorder that feeds the upload queue

**Usage:**

```tsx
import BulkUploader from "./components/BulkUploader";

<BulkUploader />;
```

### SessionsDashboard

**Features:**

- Collapsible session cards
- AI-generated summaries
- Todo list with sync status
- Speaker diarization display
- Filter by status
- Auto-refresh every 5s

**Usage:**

```tsx
import SessionsDashboard from "./components/SessionsDashboard";

<SessionsDashboard
  isOpen={showDashboard}
  onClose={() => setShowDashboard(false)}
/>;
```

### SettingsModal

**Features:**

- TickTick OAuth integration
- Connection status
- Project selection
- Disconnect option

---

## 🌐 API Integration

### Axios Client (`api.ts`)

```typescript
// Upload single audio file
const result = await uploadAudio(file);

// Upload multiple files
const results = await uploadAudioBulk(files);

// Fetch sessions
const sessions = await fetchSessions();

// Get session details
const session = await fetchSession(sessionId);

// TickTick integration
const status = await getTickTickStatus();
```

---

## 🧪 Testing

```bash
# Run TypeScript checks
npx tsc --noEmit

# Format check
npm run format:check

# Lint
npm run lint
```

---

## 🚀 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide.

**Quick Deploy (Vercel):**

```bash
npm install -g vercel
vercel --prod
```

**Environment Variable:**

```bash
vercel env add VITE_API_BASE_URL
# Enter: https://your-backend.railway.app
```

---

## 📊 Performance

- **Bundle Size**: ~200KB gzipped
- **First Paint**: < 1s
- **Interactive**: < 2s
- **Lighthouse Score**: 90+

**Optimizations:**

- Code splitting with React.lazy
- Image optimization
- Tree shaking (Vite)
- Gzip compression
- Browser caching

---

## 🎯 Features In Detail

### Bulk Upload

- **Capacity**: Up to 50 files
- **Ordering**: Chronological by filename timestamp
- **Progress**: Real-time per-file status
- **Error Isolation**: One failure doesn't stop others

### Sessions Dashboard

- **View Modes**: List with expand/collapse
- **Filters**: All, Completed, Processing, Error
- **Auto-refresh**: 5 second intervals
- **Details**: Transcription, summary, todos, metadata

### TickTick Integration

- **OAuth Flow**: Secure authentication
- **Auto-sync**: Tasks sync to dedicated project
- **Status**: Visual sync indicators
- **Re-sync**: Manual re-sync option

---

## 🎨 Styling

### CSS Architecture

- **Global styles**: `App.css`
- **Component styles**: Inline with CSS modules
- **Theme**: CSS variables for colors
- **Responsive**: Mobile-first breakpoints

### Animations

- **Smooth transitions**: 0.3s ease
- **Hover effects**: Transform + glow
- **Modal animations**: Fade + scale
- **Loading states**: Spinner + progress bars

---

## 🔐 Security

✅ **No secrets in frontend** - Only backend URL
✅ **HTTPS enforced** - Production uses SSL
✅ **CORS protection** - Backend validates origins
✅ **Environment vars** - Never committed to git

---

## 🐛 Troubleshooting

### Dev Server Won't Start

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

### API Calls Failing

Check backend URL:

```bash
# Should proxy in dev
VITE_API_BASE_URL=proxy

# Should be full URL in production
VITE_API_BASE_URL=https://backend.railway.app
```

### CORS Errors

Update backend CORS settings:

```bash
# Backend environment
SPEAKLY_CORS_ORIGINS=https://your-frontend.vercel.app
```

---

## 📄 License

Proprietary - All rights reserved

---

## 🎉 Ready for Production!

✅ Modern React 18 + TypeScript
✅ Beautiful gold/teal UI
✅ Bulk upload with ordering
✅ Real-time updates
✅ Mobile responsive
✅ Production optimized

**Deploy with confidence! 🚀**
