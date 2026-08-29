# The AI Loophole — AI YouTube Automation Pipeline (Final Rebuild)

100% free (zero billing/card anywhere), GitHub Actions–powered pipeline
that researches, scripts, voices, edits, and publishes AI-tool review
videos (Shorts + Long-form) — fully automated, self-improving over time.

---

## Architecture Overview

```
├── .github/workflows/
│   ├── shorts_pipeline.yml       # daily, 2x/day
│   ├── longform_pipeline.yml     # 2x/week
│   └── analytics_review.yml      # weekly, Sundays
├── core/
│   ├── state_manager.py          # job tracking, resume, cross-promo lookup
│   ├── fallback.py               # 3-tier try/except chain
│   ├── quality_gate.py           # source-tier + self-score publish gate
│   └── pipeline_runner.py        # main orchestrator — defines the contract
├── modules/
│   ├── research.py               # Trends -> Reddit -> autocomplete + gap-finding
│   ├── scripting.py              # Groq gpt-oss-120b -> Mistral Large -> Groq llama
│   ├── audio.py                  # Piper (local) -> Edge-TTS -> ElevenLabs
│   ├── visuals.py                # Pexels -> Pixabay -> Pollinations + music
│   ├── sound_library.py          # Freesound CC0-only SFX/music discovery
│   ├── sound_design.py           # SFX cue placement
│   ├── captions.py               # Whisper word/chunk timestamps
│   ├── assembly.py               # Remotion bridge (renders final MP4)
│   ├── thumbnail.py              # Pillow-based, 3-expression thumbnails
│   ├── upload.py                 # YouTube Data API v3 publish
│   ├── topic_selector.py         # topic pool + competitive intelligence
│   └── analytics.py              # weekly feedback loop, includes old videos
├── remotion/                     # Node.js/React motion graphics engine
│   └── src/
│       ├── Root.jsx
│       ├── compositions/{ShortsVideo,LongformVideo}.jsx
│       └── components/{KenBurnsClip,KineticCaption,SubtitleCaption,SfxLayer}.jsx
├── pipeline_state/                # job_state.json, published_log.json (committed)
├── assets/                        # binaries — cached only, never committed
├── fonts/, requirements.txt, orchestrator_shorts.py, orchestrator_longform.py
```

## Why these specific choices

- **No Google Gemini**: model names/SDK changed multiple times this year —
  unreliable for unattended automation. Groq + Mistral are stable.
- **No Google Cloud TTS**: requires a billing account/card even for free
  tier. Piper (local, MIT license) needs neither.
- **Remotion instead of MoviePy**: real motion graphics (Ken Burns,
  kinetic captions) instead of static crossfades.
- **Freesound (CC0 only)**: automated, zero-attribution-required SFX/music
  discovery — no manual downloading.

---

## Setup (assumes you already have a GitHub repo, YouTube channel, and
## most API keys from earlier setup — this is the final, complete list)

### 1. GitHub Secrets — complete list

| Secret | Required? | Source |
|---|---|---|
| `GROQ_API_KEY` | Yes | console.groq.com/keys |
| `MISTRAL_API_KEY` | Yes | console.mistral.ai (free "Experiment" tier) |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | Yes | reddit.com/prefs/apps |
| `PEXELS_API_KEY` | Yes | pexels.com/api |
| `PIXABAY_API_KEY` | Yes | pixabay.com/api/docs |
| `FREESOUND_API_KEY` | Yes | freesound.org/apiv2/apply |
| `ELEVENLABS_API_KEY` | Optional | elevenlabs.io |
| `YT_CLIENT_ID` / `YT_CLIENT_SECRET` | Yes | Google Cloud Console → Credentials |
| `YT_REFRESH_TOKEN` | Yes | see below — must include analytics scope |

No `GEMINI_API_KEY` or `GOOGLE_TTS_API_KEY` needed — remove them if present.

### 2. Google Cloud — 2 APIs only

Enable in your existing Google Cloud project: **YouTube Data API v3** and
**YouTube Analytics API**.

### 3. Refresh token (must include analytics scope)

```bash
pip install google-auth-oauthlib
```
```python
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_config(
    {"installed": {
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }},
    scopes=[
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ]
)
creds = flow.run_local_server(port=0)
print("REFRESH TOKEN:", creds.refresh_token)
```

### 4. Fonts (place in /fonts)
`Montserrat-Bold.ttf`, `Montserrat-Black.ttf`, `Roboto-Regular.ttf` from fonts.google.com

### 5. Node.js / Remotion
No manual setup — workflows install Node.js and run `npm install` automatically.

### 6. First test run
Actions tab → Shorts Pipeline → Run workflow. Watch the log for the
first run or two before trusting the schedule.

---

## How the growth features work

- **Cross-promotion**: Shorts automatically reference the latest public
  long-form video by its real title (no setup needed).
- **Quality gate**: videos built from weak fallback sources, or that
  score low on an LLM self-critique, publish `unlisted` instead of
  `public` — check `pipeline_state/job_state.json` for `needs_manual_review`.
- **Analytics feedback loop**: runs weekly, includes your channel's full
  upload history (even videos made before this pipeline existed), and
  feeds patterns back into future scripts. Needs ~10 videos with data
  before it produces anything (`performance_insights.json` will say
  `"insufficient_data"` until then).

## Monitoring
- `pipeline_state/job_state.json` — current/paused job status
- `pipeline_state/published_log.json` — full publish history
- Both are plain JSON, viewable directly on GitHub
