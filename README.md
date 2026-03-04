# NOTESHA — Flask Edition

YouTube → structured notes, email as PDF.

## Deploy to Render

1. Push this folder to a GitHub repo
2. Go to render.com → New → Web Service → connect your repo
3. Settings:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
   - **Environment:** Python 3
4. Add Environment Variables:
   - `GROQ_API_KEY`
   - `EMAIL_SENDER`
   - `EMAIL_PASSWORD` (Gmail App Password)
   - `SUPADATA_API_KEY` ← optional but recommended (free at supadata.ai)

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python app.py
```

## Notes on the transcript issue

YouTube blocks transcript requests from cloud server IPs (AWS/GCP).
- **With SUPADATA_API_KEY set:** uses Supadata as primary (always works)
- **Without it:** falls back to youtube-transcript-api directly (works locally, may fail on Render)
