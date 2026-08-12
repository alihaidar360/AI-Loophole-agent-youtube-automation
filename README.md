# ToolVerdict — AI YouTube Automation Pipeline (v2)

100% free, GitHub Actions–powered pipeline producing both Shorts and
Long-form AI-tool review videos with a researcher persona, Remotion-based
motion graphics, sound design, and expressive thumbnails — fully automated.

## What's new in v2
- **Researcher-persona scripts** — first-person, hands-on-verdict structure,
  10-13 min long-form / 45-60 sec Shorts, both independently tuned
- **Remotion motion graphics** (Node.js/React) — Ken Burns zoom, kinetic
  captions (Shorts) / standard subtitles (Long-form), replacing the old
  static-crossfade renderer
- **Sound design layer** — whoosh/impact/riser/click cues on cuts and
  chapter transitions
- **New voice priority**: Piper TTS (local, offline, zero setup) →
  Edge-TTS (zero setup) → ElevenLabs (optional). No billing account or
  credit card required anywhere in the voice pipeline.
- **Expressive thumbnails/covers** — a consistent illustrated character
  with 3 expressions (excited/skeptical/neutral) driven by the video's
  verdict, plus a short psychological headline (not the raw tool name)

## Project Structure
```
├── .github/workflows/
│   ├── shorts_pipeline.yml
│   └── longform_pipeline.yml
├── core/
│   ├── state_manager.py
│   ├── fallback.py
│   └── pipeline_runner.py
├── modules/
│   ├── research.py       research.py    Trends -> Reddit -> autocomplete
│   ├── scripting.py      Gemini -> Groq, researcher persona
│   ├── audio.py          Google TTS -> ElevenLabs -> Edge-TTS
│   ├── visuals.py        Pexels -> Pixabay -> Pollinations, per-chapter
│   ├── sound_design.py   SFX cue placement
│   ├── captions.py       Whisper word timestamps -> kinetic/subtitle data
│   ├── assembly.py       Builds Remotion props, renders via Remotion CLI
│   ├── thumbnail.py      Pillow-based expressive character thumbnails
│   ├── upload.py         YouTube Data API v3
│   └── topic_selector.py
├── remotion/              Node.js/React motion graphics engine
│   ├── package.json
│   └── src/
│       ├── Root.jsx              registers both Compositions
│       ├── compositions/
│       │   ├── ShortsVideo.jsx
│       │   └── LongformVideo.jsx
│       └── components/
│           ├── KenBurnsClip.jsx
│           ├── KineticCaption.jsx
│           ├── SubtitleCaption.jsx
│           └── SfxLayer.jsx
├── pipeline_state/        job_state.json, published_log.json (committed)
├── assets/                binaries — cached only, never committed
├── fonts/, assets/music/, assets/sfx/   see each folder's README.txt
├── orchestrator_shorts.py
├── orchestrator_longform.py
└── requirements.txt
```

## Setup (only what's NEW vs the v1 guide — follow the original A-Z guide
## for GitHub/YouTube/Reddit/Gemini/Groq/Pexels/Pixabay account setup first)

### 1. Voice — zero setup needed (no billing, ever)
Primary voice is now **Piper TTS**, which runs locally on the GitHub
Actions runner — no account, no API key, no credit card. The voice
model (~60MB) downloads automatically from a public Hugging Face
repository on first run and is cached by the existing `assets/` cache
step, so it won't re-download every time. Nothing to configure.

(Earlier versions of this guide used Google Cloud TTS, which requires a
billing account/card on file even to stay within its free tier. That
step has been removed — Piper replaces it with an equal-or-better result
and zero payment info anywhere in the system.)

### 2. Fonts — 3 files now needed (was 2)
Download from fonts.google.com: `Montserrat-Bold.ttf`, `Montserrat-Black.ttf`
(the Black weight specifically), `Roboto-Regular.ttf` → upload to `/fonts`

### 3. Sound effects (new)
Download 5 short, license-free SFX from Pixabay Sound Effects or Mixkit,
name them exactly as listed in `/assets/sfx/README.txt`, upload there.

### 4. Node.js — no action needed
The GitHub Actions workflows now include a Node.js setup + `npm ci` step
automatically. Nothing to install locally unless you want to preview
Remotion compositions on your own machine (`cd remotion && npx remotion studio`).

### 5. ElevenLabs voice ID (optional, only if you want to change it)
Default is "Adam" (`pNInz6obpgDQGcFmaJgB`). To use a different voice,
grab its ID from your ElevenLabs dashboard and update
`Config.ELEVENLABS_VOICE_ID` in `config.py`.

### 6. Growth features (new): cross-promotion, quality gate, analytics loop

These three are why the channel should actually improve over time instead
of producing the same quality video forever:

- **Cross-promotion** (Shorts → Long-form) and **quality gate** (weak
  videos publish unlisted instead of public) need NO extra setup — they
  work automatically using data already in `pipeline_state/`.

- **Analytics feedback loop** needs one extra OAuth scope. Redo the
  refresh-token step from the original guide (Step 3.5), but add the
  analytics scope to the `scopes` list:
  ```python
  scopes=["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube",
          "https://www.googleapis.com/auth/yt-analytics.readonly"]
  ```
  Replace the `YT_REFRESH_TOKEN` GitHub Secret with the new token this
  produces (old one won't have analytics access).

  This also adds a **new weekly workflow** (`analytics_review.yml`,
  runs Sundays) — nothing to configure, it uses the same YouTube secrets.
  It won't produce useful insights until at least ~10 videos are
  published; until then `performance_insights.json` just says
  `"insufficient_data"` and scripting.py silently skips using it.

## Everything else
Follow the original A-Z setup roadmap (GitHub repo, YouTube channel,
Google Cloud OAuth + refresh token, Reddit app, Gemini/Groq/Pexels/Pixabay
keys, GitHub Secrets) exactly as before — only the additions above are new.

## First test run
Trigger either workflow manually from the Actions tab. Watch the log —
the Remotion render step is the most likely first-run failure point
(missing SFX/font files, or `npm ci` issues) since it's entirely new.
