#!/bin/bash
# Quick deployment script for Clawbot

set -e

echo "🚀 Clawbot Deployment Script"
echo "=============================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Check if git is initialized
if [ ! -d .git ]; then
    echo "📦 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial Clawbot deployment"
    echo "✅ Git initialized"
    echo ""
    echo "⚠️  Next steps:"
    echo "1. Create a repository on GitHub"
    echo "2. Run: git remote add origin https://github.com/YOUR_USERNAME/clawbot.git"
    echo "3. Run: git push -u origin main"
    exit 0
fi

# Check if remote is set
if ! git remote | grep -q origin; then
    echo "⚠️  No git remote found"
    echo "Please add a remote: git remote add origin https://github.com/YOUR_USERNAME/clawbot.git"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "📝 Staging changes..."
    git add .
    read -p "Enter commit message (or press Enter for default): " commit_msg
    if [ -z "$commit_msg" ]; then
        commit_msg="Update Clawbot deployment"
    fi
    git commit -m "$commit_msg"
fi

# Push to GitHub
echo "📤 Pushing to GitHub..."
git push origin main || git push origin master

echo ""
echo "✅ Code pushed to GitHub!"
echo ""
echo "🌐 Next steps for deployment:"
echo ""
echo "For Render:"
echo "1. Go to https://render.com"
echo "2. New + → Blueprint"
echo "3. Select your repository"
echo "4. Add environment variables:"
echo "   - GOOGLE_CLIENT_ID"
echo "   - GOOGLE_CLIENT_SECRET"
echo "   - GOOGLE_REDIRECT_URI (https://your-app.onrender.com/auth/callback)"
echo "5. Deploy!"
echo ""
echo "For Docker:"
echo "1. docker build -t clawbot ."
echo "2. docker run -p 8000:8000 --env-file .env clawbot"
echo ""
echo "For Docker Compose:"
echo "1. docker-compose up -d"
echo ""
