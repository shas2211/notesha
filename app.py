from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import engine
import os
import tempfile

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided."}), 400

    text, err = engine.fetch_content(url)
    if err:
        return jsonify({"error": err}), 400

    notes, err = engine.get_ai_notes(text)
    if err:
        return jsonify({"error": err}), 500

    return jsonify({"notes": notes})

@app.route("/send-email", methods=["POST"])
def send_email():
    data = request.get_json()
    notes = data.get("notes", "")
    url   = data.get("url", "")
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"error": "No email provided."}), 400

    path = engine.create_pdf(notes, url)

    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        return response

    ok, err = engine.mail_pdf(email, path)
    if not ok:
        return jsonify({"error": err}), 500

    return jsonify({"success": True})

@app.route("/download-pdf", methods=["POST"])
def download_pdf():
    data  = request.get_json()
    notes = data.get("notes", "")
    url   = data.get("url", "")
    path  = engine.create_pdf(notes, url)

    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        return response

    return send_file(path, as_attachment=True, download_name="notesha-notes.pdf", mimetype="application/pdf")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
