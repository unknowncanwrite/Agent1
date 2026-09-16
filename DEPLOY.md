# 🚀 Deploy OMNI-AGENT - FIXED ALL ERRORS (Latest)

## ❌ Your Current Error (Logs Pasted Into Start Command):

```
==> Running '2026-09-15T19:33:13.323107845Z ==> Using Ruby version 3.4.4 (default)...'
bash: -c: line 1: syntax error near unexpected token `('
Exited with status 2
```

**Cause**: Your **Start Command** field in Render dashboard contains **entire build logs**, not the actual start command! You pasted logs into start command field.

Look at log:
```
Running '2026-09-15T19:33:13.323107845Z ==> Using Ruby version 3.4.4...'
```
It tries to run logs as a command - fails with syntax error near `(`.

**Fix**: Go to Render Dashboard → Your Service → Settings → Build & Deploy → Fix these 2 fields to EXACT values below.

---

## ✅ CORRECT SETTINGS (Copy-Paste Exactly):

Go to **Render Dashboard → Your Service → Settings → Build & Deploy**

### Build Command (EXACT - Copy This):
```
pip install -r requirements.txt
```

### Start Command (EXACT - Copy This):
```
python3 main.py serve --host 0.0.0.0 --port $PORT
```

### Runtime:
- **Python 3** (NOT Elixir, NOT Ruby, NOT Node, NOT Docker)

### Branch:
- `arena/01a0a65b-agent1`

### Environment Variables:
- `OPENROUTER_API_KEY` = your free key from https://openrouter.ai/keys
- `PYTHON_VERSION` = `3.11.11`

Then **Save Changes** → **Manual Deploy → Deploy latest commit**

---

## ✅ EASIEST: DELETE AND USE BLUEPRINT (No Manual Typing, No Errors)

Manual Web Service is error-prone (you pasted logs). Use Blueprint - it reads `render.yaml` with correct commands auto.

1. **Delete current broken service** in Render dashboard
2. Go to **New → Blueprint**
3. Connect repo `unknowncanwrite/Agent1`, branch `arena/01a0a65b-agent1`
4. Render reads `render.yaml`:
   ```yaml
   buildCommand: pip install -r requirements.txt
   startCommand: python3 main.py serve --host 0.0.0.0 --port $PORT
   ```
5. Add env var `OPENROUTER_API_KEY`
6. **Apply** → Deploy → Works! No manual typing, no log pasting.

**Blueprint is recommended** - it prevents all 3 errors you hit.

---

## ✅ DOCKER (Most Reliable, Bypasses Python Detection):

1. New → Web Service → **Runtime: Docker**
2. Connect repo, branch `arena/01a0a65b-agent1`
3. **Dockerfile Path**: `./Dockerfile`
4. Env: `OPENROUTER_API_KEY`
5. Deploy → Works! Docker never has Erlang/Ruby/Python detection issues.

---

## 📋 All Errors You Hit & Fixes:

| Error | Cause | Fix |
|-------|-------|-----|
| `Using Erlang... mix phx.digest` | Selected Elixir runtime | Select **Python 3** runtime |
| `python: command not found` | Used `python` not `python3` | Use `python3` |
| `No open ports detected` | Start command missing `--host 0.0.0.0 --port $PORT` | Use `python3 main.py serve --host 0.0.0.0 --port $PORT` |
| `ModuleNotFoundError: dotenv` | Build command = start command, deps not installed | Build = `pip install -r requirements.txt`, Start = `python3 main.py...` |
| `bash: syntax error near '('` + logs in start command | Pasted build logs into Start Command field | Fix Start Command to `python3 main.py serve --host 0.0.0.0 --port $PORT` (copy exact) |

---

## 🖥️ Local PC (100% Works, No Render):

```bash
git clone https://github.com/unknowncanwrite/Agent1.git
cd Agent1
git checkout arena/01a0a65b-agent1
pip install -r requirements.txt
cp .env.example .env
# Edit .env, add OPENROUTER_API_KEY=sk-or-v1-... (free from https://openrouter.ai/keys)

python3 main.py serve --host 0.0.0.0 --port 8000
# Open http://localhost:8000 → Manus-like chat UI
```

---

## 🔍 Expected Success Logs:

After fixing Build/Start commands correctly, you should see:

```
==> Using Python version 3.11.11 via .python-version
==> Running build command 'pip install -r requirements.txt'...
Successfully installed ...
==> Build successful 🎉
==> Deploying...
==> Running 'python3 main.py serve --host 0.0.0.0 --port $PORT'
🚀 Starting OMNI-AGENT Web UI
Uvicorn running on http://0.0.0.0:10000
==> Your service is live 🎉
```

Then open `https://your-app.onrender.com/` → Manus-like chat.

**If you still see logs in start command**: You pasted logs into start command field. Go to Settings → Build & Deploy → Clear Start Command field → Paste exact: `python3 main.py serve --host 0.0.0.0 --port $PORT` → Save → Deploy.

---

## 🎉 After Deploy:

- Web UI: `https://your-app.onrender.com/` - Manus-like chat
- API Docs: `https://your-app.onrender.com/docs`
- Health: `https://your-app.onrender.com/api/health`

Free tier: 750 hrs/month, $0 with free OpenRouter models.
