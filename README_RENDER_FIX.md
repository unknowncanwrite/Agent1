# 🔧 Render Deploy - All Errors Fixed

## Error 1: Erlang
```
Using Erlang version 28.0.2
mix phx.digest - Build failed
```
**Fix**: Select Runtime: Python 3 (not Elixir)

## Error 2: python: command not found
```
bash: python: command not found
No open ports
```
**Fix**: Use `python3` not `python`

## Error 3: dotenv not found (Current)
```
Running build command 'python main.py serve...'
ModuleNotFoundError: No module named 'dotenv'
Build failed
```
**Fix**: Build Command WRONG - you set Build to Start command.

### Correct Settings:

**Build Command** (installs deps - runs FIRST):
```
pip install -r requirements.txt
```

**Start Command** (starts server - runs AFTER build):
```
python3 main.py serve --host 0.0.0.0 --port $PORT
```

**Runtime**: Python 3
**Branch**: arena/01a0a65b-agent1
**Env**: OPENROUTER_API_KEY, PYTHON_VERSION=3.11.11

### Easiest: Use Blueprint

1. New → Blueprint → Connect repo → Branch arena/01a0a65b-agent1
2. Add OPENROUTER_API_KEY
3. Deploy - render.yaml has correct build/start auto

### Docker (Always Works)

1. New → Web Service → Runtime: Docker
2. Dockerfile: ./Dockerfile
3. Env: OPENROUTER_API_KEY
4. Deploy

See DEPLOY.md for full guide.
