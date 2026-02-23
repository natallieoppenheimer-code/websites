# Push to GitHub and deploy on Render

Your repo is initialized and the first commit is done. Follow these steps to get it on GitHub and then on Render.

---

## 1. Create the repo on GitHub

1. Open **https://github.com/new**
2. **Repository name:** e.g. `textlink-sms-api`
3. Choose **Public**, leave "Add a README" **unchecked**
4. Click **Create repository**

---

## 2. Push this project to GitHub

In your terminal, from the project folder, run (replace `YOUR_USERNAME` and `YOUR_REPO` with your GitHub username and repo name):

```bash
cd /Users/paulocfborges/Desktop/dev

# Rename branch to main (optional, Render expects main by default)
git branch -M main

# Add your new GitHub repo as remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push (you may be asked to sign in to GitHub)
git push -u origin main
```

Example if your username is `pborgesEdgeX` and repo is `textlink-sms-api`:

```bash
git branch -M main
git remote add origin https://github.com/pborgesEdgeX/textlink-sms-api.git
git push -u origin main
```

---

## 3. Deploy on Render

1. Go to **https://render.com** and sign in (or create an account).
2. Click **New +** → **Blueprint**.
3. Connect your **GitHub** account if needed, then select the repo you just pushed (e.g. `textlink-sms-api`).
4. Render will detect `render.yaml`. Click **Apply**.
5. When prompted for **TEXTLINK_API_KEY**, paste:
   ```
   GmW3Hfv7tpxJTLhtOR2phT448ZHoh1JLYBIURx5PL2gmuSWyNdq4n5SoBI2axrai
   ```
6. Wait for the deploy to finish.

Your API will be live at:

- **Base URL:** `https://textlink-sms-api.onrender.com` (or the name you gave the service)
- **Docs:** `https://<your-service-name>.onrender.com/docs`
- **Send SMS:** `POST https://<your-service-name>.onrender.com/send-sms`

---

## 4. Use from OpenClaw

In OpenClaw, add a custom API / tool:

- **URL:** `https://<your-service-name>.onrender.com/send-sms`
- **Method:** POST
- **Body (JSON):** `{"phone_number": "+1234567890", "text": "Your message"}`

Then your assistant can send SMS through this API.
