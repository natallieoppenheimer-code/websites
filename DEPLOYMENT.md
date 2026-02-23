# Clawbot Deployment Guide

Complete guide to deploy Clawbot with all integrations (Gmail, Calendar, GSuite, Memory System).

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google Cloud Setup](#google-cloud-setup)
3. [Environment Configuration](#environment-configuration)
4. [Deployment Options](#deployment-options)
   - [Render (Recommended)](#render-recommended)
   - [Docker](#docker)
   - [Railway](#railway)
   - [Fly.io](#flyio)
5. [Post-Deployment](#post-deployment)
6. [Production Checklist](#production-checklist)

## Prerequisites

- Python 3.8+
- Google Cloud account
- GitHub account (for deployment)
- (Optional) Redis account/hosting for production memory storage

## Google Cloud Setup

### 1. Create/Select Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Note your Project ID

### 2. Enable APIs

Enable the following APIs:
- **Gmail API**
- **Google Calendar API**
- **Admin SDK API** (for GSuite)

**Steps:**
1. Go to **APIs & Services** → **Library**
2. Search and enable each API
3. Wait for activation (usually instant)

### 3. Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. If prompted, configure OAuth consent screen:
   - **User Type**: External (or Internal for GSuite)
   - **App name**: Clawbot
   - **Support email**: Your email
   - **Authorized domains**: Your domain (e.g., `onrender.com`)
   - **Scopes**: Add scopes for Gmail, Calendar, Admin SDK
   - **Test users**: Add your email for testing

4. Create OAuth Client:
   - **Application type**: Web application
   - **Name**: Clawbot Production
   - **Authorized redirect URIs**: 
     - `https://your-app.onrender.com/auth/callback` (production)
     - `http://localhost:8000/auth/callback` (local dev)
   - Click **Create**

5. **Save credentials:**
   - Copy **Client ID**
   - Copy **Client Secret**
   - Keep these secure!

### 4. (Optional) Domain-wide Delegation for GSuite

If using GSuite Admin API:
1. Go to **APIs & Services** → **Credentials**
2. Click on your OAuth client
3. Enable **Domain-wide delegation**
4. Note the **Client ID**
5. In GSuite Admin Console, add this Client ID with required scopes

## Environment Configuration

### Create Production `.env`

Copy `.env.example` and configure:

```bash
# Google OAuth2 (REQUIRED)
GOOGLE_CLIENT_ID=your_production_client_id
GOOGLE_CLIENT_SECRET=your_production_client_secret
GOOGLE_REDIRECT_URI=https://your-app.onrender.com/auth/callback

# Token Cache (file or redis)
TOKEN_CACHE_TYPE=redis  # Use redis for production
TOKEN_CACHE_PATH=./.token_cache

# Redis Configuration (if using redis)
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your-redis-password

# Multi-Agent Configuration
ENABLE_MULTI_AGENT=true
AGENT_ROUTING_STRATEGY=intent_based

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Optional: TextLink SMS (if using SMS features)
TEXTLINK_API_KEY=your_textlink_key
```

## Deployment Options

### Render (Recommended)

Render is the easiest option and works great with FastAPI.

#### Step 1: Update `render.yaml`

The `render.yaml` file is already configured. Update it if needed:

```yaml
services:
  - type: web
    name: clawbot-api
    runtime: python
    plan: starter  # Use starter for always-on (free tier sleeps)
    healthCheckPath: /health
    
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn clawbot_api:app --host 0.0.0.0 --port $PORT
    
    envVars:
      - key: GOOGLE_CLIENT_ID
        sync: false
      - key: GOOGLE_CLIENT_SECRET
        sync: false
      - key: GOOGLE_REDIRECT_URI
        sync: false
      - key: TOKEN_CACHE_TYPE
        value: file  # Or use Redis addon
      - key: ENABLE_MULTI_AGENT
        value: "true"
      - key: AGENT_ROUTING_STRATEGY
        value: intent_based
```

#### Step 2: Push to GitHub

```bash
cd /Users/paulocfborges/Desktop/dev

# Initialize git if not already done
git init
git add .
git commit -m "Initial Clawbot deployment"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/clawbot.git
git branch -M main
git push -u origin main
```

#### Step 3: Deploy on Render

1. Go to [render.com](https://render.com) and sign in
2. Click **New +** → **Blueprint**
3. Connect your GitHub account
4. Select your repository (`clawbot`)
5. Render will detect `render.yaml`
6. Click **Apply**
7. **Add Environment Variables**:
   - `GOOGLE_CLIENT_ID`: Your Google Client ID
   - `GOOGLE_CLIENT_SECRET`: Your Google Client Secret
   - `GOOGLE_REDIRECT_URI`: `https://your-app.onrender.com/auth/callback`
   - `TOKEN_CACHE_TYPE`: `file` (or configure Redis addon)
8. Click **Apply** and wait for deployment

#### Step 4: Add Redis (Optional but Recommended)

1. In Render dashboard, click **New +** → **Redis**
2. Name it `clawbot-redis`
3. Copy connection details
4. Update environment variables:
   - `TOKEN_CACHE_TYPE`: `redis`
   - `REDIS_HOST`: From Redis instance
   - `REDIS_PORT`: `6379`
   - `REDIS_PASSWORD`: From Redis instance
5. Redeploy your web service

#### Step 5: Update Google OAuth Redirect URI

1. Go back to Google Cloud Console
2. Edit your OAuth client
3. Add redirect URI: `https://your-app.onrender.com/auth/callback`
4. Save

Your API will be live at: `https://your-app.onrender.com`

### Docker

#### Step 1: Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories for cache
RUN mkdir -p .token_cache .memory_store

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "clawbot_api:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Step 2: Build and Run

```bash
# Build image
docker build -t clawbot .

# Run container
docker run -d \
  --name clawbot \
  -p 8000:8000 \
  -e GOOGLE_CLIENT_ID=your_client_id \
  -e GOOGLE_CLIENT_SECRET=your_client_secret \
  -e GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback \
  -e TOKEN_CACHE_TYPE=file \
  -v $(pwd)/.token_cache:/app/.token_cache \
  -v $(pwd)/.memory_store:/app/.memory_store \
  clawbot
```

#### Step 3: Docker Compose (with Redis)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  clawbot:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI}
      - TOKEN_CACHE_TYPE=redis
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_DB=0
    depends_on:
      - redis
    volumes:
      - ./data:/app/data

volumes:
  redis_data:
```

Run:
```bash
docker-compose up -d
```

### Railway

1. Go to [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub**
3. Select your repository
4. Add environment variables (same as Render)
5. Railway auto-detects Python and deploys
6. Add Redis plugin if needed

### Fly.io

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `fly auth login`
3. Launch: `fly launch`
4. Set secrets:
   ```bash
   fly secrets set GOOGLE_CLIENT_ID=your_id
   fly secrets set GOOGLE_CLIENT_SECRET=your_secret
   fly secrets set GOOGLE_REDIRECT_URI=https://your-app.fly.dev/auth/callback
   ```
5. Deploy: `fly deploy`

## Post-Deployment

### 1. Verify Deployment

```bash
# Health check
curl https://your-app.onrender.com/health

# API docs
open https://your-app.onrender.com/docs
```

### 2. Test OAuth Flow

1. Get authorization URL:
   ```bash
   curl "https://your-app.onrender.com/auth/authorize?user_id=test_user"
   ```

2. Visit the URL in browser
3. Grant permissions
4. Handle callback (you'll be redirected)

### 3. Test Endpoints

```bash
# Check auth status
curl "https://your-app.onrender.com/auth/status/test_user"

# Test Gmail (after auth)
curl "https://your-app.onrender.com/gmail/messages?user_id=test_user"

# Test Memory
curl -X POST "https://your-app.onrender.com/memory/store?user_id=test_user&content=Test%20memory"
```

### 4. Monitor Logs

**Render:**
- Dashboard → Your Service → Logs

**Docker:**
```bash
docker logs -f clawbot
```

## Production Checklist

- [ ] Google OAuth credentials configured
- [ ] All required APIs enabled in Google Cloud
- [ ] Redirect URI matches production URL
- [ ] Environment variables set securely
- [ ] Redis configured (recommended for production)
- [ ] Health check endpoint working (`/health`)
- [ ] OAuth flow tested end-to-end
- [ ] Memory system tested (store/retrieve)
- [ ] Gmail integration tested
- [ ] Calendar integration tested
- [ ] GSuite integration tested (if using)
- [ ] CORS configured correctly
- [ ] HTTPS enabled (automatic on Render/Railway/Fly.io)
- [ ] Monitoring/logging set up
- [ ] Backup strategy for Redis (if using)
- [ ] Domain configured (optional)

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth Client ID | `123456789.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth Client Secret | `GOCSPX-...` |
| `GOOGLE_REDIRECT_URI` | Yes | OAuth redirect URI | `https://app.onrender.com/auth/callback` |
| `TOKEN_CACHE_TYPE` | No | `file` or `redis` | `redis` |
| `REDIS_HOST` | If redis | Redis hostname | `redis-12345.redislabs.com` |
| `REDIS_PORT` | If redis | Redis port | `6379` |
| `REDIS_PASSWORD` | If redis | Redis password | `...` |
| `ENABLE_MULTI_AGENT` | No | Enable multi-agent routing | `true` |
| `AGENT_ROUTING_STRATEGY` | No | Routing strategy | `intent_based` |

## Troubleshooting

### OAuth Errors

**"redirect_uri_mismatch"**
- Check redirect URI matches exactly in Google Console
- Include protocol (`https://`)
- No trailing slashes

**"invalid_client"**
- Verify Client ID and Secret are correct
- Check environment variables are set

### Memory Storage Issues

**File-based not persisting**
- Ensure volume mounts in Docker
- Check file permissions
- Use Redis for production

**Redis connection errors**
- Verify Redis host/port
- Check password
- Test connection: `redis-cli -h host -p port -a password ping`

### Deployment Issues

**Build failures**
- Check Python version (3.8+)
- Verify `requirements.txt` is correct
- Check build logs

**Service not starting**
- Check start command: `uvicorn clawbot_api:app --host 0.0.0.0 --port $PORT`
- Verify port matches `$PORT` environment variable
- Check application logs

## Security Best Practices

1. **Never commit `.env` files** - Use environment variables
2. **Use Redis with password** in production
3. **Enable HTTPS** (automatic on most platforms)
4. **Rotate credentials** periodically
5. **Limit OAuth scopes** to minimum required
6. **Use domain-wide delegation** carefully for GSuite
7. **Monitor access logs** regularly
8. **Set up rate limiting** (consider adding middleware)

## Next Steps

1. Set up monitoring (e.g., Sentry for errors)
2. Configure custom domain (optional)
3. Set up CI/CD pipeline
4. Add rate limiting
5. Implement backup strategy for Redis
6. Set up alerts for errors

## Support

For issues:
1. Check logs in deployment platform
2. Verify environment variables
3. Test locally first
4. Check Google Cloud Console for API quotas/errors
