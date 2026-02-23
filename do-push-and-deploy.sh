#!/bin/bash
# Run this after: 1) Creating the repo on GitHub  2) Logging in with: gh auth login
set -e
cd "$(dirname "$0")"

echo "→ Pushing to GitHub..."
/usr/bin/git push -u origin main

echo ""
echo "✅ Code is on GitHub: https://github.com/pborgesEdgeX/textlink-sms-api"
echo ""
echo "→ Next: Deploy on Render"
echo "  1. Open https://dashboard.render.com"
echo "  2. New + → Blueprint"
echo "  3. Select repo: pborgesEdgeX/textlink-sms-api"
echo "  4. When asked for TEXTLINK_API_KEY, paste:"
echo "     GmW3Hfv7tpxJTLhtOR2phT448ZHoh1JLYBIURx5PL2gmuSWyNdq4n5SoBI2axrai"
echo "  5. Apply and wait for deploy."
echo ""
