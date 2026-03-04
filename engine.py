import re
import os
import smtplib
import tempfile
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from groq import Groq
from fpdf import FPDF
from dotenv import load_dotenv

load_dotenv(override=True)
API_KEY      = os.getenv("GROQ_API_KEY")
SENDER       = os.getenv("EMAIL_SENDER")
PWD          = os.getenv("EMAIL_PASSWORD")
SUPADATA_KEY = os.getenv("SUPADATA_API_KEY", None)


def extract_video_id(url):
    match = re.search(r"(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else None


def _fetch_via_supadata(vid_id):
    try:
        resp = requests.get(
            "https://api.supadata.ai/v1/youtube/transcript",
            params={"videoId": vid_id, "text": "true"},
            headers={"x-api-key": SUPADATA_KEY},
            timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("text") or data.get("content")
            if isinstance(text, list):
                text = " ".join(chunk.get("text", "") for chunk in text)
            return str(text).strip() or None
    except Exception as e:
        print("SUPADATA ERROR:", e)
    return None

def _fetch_via_ytt(vid_id):
    ytt = YouTubeTranscriptApi()
    try:
        transcript_list = ytt.list_transcripts(vid_id)
        try:
            transcript = transcript_list.find_transcript(['en'])
        except Exception:
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
            except Exception:
                transcript = next(iter(transcript_list))
        data = transcript.fetch()
        return " ".join([i.text for i in data]).strip() or None
    except (VideoUnavailable, TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception:
        pass

    try:
        data = ytt.get_transcript(vid_id)
        return " ".join([i['text'] for i in data]).strip() or None
    except Exception:
        return None


def fetch_content(url):
    vid_id = extract_video_id(url)
    if not vid_id:
        return None, "Invalid YouTube link."

    if SUPADATA_KEY:
        text = _fetch_via_supadata(vid_id)
        if text:
            return text, None

    text = _fetch_via_ytt(vid_id)
    if text:
        return text, None

    if not SUPADATA_KEY:
        return None, (
            "Could not fetch transcript — YouTube blocks requests from cloud servers. "
            "Add a SUPADATA_API_KEY environment variable (free at supadata.ai) to fix this."
        )

    return None, "Could not retrieve transcript. The video may have captions disabled, be private, or age-restricted."


def get_ai_notes(text):
    try:
        client = Groq(api_key=API_KEY)
        p = f"""Professional notes needed for this transcript. 

Format:
# Summary
Overview.

# Key Points
- Core ideas.

# Detailed Notes
Topic-wise breakdown.

# Action Items
- Next steps.

# Highlights
- Top quotes.

---
{text}"""
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": p}],
            temperature=0.2,
        )
        return resp.choices[0].message.content, None
    except Exception as e:
        return None, str(e)


def create_pdf(notes, url):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "NOTESHA - Notes", ln=True, align="C")
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, f"Source: {url}", ln=True, align="C")
    pdf.ln(5)
    pdf.set_text_color(0, 0, 0)

    for line in notes.split("\n"):
        line = line.strip()
        if not line:
            pdf.ln(3)
        elif line.startswith("# "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, line[2:], ln=True)
        elif line.startswith("- "):
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(5, 6, chr(149))
            pdf.multi_cell(0, 6, " " + line[2:])
        else:
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, line)

    f = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(f.name)
    return f.name


def mail_pdf(to, path):
    try:
        msg = MIMEMultipart()
        msg["From"], msg["To"], msg["Subject"] = SENDER, to, "Your Notes - NOTESHA"
        msg.attach(MIMEText("Hi,\n\nYour notes are attached.\n\nBest,\nNOTESHA", "plain"))
        with open(path, "rb") as f:
            p = MIMEBase("application", "octet-stream")
            p.set_payload(f.read())
            encoders.encode_base64(p)
            p.add_header("Content-Disposition", "attachment; filename=notes.pdf")
            msg.attach(p)
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(SENDER, PWD)
            s.send_message(msg)
        return True, None
    except Exception as e:
        return False, str(e)
