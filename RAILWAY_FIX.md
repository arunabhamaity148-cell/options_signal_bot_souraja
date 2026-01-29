# 🚂 RAILWAY DEPLOYMENT FIX
## Stop "Stopping Container" Issue

---

## ❌ PROBLEM

Railway container stopping after few minutes:
```
Starting Container
Bot started...
Stopping Container  ← THIS
```

---

## ✅ SOLUTION

Railway needs the service to be **EXPOSED** as a web service.

---

## 🔧 FIX STEPS

### Step 1: Railway Settings

1. Go to Railway Dashboard
2. Select your project: `options_signal_bot_souraja`
3. Click **Settings** tab
4. Find **"Service Type"** or **"Networking"**
5. Change to: **"Web Service"** or **"Public"**
6. Click **"Generate Domain"**

**OR:**

1. Click **Settings**
2. Scroll to **"Deploy"**
3. Under **"Service"** change from:
   - ❌ `Private` or `None`
   - ✅ `Public` or `Exposed`

### Step 2: Redeploy

After changing settings:
```
Deployments → Latest → Click ⋮ → Redeploy
```

---

## 📊 RAILWAY SETTINGS (Complete)

### Service Configuration:

```
Service Type: Web Service
Port: 8080 (auto-detected from code)
Health Check Path: /health
Start Command: python main.py
```

### Environment Variables:

```
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional (if using Shoonya)
SHOONYA_USER_ID=your_id
SHOONYA_PASSWORD=your_pass
SHOONYA_TOTP_KEY=your_totp
```

### Networking:

```
✅ Public Networking: ENABLED
✅ Generate Domain: YES
```

---

## 🎯 WHY THIS WORKS

### Before Fix:
```
Railway: "No HTTP service detected"
Railway: "Container idle, stopping..."
❌ Stops after 5 minutes
```

### After Fix:
```
Railway: "Web service detected on port 8080"
Railway: "Ping /health → OK"
Railway: "Container healthy"
✅ Runs 24/7
```

---

## 🔍 VERIFY IT'S WORKING

After redeploy, check:

### 1. Railway Logs:
```
✓ HTTP server started on port 8080
Bot is live - Monitoring markets...
(No "Stopping Container")
```

### 2. Public URL:
Railway will give you a URL like:
```
https://options-signal-bot-production-xxxx.up.railway.app
```

Visit it → Should show:
```
🤖 Options Signal Bot
Status: RUNNING ✅
```

### 3. Health Check:
```
https://your-url.railway.app/health
```

Should return: `OK - Bot is running`

---

## 🆘 IF STILL STOPPING

### Check 1: Memory Limit
Railway free plan: 512 MB RAM

**Fix:**
```python
# In main.py, reduce scan frequency
DATA_REFRESH_INTERVAL = 120  # 2 minutes instead of 60 seconds
```

### Check 2: Crash Loop
**Look for errors in logs:**
```
Traceback...
ModuleNotFoundError...
```

**Fix:** Install missing dependency in requirements.txt

### Check 3: Health Check Failing
**Test locally first:**
```bash
python main.py
# Then visit: http://localhost:8080/health
```

If local works but Railway doesn't → Railway networking issue

---

## 📋 COMPLETE RAILWAY CHECKLIST

Before deploying:

- [ ] `railway.json` file added to project root
- [ ] Service Type: **Web Service**
- [ ] Public Networking: **ENABLED**
- [ ] Domain generated
- [ ] Environment variables set (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- [ ] `main.py` has HTTP server code
- [ ] `requirements.txt` is updated
- [ ] Port 8080 is used in code
- [ ] `/health` endpoint exists

After deploying:

- [ ] No "Stopping Container" in logs
- [ ] Public URL accessible
- [ ] `/health` returns OK
- [ ] Telegram test message received
- [ ] Bot stays running for 10+ minutes

---

## 🎓 RAILWAY FREE PLAN LIMITS

Be aware:

| Resource | Limit | Our Usage |
|----------|-------|-----------|
| **RAM** | 512 MB | ~100-150 MB ✅ |
| **CPU** | Shared | <5% ✅ |
| **Build Time** | 5 min | ~2 min ✅ |
| **Execution Time** | Unlimited | 24/7 ✅ |
| **Network** | Limited egress | Low ✅ |

**Verdict:** Bot fits perfectly in free plan! 🎉

---

## 🔄 ALTERNATIVE: REPLIT (If Railway Fails)

If Railway keeps stopping, use Replit:

1. Go to https://replit.com
2. Create new Repl → Import from GitHub
3. Add `.replit` file:
   ```toml
   run = "python main.py"
   ```
4. Add secrets (env vars)
5. Click Run
6. Enable "Always On" (if paid plan)

---

## 🚀 RECOMMENDED: RUN ON LOCAL PC

**Most reliable option:**

✅ No stopping
✅ No limits
✅ Full control
✅ Better logs
✅ Faster debugging

**Only need:**
- PC that can stay on during trading hours (9 AM - 3:30 PM)
- Stable internet
- Windows/Mac/Linux

**See:** `LOCAL_SETUP.md` for complete guide

---

## 📞 RAILWAY SUPPORT

If nothing works:

1. Railway Discord: https://discord.gg/railway
2. Railway Docs: https://docs.railway.app
3. Create GitHub issue with logs

---

**TL;DR:**
1. Railway Settings → Service Type → **Web Service**
2. Enable **Public Networking**
3. Generate **Domain**
4. **Redeploy**
5. Done! ✅
