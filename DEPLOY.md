# Deploy this app on Render (OpenClaw-style)

Your FastAPI SMS app can run on **Render** the same way OpenClaw does. Once it’s deployed, OpenClaw (or anything else) can call your SMS API by URL.

## 1. Push the project to GitHub

```bash
cd /Users/paulocfborges/Desktop/dev
git init
git add .
git commit -m "FastAPI TextLink SMS API"
# Create a new repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

## 2. Deploy on Render

1. Go to **[render.com](https://render.com)** and sign in (or create an account).
2. **New → Blueprint**.
3. Connect the GitHub repo that contains this project.
4. Render will detect `render.yaml`. Confirm the service (e.g. `textlink-sms-api`).
5. When prompted for **TEXTLINK_API_KEY**, paste your key:  
   `GmW3Hfv7tpxJTLhtOR2phT448ZHoh1JLYBIURx5PL2gmuSWyNdq4n5SoBI2axrai`
6. Click **Apply** and wait for the first deploy to finish.

Your API will be at:

**`https://<your-service-name>.onrender.com`**

- Docs: `https://<your-service-name>.onrender.com/docs`
- Send SMS: `POST https://<your-service-name>.onrender.com/send-sms`

## 3. Use from OpenClaw

After the app is deployed:

- In OpenClaw (or your assistant config), add a **custom API / tool** that calls:
  - **URL:** `https://<your-service-name>.onrender.com/send-sms`
  - **Method:** POST  
  - **Body (JSON):** `{"phone_number": "+1234567890", "text": "Your message"}`

Then your OpenClaw assistant can send SMS through this API.

## Free tier note

On Render’s **free** plan the service sleeps after ~15 minutes of no traffic. The first request after that may take a few seconds to wake. For always-on, use a paid plan (e.g. Starter) in the Render dashboard.
