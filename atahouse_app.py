"""
AtaHouse v2 — Professional Flask app
Features:
- System UI/UX with navigation bar
- Social media downloader categories (YouTube, TikTok, Instagram, Facebook, Twitter/X)
- Thumbnail grabber (shows preview before download)
- About Us, Tips, Contact Us pages
- Admin login (only you: username=atauwu, password=atauwu58$)
- Admin dashboard with download stats (URLs, formats, timestamps)

How to run (CMD + Notepad):
1. Save this as `atahouse_app.py`
2. Create venv: `python -m venv venv` then `venv\Scripts\activate`
3. Install: `pip install flask yt-dlp PyPDF2 pdfminer.six`
4. Run: `python atahouse_app.py`
5. Open browser: http://127.0.0.1:5000
"""

from flask import Flask, request, render_template_string, send_file, redirect, url_for, flash, session
import os, io, uuid, shutil, threading, datetime
from pathlib import Path

try:
    import yt_dlp
except:
    yt_dlp = None

try:
    from PyPDF2 import PdfReader, PdfWriter
except:
    PdfReader = PdfWriter = None

try:
    from pdfminer.high_level import extract_text
except:
    extract_text = None

app = Flask(__name__)
app.secret_key = 'atahouse-secret-2025'
BASE = Path(__file__).parent.resolve()
TMP = BASE / 'tmp'
TMP.mkdir(exist_ok=True)

# simple in-memory stats
DOWNLOAD_LOGS = []

ADMIN_USER = "atauwu"
ADMIN_PASS = "atauwu58$"

NAVBAR = """
<nav style="display:flex;gap:16px;background:#0b6efd;padding:12px;border-radius:0 0 10px 10px">
  <a href="/" style="color:white;text-decoration:none">Home</a>
  <a href="/about" style="color:white;text-decoration:none">About Us</a>
  <a href="/tips" style="color:white;text-decoration:none">Tips</a>
  <a href="/contact" style="color:white;text-decoration:none">Contact</a>
  <a href="/admin" style="color:white;text-decoration:none;margin-left:auto">Admin</a>
</nav>
"""

BASE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f7f9fc;color:#111}
    .container{max-width:960px;margin:20px auto;padding:20px;background:#fff;border-radius:12px;box-shadow:0 4px 14px rgba(0,0,0,0.08)}
    h1,h2,h3{margin-top:0}
    input,select{padding:10px;width:100%;margin-top:6px;border-radius:8px;border:1px solid #ddd}
    button{margin-top:10px;padding:10px 14px;background:#0b6efd;color:white;border:none;border-radius:8px;cursor:pointer}
    .btn{padding:8px 12px;border-radius:8px;text-decoration:none;display:inline-block;margin:4px}
    .yt{background:#ff0000;color:#fff}
    .tt{background:#010101;color:#fff}
    .fb{background:#1877f2;color:#fff}
    .ig{background:#e1306c;color:#fff}
    .tw{background:#1da1f2;color:#fff}
    footer{margin-top:20px;font-size:13px;color:#666;text-align:center}
  </style>
</head>
<body>
  {{ navbar|safe }}
  <div class="container">
    {{ content|safe }}
  </div>
  <footer>© 2025 AtaHouse Downloader + PDF Tools</footer>
</body>
</html>
"""

def render_page(title, content):
    return render_template_string(BASE_HTML, title=title, navbar=NAVBAR, content=content)

def safe_cleanup_tmp():
    for p in TMP.iterdir():
        try:
            if p.is_file(): p.unlink()
            else: shutil.rmtree(p)
        except: pass

@app.route('/')
def home():
    content = """
    <h1>AtaHouse Downloader</h1>
    <p>Choose a platform and paste a link. Get video, audio, or thumbnails fast.</p>
    <div>
      <a class="btn yt" href="/?cat=youtube">YouTube</a>
      <a class="btn tt" href="/?cat=tiktok">TikTok</a>
      <a class="btn fb" href="/?cat=facebook">Facebook</a>
      <a class="btn ig" href="/?cat=instagram">Instagram</a>
      <a class="btn tw" href="/?cat=twitter">Twitter/X</a>
    </div>
    <form method="POST" action="/download" style="margin-top:14px">
      <label>Media URL</label>
      <input type="text" name="media_url" required>
      <label>Format</label>
      <select name="format">
        <option value="best">Best Quality</option>
        <option value="mp4">MP4 Video</option>
        <option value="mp3">MP3 Audio</option>
        <option value="thumb">Thumbnail</option>
      </select>
      <button type="submit">Download</button>
    </form>
    """
    return render_page("AtaHouse Downloader", content)

@app.route('/about')
def about():
    return render_page("About Us", "<h2>About AtaHouse</h2><p>AtaHouse is your one-stop downloader and PDF tool built for speed and simplicity.</p>")

@app.route('/tips')
def tips():
    return render_page("Tips", "<h2>Tips</h2><ul><li>Use valid URLs only.</li><li>For audio, choose MP3.</li><li>Use cleanup often to clear tmp files.</li></ul>")

@app.route('/contact')
def contact():
    return render_page("Contact Us", "<h2>Contact Us</h2><p>Email: admin@atahouse.local</p>")

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('media_url').strip()
    fmt = request.form.get('format')
    if not url:
        flash('No URL provided')
        return redirect(url_for('home'))

    if yt_dlp is None:
        flash('yt_dlp not installed')
        return redirect(url_for('home'))

    task_id = str(uuid.uuid4())
    out_dir = TMP / task_id
    out_dir.mkdir()
    ydl_opts = {'outtmpl': str(out_dir / '%(title).100s.%(ext)s'), 'quiet':True, 'noplaylist':True}

    if fmt == 'mp3':
        ydl_opts.update({'format':'bestaudio/best','postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3'}]})
    elif fmt == 'mp4':
        ydl_opts.update({'format':'mp4'})
    elif fmt == 'thumb':
        ydl_opts.update({'skip_download':True,'writethumbnail':True})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            DOWNLOAD_LOGS.append({'url':url,'fmt':fmt,'time':datetime.datetime.now().isoformat()})
            files = list(out_dir.glob('*'))
            if not files:
                flash('No file produced')
                return redirect(url_for('home'))
            f = max(files, key=lambda x: x.stat().st_size)
            return send_file(f, as_attachment=True)
    except Exception as e:
        flash('Download error: '+str(e))
        return redirect(url_for('home'))

@app.route('/admin', methods=['GET','POST'])
def admin():
    if request.method=='POST':
        u = request.form.get('username'); p = request.form.get('password')
        if u==ADMIN_USER and p==ADMIN_PASS:
            session['admin']=True
            return redirect('/admin')
        flash('Invalid credentials')

    if not session.get('admin'):
        return render_page("Admin Login", "<h2>Login</h2><form method='post'><input name='username'><input type='password' name='password'><button>Login</button></form>")

    rows = "".join(f"<tr><td>{log['url']}</td><td>{log['fmt']}</td><td>{log['time']}</td></tr>" for log in DOWNLOAD_LOGS)
    content = f"<h2>Admin Dashboard</h2><table border=1 cellpadding=5><tr><th>URL</th><th>Format</th><th>Time</th></tr>{rows}</table>"
    return render_page("Admin Dashboard", content)

@app.route('/cleanup', methods=['POST'])
def cleanup():
    safe_cleanup_tmp()
    flash('tmp cleaned')
    return redirect('/')

if __name__=='__main__':
    def cleaner():
        import time
        while True:
            safe_cleanup_tmp(); time.sleep(21600)
    threading.Thread(target=cleaner,daemon=True).start()
    app.run(port=5000,debug=True)
