# ToolVerdict — AI YouTube Automation Pipeline

100% free, GitHub Actions–powered pipeline that researches, scripts, voices,
edits, and publishes AI-tool review videos (Shorts + Long-form) for a
Western (US/UK) audience — fully automated after setup.

---

## 📁 Project Structure

```
├── .github/workflows/
│   ├── shorts_pipeline.yml       # daily, 2x/day trigger
│   └── longform_pipeline.yml     # 2x/week trigger
├── core/
│   ├── state_manager.py          # job_state.json / resume logic
│   ├── fallback.py                # 3-tier try/except chain
│   └── pipeline_runner.py         # main orchestrator
├── modules/
│   ├── research.py                # Trends -> Reddit -> autocomplete
│   ├── scripting.py               # Gemini -> Groq
│   ├── audio.py                   # Edge-TTS -> ElevenLabs -> Google TTS
│   ├── visuals.py                 # Pexels -> Pixabay -> Pollinations
│   ├── captions.py                # Whisper + Pillow (no ImageMagick)
│   ├── assembly.py                # MoviePy final render
│   ├── upload.py                  # YouTube Data API v3
│   └── topic_selector.py          # picks next AI tool to cover
├── pipeline_state/                # job_state.json, published_log.json (committed)
├── assets/                        # binaries — cached only, never committed
├── fonts/                         # put .ttf files here
├── orchestrator_shorts.py
├── orchestrator_longform.py
└── requirements.txt
```

---

## 🚀 Setup Guide (Step-by-Step)

### Step 1 — Create the GitHub repo
1. Go to https://github.com/new
2. Name it (e.g. `toolverdict-pipeline`), set to **Public** (unlimited free Actions minutes)
3. Upload this entire project folder to the repo (drag-and-drop on github.com works, or `git push` if you're comfortable with git)

### Step 2 — Create the YouTube channel
1. Go to https://youtube.com, sign in with a Google account (create a fresh one if you want it separate from your personal account)
2. Click your profile icon → **Create a channel**
3. Name it (e.g. "ToolVerdict"), add a simple logo/banner (Canva free tier)

### Step 3 — Google Cloud Project + YouTube Data API
1. Go to https://console.cloud.google.com/
2. Create a new project (e.g. "toolverdict-automation")
3. Go to **APIs & Services → Library**, search "YouTube Data API v3", click **Enable**
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Download the JSON — this gives you `client_id` and `client_secret`
5. Go to **OAuth consent screen** → set to "External" → add your own Google account as a **Test User** (this avoids Google's app-verification review since it's just for you)

### Step 4 — Generate your YouTube Refresh Token (one-time, local step)
This is the only step that needs to run on your own computer once:
```bash
pip install google-auth-oauthlib
python -c "
from google_auth_oauthlib.flow import InstalledAppFlow
flow = InstalledAppFlow.from_client_config(
    {'installed': {
        'client_id': 'YOUR_CLIENT_ID',
        'client_secret': 'YOUR_CLIENT_SECRET',
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
    }},
    scopes=['https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/youtube']
)
creds = flow.run_local_server(port=0)
print('REFRESH TOKEN:', creds.refresh_token)
"
```
A browser window opens → log in with the SAME Google account as your YouTube channel → approve → copy the printed refresh token.

### Step 5 — Reddit API (free developer app)
1. Go to https://www.reddit.com/prefs/apps
2. Click **create another app...** at the bottom
3. Type: **script**, redirect URI: `http://localhost:8080`
4. After creating, note the string under the app name (that's `client_id`) and the "secret" field (`client_secret`)

### Step 6 — Free API keys for the rest of the stack
| Service | Where to get it | Free tier |
|---|---|---|
| Gemini | https://aistudio.google.com/apikey | Generous free tier |
| Groq | https://console.groq.com/keys | Free, very fast |
| Pexels | https://www.pexels.com/api/ | Free, unlimited |
| Pixabay | https://pixabay.com/api/docs/ | Free, unlimited |
| ElevenLabs (optional fallback) | https://elevenlabs.io/ | 10 min/month free |
| Google Cloud TTS (optional fallback) | Same Google Cloud project as Step 3, enable "Cloud Text-to-Speech API" | Free tier |

### Step 7 — Add everything as GitHub Secrets
In your repo: **Settings → Secrets and variables → Actions → New repository secret**. Add each of these:
```
GEMINI_API_KEY
GROQ_API_KEY
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
ELEVENLABS_API_KEY       (optional, can leave blank)
GOOGLE_TTS_API_KEY       (optional, can leave blank)
PEXELS_API_KEY
PIXABAY_API_KEY
YT_CLIENT_ID
YT_CLIENT_SECRET
YT_REFRESH_TOKEN
```

### Step 8 — Add fonts and music (required, one-time)
- Download **Montserrat-Bold.ttf** and **Roboto-Regular.ttf** free from https://fonts.google.com and place them in `/fonts`
- Download 3-5 royalty-free tracks from **Pixabay Audio** (https://pixabay.com/music/) — pick ones explicitly marked free for commercial use — place them in `/assets/music/` and update the file paths in `modules/visuals.py` → `SAFE_MUSIC_LIBRARY`

### Step 9 — Turn it on
Go to the **Actions** tab in your repo → you'll see both workflows listed → they'll now run automatically on schedule. You can also click **Run workflow** to trigger one manually and test the whole pipeline end-to-end.

---

## ⚠️ Before your first real run
Trigger one workflow manually (`workflow_dispatch`) and **watch the Actions log** closely for the first 2-3 runs. This catches API key typos, quota issues, or format errors before they burn through your free-tier credits repeatedly.

## 🔍 Monitoring
- `pipeline_state/job_state.json` — current/paused job status
- `pipeline_state/published_log.json` — full history of what's been published
- Both are plain JSON, viewable directly on GitHub without any extra tooling
