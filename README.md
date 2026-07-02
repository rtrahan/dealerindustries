# Dealer Industries

Advisor performance PDF reporting tool. Upload Tekion, Dynatron, or CDK report files and generate consolidated PDFs.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional — only needed for CDK Photos (Gemini)
./run.sh
```

Open http://127.0.0.1:8000

## Deploy on Vercel

This project uses [Vercel's zero-config FastAPI support](https://vercel.com/docs/frameworks/backend/fastapi). The entrypoint is `app/main.py`.

### Setup

1. Import the repo at [github.com/rtrahan/dealerindustries](https://github.com/rtrahan/dealerindustries) in the [Vercel dashboard](https://vercel.com/new).
2. Leave the **Root Directory** as `.` (project root).
3. Vercel will auto-detect FastAPI from `requirements.txt` / `pyproject.toml`.
4. Add environment variables (Project Settings → Environment Variables):

| Variable | Required | Notes |
|----------|----------|-------|
| `GEMINI_API_KEY` | Only for CDK Photos | Get a key from [Google AI Studio](https://aistudio.google.com/apikey) |
| `GEMINI_MODEL` | No | Defaults to `gemini-2.5-flash` |
| `GEMINI_MAX_WORKERS` | No | Defaults to `6` |

5. Deploy.

### Report modes

| Mode | Works on Vercel | Notes |
|------|-----------------|-------|
| **Tekion** | Yes | Excel + CSV uploads |
| **Dynatron** | Yes | Op Code Analysis `.xlsx` + RAP `.csv` |
| **CDK Photos** | Yes* | Requires `GEMINI_API_KEY`; photos are auto-compressed to fit Vercel's 4 MB upload limit |

\* PDF generation is configured for up to 60 seconds (`vercel.json`). Hobby plans cap at 10s — upgrade to Pro if reports time out.

### CLI deploy (optional)

```bash
npm i -g vercel   # or: brew install vercel-cli
vercel login
vercel --prod
```
