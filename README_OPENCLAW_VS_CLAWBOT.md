# OpenClaw vs Clawbot – What’s What

## The confusion

**OpenClaw** and **Clawbot** are two different things. Both have “claw” in the name, but they are not the same app.

---

## OpenClaw (your existing assistant)

- **What it is:** The assistant you already use – TUI + gateway.
- **Where it lives:** Installed on your Mac (e.g. via Homebrew or another installer). **Not in this repo.**
- **How you run it:**  
  `openclaw tui --url ws://127.0.0.1:18789 --password CrazyClaw1!`
- **We don’t control it:** We didn’t build OpenClaw and we don’t have its source code here. We can’t change how OpenClaw starts or how it’s configured from this project.

So: **“OpenClaw” = the assistant app you already have.**

---

## Clawbot (what we built in this repo)

- **What it is:** An HTTP API server that provides:
  - Gmail, Calendar, GSuite
  - Memory (daily context, long-term)
  - TextLink SMS
  - Token caching, multi-agent routing
- **Where it lives:** This repo – `/Users/paulocfborges/Desktop/dev`.
- **How you run it:**  
  `./start_clawbot.sh`  
  → API at **http://localhost:8000**
- **We control it:** All Clawbot code and config are in this project.

So: **“Clawbot” = the backend/tools API we built in this repo.**

---

## How they work together

- **OpenClaw** = the front-end assistant (TUI, gateway on port 18789).
- **Clawbot** = the backend that adds Gmail, Calendar, Memory, SMS.

**“Incorporating Clawbot into OpenClaw”** means:  
**Configure OpenClaw so it calls Clawbot’s API** (http://localhost:8000).  
That configuration is done **inside OpenClaw’s setup** (its config file or UI), not by editing Clawbot.

So:

1. **Clawbot** must be running: `./start_clawbot.sh` → http://localhost:8000.
2. **OpenClaw** must be running: your usual `openclaw tui ...` (and its gateway).
3. **OpenClaw** must be **configured** to use Clawbot (custom API / tools base URL = `http://localhost:8000`).

Until step 3 is done in OpenClaw’s config, OpenClaw is “set up” as an assistant, but it is **not** yet using Gmail/Calendar/Memory/SMS from Clawbot.

---

## Making sure “OpenClaw is set up correctly”

- **OpenClaw itself** (TUI, gateway, auth): that’s the OpenClaw project’s docs/setup. We can’t change that from here.
- **OpenClaw + Clawbot**: “set up correctly” =  
  - Clawbot running (`./start_clawbot.sh`).  
  - OpenClaw running (`openclaw tui --url ws://127.0.0.1:18789 ...`).  
  - OpenClaw config points to `http://localhost:8000` for Clawbot’s tools/API.

To find **where OpenClaw’s config is** (so we can add Clawbot there):

```bash
which openclaw
```

Then check:

- Same directory as the `openclaw` binary (e.g. config file next to it).
- `~/.openclaw/` or `~/.config/openclaw/`.
- OpenClaw’s official docs for “config file” or “custom API / tools”.

Once you have that path or a screenshot of the config, we can say exactly what to add so OpenClaw uses Clawbot.

---

## One-line summary

- **OpenClaw** = your assistant (external app, not in this repo).  
- **Clawbot** = the API in this repo (Gmail, Calendar, Memory, SMS).  
- **“All set up correctly”** = OpenClaw running + Clawbot running + OpenClaw configured to call `http://localhost:8000`.
