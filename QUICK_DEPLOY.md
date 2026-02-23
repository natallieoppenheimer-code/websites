# Quick Deployment Guide

Fastest way to get Clawbot deployed.

## Option 1: Render (Easiest - 5 minutes)

### Step 1: Push to GitHub

```bash
cd /Users/paulocfborges/Desktop/dev

# If not already a git repo
git init
git add .
git commit -m "Initial Clawbot deployment"

# Create repo on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/clawbot.git
git branch -M main
git push -u origin main
```

Or use the deploy script:
```bash
./deploy.sh
```

### Step 2: Deploy on Render

1. Go to [render.com](https://render.com) → Sign in
2. **New +** → **Blueprint**
3. Connect GitHub → Select `clawbot` repo
4. Render detects `render.yaml` → Click **Apply**
5. **Add Environment Variables**:
   ```
   GOOGLE_CLIENT_ID=your_client_id
   GOOGLE_CLIENT_SECRET=your_client_secret
   GOOGLE_REDIRECT_URI=https://clawbot-api.onrender.com/auth/callback
   ```
6. Click **Apply** → Wait for deployment

### Step 3: Update Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. **APIs & Services** → **Credentials**
3. Edit your OAuth client
4. Add redirect URI: `https://clawbot-api.onrender.com/auth/callback`
5. Save

**Done!** Your API is at: `https://clawbot-api.onrender.com`

---

## Option 2: Docker (Local/Production)

### Quick Start

```bash
# Build and run
docker-compose up -d

# Or manually
docker build -t clawbot .
docker run -p 8000:8000 --env-file .env clawbot
```

**Access:** http://localhost:8000

---

## Option 3: Railway (Alternative)

1. Go to [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub**
3. Select repo → Add env vars → Deploy

---

## Verify Deployment

```bash
# Health check
curl https://your-app.onrender.com/health

# API docs
open https://your-app.onrender.com/docs
```

---

## What You Need Before Deploying

✅ **Google OAuth Credentials:**
- Client ID
- Client Secret
- Redirect URI configured

✅ **GitHub Repository:**
- Code pushed to GitHub

✅ **Environment Variables:**
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

---

## Full Documentation

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Detailed setup instructions
- Google Cloud configuration
- Redis setup
- Production checklist
- Troubleshooting
