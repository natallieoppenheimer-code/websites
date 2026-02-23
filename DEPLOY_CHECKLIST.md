# Clawbot Deployment Checklist

Follow these steps in order to deploy Clawbot.

## Pre-Deployment Setup

### ✅ Step 1: Google Cloud Configuration

- [ ] Create/select Google Cloud project
- [ ] Enable Gmail API
- [ ] Enable Google Calendar API
- [ ] Enable Admin SDK API (if using GSuite)
- [ ] Configure OAuth consent screen
- [ ] Create OAuth 2.0 credentials
- [ ] Copy Client ID: `_________________`
- [ ] Copy Client Secret: `_________________`
- [ ] Note: Redirect URI will be set after deployment

### ✅ Step 2: Local Testing

- [ ] Copy `.env.example` to `.env`
- [ ] Fill in Google OAuth credentials in `.env`
- [ ] Test locally: `uvicorn clawbot_api:app --reload`
- [ ] Verify `/health` endpoint works
- [ ] Test OAuth flow locally
- [ ] Test at least one integration (Gmail/Calendar)

### ✅ Step 3: Prepare Code

- [ ] Review all files are committed
- [ ] Check `.gitignore` excludes `.env`, `.token_cache`, `.memory_store`
- [ ] Verify `requirements.txt` is up to date
- [ ] Test setup script: `python setup_clawbot.py`

## Deployment

### ✅ Step 4: GitHub Setup

- [ ] Create GitHub repository (or use existing)
- [ ] Initialize git: `git init` (if needed)
- [ ] Add files: `git add .`
- [ ] Commit: `git commit -m "Initial Clawbot deployment"`
- [ ] Add remote: `git remote add origin https://github.com/YOUR_USERNAME/clawbot.git`
- [ ] Push: `git push -u origin main`

**OR use the deploy script:**
```bash
./deploy.sh
```

### ✅ Step 5: Choose Deployment Platform

**Option A: Render (Recommended)**
- [ ] Go to render.com and sign in
- [ ] Click "New +" → "Blueprint"
- [ ] Connect GitHub account
- [ ] Select your repository
- [ ] Render detects `render.yaml` → Click "Apply"
- [ ] Add environment variables (see below)
- [ ] Wait for deployment to complete
- [ ] Note your app URL: `https://_________________.onrender.com`

**Option B: Docker**
- [ ] Build image: `docker build -t clawbot .`
- [ ] Run container: `docker run -p 8000:8000 --env-file .env clawbot`
- [ ] Or use docker-compose: `docker-compose up -d`

**Option C: Railway**
- [ ] Go to railway.app
- [ ] New Project → Deploy from GitHub
- [ ] Select repository
- [ ] Add environment variables
- [ ] Deploy

### ✅ Step 6: Environment Variables

Set these in your deployment platform:

```
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
GOOGLE_REDIRECT_URI=https://your-app.onrender.com/auth/callback
TOKEN_CACHE_TYPE=file
ENABLE_MULTI_AGENT=true
AGENT_ROUTING_STRATEGY=intent_based
```

**For Redis (optional but recommended):**
```
TOKEN_CACHE_TYPE=redis
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password
```

### ✅ Step 7: Update Google OAuth Redirect URI

- [ ] Go to Google Cloud Console
- [ ] APIs & Services → Credentials
- [ ] Click on your OAuth client
- [ ] Add authorized redirect URI: `https://your-app.onrender.com/auth/callback`
- [ ] Save changes

## Post-Deployment Verification

### ✅ Step 8: Test Deployment

- [ ] Health check: `curl https://your-app.onrender.com/health`
- [ ] API docs: Open `https://your-app.onrender.com/docs`
- [ ] Test OAuth flow:
  ```bash
  curl "https://your-app.onrender.com/auth/authorize?user_id=test_user"
  ```
- [ ] Complete OAuth flow in browser
- [ ] Verify callback works
- [ ] Test memory storage:
  ```bash
  curl -X POST "https://your-app.onrender.com/memory/store?user_id=test_user&content=Test"
  ```
- [ ] Test Gmail endpoint (after auth):
  ```bash
  curl "https://your-app.onrender.com/gmail/messages?user_id=test_user"
  ```

### ✅ Step 9: Production Hardening

- [ ] Set up Redis (if not using file storage)
- [ ] Configure custom domain (optional)
- [ ] Set up monitoring/logging
- [ ] Review security settings
- [ ] Test all integrations
- [ ] Document your deployment URL
- [ ] Share API docs URL with team

## Quick Reference

### Your Deployment URLs

- **API Base URL:** `https://_________________.onrender.com`
- **API Docs:** `https://_________________.onrender.com/docs`
- **Health Check:** `https://_________________.onrender.com/health`

### Important Credentials

- **Google Client ID:** `_________________`
- **Google Client Secret:** `_________________` (keep secret!)
- **Redirect URI:** `https://_________________.onrender.com/auth/callback`

### Useful Commands

```bash
# Local development
uvicorn clawbot_api:app --reload

# Check health
curl https://your-app.onrender.com/health

# View logs (Render)
# Dashboard → Your Service → Logs

# View logs (Docker)
docker logs -f clawbot-api

# Restart service (Docker)
docker-compose restart
```

## Troubleshooting

**OAuth not working?**
- Check redirect URI matches exactly
- Verify credentials in environment variables
- Check Google Cloud Console for errors

**Service not starting?**
- Check logs in deployment platform
- Verify all environment variables are set
- Check Python version (3.8+)

**Memory not persisting?**
- Use Redis for production
- Check volume mounts in Docker
- Verify file permissions

## Next Steps After Deployment

1. ✅ Test all endpoints
2. ✅ Integrate with OpenClaw
3. ✅ Set up monitoring
4. ✅ Configure backups (if using Redis)
5. ✅ Document your setup
6. ✅ Share with team

---

**Need help?** Check [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.
