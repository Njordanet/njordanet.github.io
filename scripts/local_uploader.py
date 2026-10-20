#!/usr/bin/env python3
"""
scripts/local_uploader.py - Clean local web uploader for njorda.net gallery
Run: python3 scripts/local_uploader.py
Open: http://localhost:8765
"""

import os
import sys
import json
import cgi
import tempfile
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Import add_photo logic from scripts/add_photo.py
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import add_photo as ap

PORT = 8765

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
  <title>Gallery Uploader // njorda.net</title>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="stylesheet" href="/njorda.css">
  <style>
    .upload-box {
      border: 2px dashed var(--border-focus);
      background-color: var(--bg-subtle);
      border-radius: 14px;
      padding: 32px 20px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s ease;
      margin-bottom: 20px;
    }
    .upload-box:hover, .upload-box.dragover {
      border-color: var(--accent-olive-hover);
      background-color: rgba(78, 99, 57, 0.12);
    }
    .upload-icon {
      font-size: 38px;
      margin-bottom: 8px;
      display: block;
    }
    .form-group {
      margin-bottom: 16px;
    }
    .form-group label {
      display: block;
      font-weight: 700;
      margin-bottom: 6px;
      font-family: var(--font-heading);
      color: var(--text-main);
    }
    .form-control {
      width: 100%;
      padding: 10px 14px;
      font-family: var(--font-typewriter);
      font-size: 14px;
      border: 1px solid var(--border-soft);
      border-radius: 8px;
      background: var(--bg-card);
      color: var(--text-main);
      box-sizing: border-box;
    }
    .form-control:focus {
      outline: none;
      border-color: var(--accent-olive);
      box-shadow: 0 0 0 2px rgba(78, 99, 57, 0.2);
    }
    textarea.form-control {
      resize: vertical;
      min-height: 80px;
    }
    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    @media (max-width: 600px) {
      .grid-2 { grid-template-columns: 1fr; }
    }
    .preview-box {
      display: none;
      margin-bottom: 20px;
      text-align: center;
    }
    .preview-box img {
      max-width: 100%;
      max-height: 320px;
      border-radius: 12px;
      border: 1px solid var(--border-soft);
      box-shadow: var(--card-shadow);
    }
    .btn {
      display: inline-block;
      width: 100%;
      padding: 14px 20px;
      font-family: var(--font-heading);
      font-size: 16px;
      font-weight: 700;
      background: var(--accent-olive);
      color: #fff;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      transition: background 0.2s ease, transform 0.1s ease;
    }
    .btn:hover {
      background: var(--accent-olive-hover);
      transform: translateY(-1px);
    }
    .checkbox-group {
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 18px 0;
      font-size: 14px;
    }
    .status-msg {
      padding: 14px 18px;
      border-radius: 10px;
      margin-bottom: 20px;
      display: none;
      font-weight: 700;
    }
    .status-success {
      background: #D8EAD2;
      color: #264A1B;
      border: 1px solid #B0D6A3;
    }
    .status-error {
      background: #F8D7DA;
      color: #721C24;
      border: 1px solid #F5C6CB;
    }
  </style>
</head>
<body>

  <div class="page">
    <div class="box">
      <div class="box-header">
        <div class="header-title flicker">njorda.net</div>
        <div class="tagline">
          <i>local.uploader // photo.intake</i>
        </div>
      </div>
    </div>

    <nav>
      <a href="/index.html" target="_blank">home ↗</a>
      <a href="/gallery.html" target="_blank">view live gallery ↗</a>
    </nav>

    <div id="statusAlert" class="status-msg"></div>

    <div class="box">
      <div class="box-header">
        <h2>Upload New Photo</h2>
      </div>
      <div class="box-body">
        <form id="uploadForm" enctype="multipart/form-data">
          
          <div class="upload-box" id="dropArea">
            <span class="upload-icon">📷</span>
            <b>Click or drag &amp; drop photo here</b>
            <p style="margin: 6px 0 0; font-size: 12px; color: var(--text-muted);">
              JPG, PNG, TIFF, or WebP. Camera EXIF data is auto-detected.
            </p>
            <input type="file" id="fileInput" name="photo" accept="image/*" style="display: none;" required>
          </div>

          <div class="preview-box" id="previewArea">
            <img id="previewImg" src="" alt="Preview">
          </div>

          <div class="form-group">
            <label for="title">Title *</label>
            <input type="text" id="title" name="title" class="form-control" placeholder="e.g. Alpine Autumn Pines" required>
          </div>

          <div class="form-group">
            <label for="caption">Caption</label>
            <textarea id="caption" name="caption" class="form-control" placeholder="A short story or notes about this shot..."></textarea>
          </div>

          <div class="grid-2">
            <div class="form-group">
              <label for="location">Location</label>
              <input type="text" id="location" name="location" class="form-control" placeholder="e.g. Pyrenees, Spain">
            </div>
            <div class="form-group">
              <label for="date">Date Taken</label>
              <input type="text" id="date" name="date" class="form-control" placeholder="YYYY-MM-DD (auto-read if available)">
            </div>
          </div>

          <div class="grid-2">
            <div class="form-group">
              <label for="camera">Camera</label>
              <input type="text" id="camera" name="camera" class="form-control" placeholder="Fujifilm X-T30 II">
            </div>
            <div class="form-group">
              <label for="lens">Lens</label>
              <input type="text" id="lens" name="lens" class="form-control" placeholder="e.g. XF 18-55mm f/2.8-4">
            </div>
          </div>

          <div class="form-group">
            <label for="settings">Exposure Settings</label>
            <input type="text" id="settings" name="settings" class="form-control" placeholder="e.g. 35mm • ƒ/5.6 • 1/250s • ISO 160">
          </div>

          <div class="checkbox-group">
            <input type="checkbox" id="pushGit" name="push" value="true" checked>
            <label for="pushGit" style="margin: 0; cursor: pointer;">
              <b>Push directly to GitHub</b> (runs git add, commit &amp; push)
            </label>
          </div>

          <button type="submit" id="submitBtn" class="btn">Process &amp; Publish Photo</button>
        </form>
      </div>
    </div>

    <div class="footer">
      njorda.net &bull; local gallery ingest utility
    </div>
  </div>

  <script>
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('fileInput');
    const previewArea = document.getElementById('previewArea');
    const previewImg = document.getElementById('previewImg');
    const titleInput = document.getElementById('title');
    const form = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitBtn');
    const statusAlert = document.getElementById('statusAlert');

    dropArea.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(name => {
      dropArea.addEventListener(name, (e) => {
        e.preventDefault();
        dropArea.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      dropArea.addEventListener(name, (e) => {
        e.preventDefault();
        dropArea.classList.remove('dragover');
      });
    });

    dropArea.addEventListener('drop', (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        handleFileSelect();
      }
    });

    fileInput.addEventListener('change', handleFileSelect);

    function handleFileSelect() {
      const file = fileInput.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (e) => {
        previewImg.src = e.target.result;
        previewArea.style.display = 'block';
        if (!titleInput.value) {
          const rawName = file.name.replace(/\\.[^/.]+$/, "").replace(/[-_]/g, " ");
          titleInput.value = rawName.charAt(0).toUpperCase() + rawName.slice(1);
        }
      };
      reader.readAsDataURL(file);
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!fileInput.files[0]) {
        alert('Please choose a photo first!');
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Processing, optimizing & publishing...';
      statusAlert.style.display = 'none';

      const formData = new FormData(form);
      try {
        const res = await fetch('/api/upload', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (data.success) {
          statusAlert.className = 'status-msg status-success';
          statusAlert.innerHTML = '🎉 Success! Photo "' + data.title + '" has been added and published. <a href="/gallery.html" target="_blank">View Live Gallery &rarr;</a>';
          statusAlert.style.display = 'block';
          form.reset();
          previewArea.style.display = 'none';
        } else {
          statusAlert.className = 'status-msg status-error';
          statusAlert.textContent = '❌ Error: ' + (data.error || 'Failed to process photo.');
          statusAlert.style.display = 'block';
        }
      } catch (err) {
        statusAlert.className = 'status-msg status-error';
        statusAlert.textContent = '❌ Network error: ' + err.message;
        statusAlert.style.display = 'block';
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Process & Publish Photo';
      }
    });
  </script>
</body>
</html>
"""


class GalleryHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path

        if path in ("/", "/upload", "/uploader"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        # Serve static site files (CSS, images, gallery.html)
        file_path = REPO_ROOT / path.lstrip("/")
        if file_path.is_file():
            content_type = "text/plain"
            if file_path.suffix == ".html":
                content_type = "text/html; charset=utf-8"
            elif file_path.suffix == ".css":
                content_type = "text/css"
            elif file_path.suffix in (".jpg", ".jpeg"):
                content_type = "image/jpeg"
            elif file_path.suffix == ".png":
                content_type = "image/png"
            elif file_path.suffix == ".webp":
                content_type = "image/webp"
            elif file_path.suffix == ".json":
                content_type = "application/json"

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/upload":
            content_type = self.headers.get("Content-Type")
            if not content_type or "multipart/form-data" not in content_type:
                self.send_json({"success": False, "error": "Invalid form submission"})
                return

            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type}
            )

            file_item = form["photo"] if "photo" in form else None
            if not file_item or not file_item.file:
                self.send_json({"success": False, "error": "No image file provided"})
                return

            title = form.getvalue("title", "").strip()
            caption = form.getvalue("caption", "").strip()
            location = form.getvalue("location", "").strip()
            date = form.getvalue("date", "").strip()
            camera = form.getvalue("camera", "").strip()
            lens = form.getvalue("lens", "").strip()
            settings = form.getvalue("settings", "").strip()
            push = form.getvalue("push") in ("true", "1", "on")

            # Save uploaded temp file
            suffix = Path(file_item.filename).suffix or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_item.file.read())
                tmp_path = Path(tmp.name)

            try:
                success = ap.add_photo(
                    tmp_path,
                    title=title,
                    caption=caption,
                    date=date,
                    location=location,
                    camera=camera,
                    lens=lens,
                    settings=settings,
                    push=push
                )
                if success:
                    self.send_json({"success": True, "title": title})
                else:
                    self.send_json({"success": False, "error": "Failed to add photo."})
            except Exception as e:
                self.send_json({"success": False, "error": str(e)})
            finally:
                if tmp_path.exists():
                    tmp_path.unlink()
            return

        self.send_response(404)
        self.end_headers()

    def send_json(self, data: dict):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))


def main():
    server = HTTPServer(("127.0.0.1", PORT), GalleryHandler)
    url = f"http://localhost:{PORT}"
    print(f"======================================================")
    print(f"  njorda.net Gallery Local Uploader running at:")
    print(f"  👉  {url}")
    print(f"  Press Ctrl+C to stop the server.")
    print(f"======================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping uploader server.")
        server.server_close()


if __name__ == "__main__":
    main()
