#!/usr/bin/env python3
"""
scripts/add_photo.py - Add and optimize photos for njorda.net gallery
"""

import os
import sys
import json
import re
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageOps, ExifTags

REPO_ROOT = Path(__file__).resolve().parent.parent
PHOTOS_DIR = REPO_ROOT / "photos"
FULL_DIR = PHOTOS_DIR / "full"
THUMB_DIR = PHOTOS_DIR / "thumbs"
JSON_FILE = PHOTOS_DIR / "photos.json"
GALLERY_HTML = REPO_ROOT / "gallery.html"

MAX_FULL_SIZE = 2048
MAX_THUMB_SIZE = 650
JPEG_QUALITY_FULL = 85
JPEG_QUALITY_THUMB = 82


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text or "photo"


def format_month_year(date_str: str) -> str:
    """Format YYYY-MM-DD or YYYY-MM into 'Month Year', e.g. 'Oct 2026'."""
    if not date_str:
        return ""
    try:
        clean = date_str.replace(":", "-")[:7]
        dt = datetime.strptime(clean, "%Y-%m")
        return dt.strftime("%b %Y")
    except Exception:
        return date_str


def sort_photos(photos: list) -> list:
    """Sort photos newest to oldest by date string (YYYY-MM-DD or YYYY-MM)."""
    return sorted(photos, key=lambda p: (p.get("date", ""), p.get("id", "")), reverse=True)


def extract_exif_data(img: Image.Image) -> dict:
    meta = {}
    try:
        raw = {}
        # 1. Root EXIF dictionary
        exif_dict = img._getexif() or {}
        for k, v in exif_dict.items():
            tag = ExifTags.TAGS.get(k, k)
            raw[tag] = v

        # 2. Pillow getexif() + sub-IFD
        exif = img.getexif()
        if exif:
            for k, v in exif.items():
                tag = ExifTags.TAGS.get(k, k)
                if tag not in raw or not raw[tag]:
                    raw[tag] = v
            try:
                exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
                for k, v in exif_ifd.items():
                    tag = ExifTags.TAGS.get(k, k)
                    if tag not in raw or not raw[tag]:
                        raw[tag] = v
            except Exception:
                pass

        # Camera make / model
        make = str(raw.get("Make", "")).strip()
        model = str(raw.get("Model", "")).strip()
        if model:
            if make and not model.lower().startswith(make.lower()):
                meta["camera"] = f"{make} {model}"
            else:
                meta["camera"] = model

        # Lens
        lens = raw.get("LensModel") or raw.get("LensMake")
        if lens:
            meta["lens"] = str(lens).strip()

        # Date taken: check DateTimeOriginal, DateTimeDigitized, DateTime
        for key in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
            dt_val = raw.get(key)
            if dt_val:
                s_clean = str(dt_val).strip()[:19]
                for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y:%m:%d", "%Y-%m-%d"):
                    try:
                        dt = datetime.strptime(s_clean, fmt)
                        meta["date"] = dt.strftime("%Y-%m-%d")
                        break
                    except Exception:
                        pass
                if "date" in meta:
                    break

        # Exposure settings
        settings = []
        if "FocalLength" in raw:
            try:
                fl = float(raw["FocalLength"])
                settings.append(f"{fl:.0f}mm" if fl.is_integer() else f"{fl:.1f}mm")
            except Exception:
                pass

        if "FNumber" in raw:
            try:
                fn = float(raw["FNumber"])
                settings.append(f"ƒ/{fn:.1f}")
            except Exception:
                pass

        if "ExposureTime" in raw:
            try:
                et = float(raw["ExposureTime"])
                if et < 1 and et > 0:
                    settings.append(f"1/{int(round(1.0 / et))}s")
                else:
                    settings.append(f"{et:.1f}s")
            except Exception:
                pass

        if "ISOSpeedRatings" in raw or "PhotographicSensitivity" in raw:
            iso = raw.get("ISOSpeedRatings") or raw.get("PhotographicSensitivity")
            settings.append(f"ISO {iso}")

        if settings:
            meta["settings"] = " • ".join(settings)

    except Exception as e:
        print(f"Note: Error reading EXIF: {e}")

    return meta


def process_image(src_path: Path, output_basename: str):
    FULL_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)

    img = Image.open(src_path)
    img = ImageOps.exif_transpose(img)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    orig_w, orig_h = img.size

    # Full web version (max 2048px)
    full_img = img.copy()
    full_img.thumbnail((MAX_FULL_SIZE, MAX_FULL_SIZE), Image.Resampling.LANCZOS)
    full_dest = FULL_DIR / f"{output_basename}.jpg"
    full_img.save(full_dest, "JPEG", quality=JPEG_QUALITY_FULL, optimize=True)

    # Thumbnail version (max 650px)
    thumb_img = img.copy()
    thumb_img.thumbnail((MAX_THUMB_SIZE, MAX_THUMB_SIZE), Image.Resampling.LANCZOS)
    thumb_dest = THUMB_DIR / f"{output_basename}.jpg"
    thumb_img.save(thumb_dest, "JPEG", quality=JPEG_QUALITY_THUMB, optimize=True)

    full_w, full_h = full_img.size
    return f"photos/full/{output_basename}.jpg", f"photos/thumbs/{output_basename}.jpg", full_w, full_h


def load_photos_json() -> list:
    if JSON_FILE.exists():
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_photos_json(photos: list):
    photos = sort_photos(photos)
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(photos, f, indent=2, ensure_ascii=False)


def render_gallery_html(photos: list):
    """Generate or update gallery.html with photos sorted newest to oldest."""
    photos = sort_photos(photos)

    cards_html = []
    for idx, p in enumerate(photos):
        location = p.get("location", "")
        date_str = p.get("date", "")
        month_year = format_month_year(date_str)
        thumb = p.get("thumb", "")

        label_parts = []
        if location:
            label_parts.append(location)
        if month_year:
            label_parts.append(f'<span class="gallery-date">{month_year}</span>')

        caption_html = ' <span class="gallery-sep">&bull;</span> '.join(label_parts)
        location_block = f'<span class="gallery-location">{caption_html}</span>' if caption_html else ""

        card = f"""      <!-- Photo Card {idx + 1} -->
      <div class="gallery-card" data-index="{idx}">
        <div class="gallery-thumb-wrap">
          <img src="/{thumb}" alt="{location or 'Photo'}" loading="lazy">
        </div>
        <div class="gallery-card-body">
          {location_block}
        </div>
      </div>"""
        cards_html.append(card)

    cards_block = "\n".join(cards_html)
    json_block = json.dumps(photos, indent=2, ensure_ascii=False)

    count_str = f"{len(photos)} frame" if len(photos) == 1 else f"{len(photos)} frames"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <title>gallery – njorda.net</title>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script>(function(){{const t=localStorage.getItem('njorda_theme');if(t)document.documentElement.setAttribute('data-theme',t);}})();</script>
  <link rel="stylesheet" href="njorda.css?v=5">
  <script src="/site.js?v=5" defer></script>
</head>
<body class="gallery-page">

  <div class="page">

    <!-- Header -->
    <div class="box">
      <div class="box-header">
        <button id="themeToggle" class="theme-toggle-btn" aria-label="Toggle theme" title="Toggle theme">🌙</button>
        <div class="header-title flicker">njorda.net</div>
        <div class="tagline">
          <i>field.log // visual.archive</i>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <nav>
      <a href="/index.html">home</a>
      <a href="/about.html">about</a>
      <a href="/tech.html">tech</a>
      <a href="/gallery.html" class="active">gallery</a>
      <a href="https://blog.njorda.net" target="_blank">blog ↗</a>
      <a href="https://bsky.app/profile/njorda.net" target="_blank">bluesky ↗</a>
      <a href="https://www.linkedin.com/in/jordannicholas" target="_blank">linkedin ↗</a>
    </nav>

    <!-- Gallery Grid -->
    <div class="gallery-grid" id="galleryGrid">
{cards_block}
    </div>

    <!-- Field Status -->
    <div class="under-construction">
      [ FIELD ARCHIVE ] Ann Arbor, MI &bull; 🍂 Autumn &bull; Actively updated &bull; {count_str}
    </div>

    <!-- Footer -->
    <div class="footer">
      &copy; <script>document.write(new Date().getFullYear());</script> njorda.net &bull; visual archive
    </div>

  </div>

  <!-- Lightbox Modal -->
  <div class="lightbox-modal" id="lightbox" aria-hidden="true">
    <div class="lightbox-content" role="dialog" aria-modal="true">
      <button class="lightbox-close" id="lightboxClose" title="Close (Esc)">&times;</button>
      <button class="lightbox-nav-btn lightbox-prev" id="lightboxPrev" title="Previous photo (&larr;)">&lsaquo;</button>
      <button class="lightbox-nav-btn lightbox-next" id="lightboxNext" title="Next photo (&rarr;)">&rsaquo;</button>
      <div class="lightbox-image-wrap">
        <img id="lightboxImg" src="" alt="">
      </div>
      <div class="lightbox-info">
        <span class="lightbox-location" id="lightboxLocation"></span>
      </div>
    </div>
  </div>

  <script id="gallery-data" type="application/json">
{json_block}
  </script>

  <script>
    (function() {{
      const galleryData = JSON.parse(document.getElementById('gallery-data').textContent || '[]');
      const lightbox = document.getElementById('lightbox');
      const lightboxImg = document.getElementById('lightboxImg');
      const lightboxLocation = document.getElementById('lightboxLocation');
      const closeBtn = document.getElementById('lightboxClose');
      const prevBtn = document.getElementById('lightboxPrev');
      const nextBtn = document.getElementById('lightboxNext');
      let currentIndex = -1;

      function formatMonthYear(dateStr) {{
        if (!dateStr) return '';
        try {{
          const parts = dateStr.replace(/:/g, '-').split('-');
          if (parts.length >= 2) {{
            const year = parseInt(parts[0], 10);
            const monthIndex = parseInt(parts[1], 10) - 1;
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            if (monthIndex >= 0 && monthIndex < 12 && !isNaN(year)) {{
              return months[monthIndex] + ' ' + year;
            }}
          }}
        }} catch (e) {{}}
        return dateStr;
      }}

      function openLightbox(index) {{
        if (index < 0 || index >= galleryData.length) return;
        currentIndex = index;
        const item = galleryData[index];

        lightboxImg.src = '/' + item.full;
        lightboxImg.alt = item.location ? ('Photo from ' + item.location) : 'Photo';

        const labelParts = [];
        if (item.location) labelParts.push(item.location);
        const my = formatMonthYear(item.date);
        if (my) labelParts.push('<span class="lightbox-date">' + my + '</span>');
        lightboxLocation.innerHTML = labelParts.join(' &bull; ');

        const showNav = galleryData.length > 1;
        prevBtn.style.display = showNav ? 'flex' : 'none';
        nextBtn.style.display = showNav ? 'flex' : 'none';

        lightbox.classList.add('active');
        lightbox.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
      }}

      function closeLightbox() {{
        lightbox.classList.remove('active');
        lightbox.setAttribute('aria-hidden', 'true');
        lightboxImg.src = '';
        document.body.style.overflow = '';
      }}

      function showPrev() {{
        if (galleryData.length <= 1) return;
        const next = (currentIndex - 1 + galleryData.length) % galleryData.length;
        openLightbox(next);
      }}

      function showNext() {{
        if (galleryData.length <= 1) return;
        const next = (currentIndex + 1) % galleryData.length;
        openLightbox(next);
      }}

      document.querySelectorAll('.gallery-card').forEach(card => {{
        card.addEventListener('click', () => {{
          const idx = parseInt(card.getAttribute('data-index'), 10);
          openLightbox(idx);
        }});
      }});

      closeBtn.addEventListener('click', closeLightbox);
      prevBtn.addEventListener('click', (e) => {{ e.stopPropagation(); showPrev(); }});
      nextBtn.addEventListener('click', (e) => {{ e.stopPropagation(); showNext(); }});

      lightbox.addEventListener('click', (e) => {{
        if (e.target === lightbox) closeLightbox();
      }});

      let touchStartX = 0;
      let touchStartY = 0;

      lightbox.addEventListener('touchstart', (e) => {{
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
      }}, {{ passive: true }});

      lightbox.addEventListener('touchend', (e) => {{
        const diffX = e.changedTouches[0].screenX - touchStartX;
        const diffY = e.changedTouches[0].screenY - touchStartY;
        if (Math.abs(diffX) > 45 && Math.abs(diffX) > Math.abs(diffY)) {{
          if (diffX < 0) showNext();
          else showPrev();
        }}
      }}, {{ passive: true }});

      document.addEventListener('keydown', (e) => {{
        if (!lightbox.classList.contains('active')) return;
        if (e.key === 'Escape') closeLightbox();
        else if (e.key === 'ArrowLeft') showPrev();
        else if (e.key === 'ArrowRight') showNext();
      }});
    }})();
  </script>



</body>
</html>
"""
    with open(GALLERY_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Updated {GALLERY_HTML} with {len(photos)} photo(s).")


def parse_date_str(s: str) -> str:
    """Parse flexible date strings (e.g. 'May 2026', 'October 2025', '2025-09') into 'YYYY-MM-DD'."""
    if not s:
        return ""
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y:%m:%d", "%B %Y", "%b %Y", "%B, %Y", "%b, %Y", "%m/%Y", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return s


def add_photo(image_path: Path, location: str = None, camera: str = None,
              lens: str = None, settings: str = None, date: str = None,
              push: bool = False, **kwargs):
    if not image_path.exists():
        print(f"Error: File not found: {image_path}", file=sys.stderr)
        return False

    with Image.open(image_path) as raw_img:
        exif = extract_exif_data(raw_img)

    location = location or (input("Location: ").strip() if sys.stdin.isatty() else "Andorra")
    raw_date = date or exif.get("date")
    if raw_date:
        date = parse_date_str(raw_date)
    elif sys.stdin.isatty():
        date = parse_date_str(input("Month/Year taken (e.g. May 2026 or 2026-05): ").strip())
    else:
        date = datetime.now().strftime("%Y-%m-%d")
    camera = camera or exif.get("camera") or "Fujifilm X-T30 II"
    lens = lens or exif.get("lens") or ""
    settings = settings or exif.get("settings") or ""

    base_slug = slugify(location) or "photo"
    slug = base_slug
    counter = 1
    while (FULL_DIR / f"{slug}.jpg").exists():
        counter += 1
        slug = f"{base_slug}-{counter}"

    print(f"Optimizing '{image_path.name}' -> '{slug}.jpg'...")
    full_rel, thumb_rel, full_w, full_h = process_image(image_path, slug)

    entry = {
        "id": slug,
        "location": location,
        "date": date,
        "camera": camera,
        "lens": lens,
        "settings": settings,
        "full": full_rel,
        "thumb": thumb_rel,
        "width": full_w,
        "height": full_h
    }

    photos = load_photos_json()
    photos.append(entry)
    # Automatically sort newest to oldest
    photos = sort_photos(photos)
    save_photos_json(photos)
    render_gallery_html(photos)

    print(f"Successfully added photo from '{location}' ({format_month_year(date)}) to gallery!")
    print(f"  Full web image: {full_rel} ({full_w}x{full_h})")
    print(f"  Thumbnail:      {thumb_rel}")

    if push:
        print("\nCommitting and pushing to GitHub...")
        subprocess.run(["git", "add", "photos/", "gallery.html"], cwd=REPO_ROOT, check=True)
        subprocess.run(["git", "commit", "-m", f"Add photo from {location} to gallery"], cwd=REPO_ROOT, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_ROOT, check=True)
        print("Done! Changes are live on GitHub.")

    return True


def main():
    parser = argparse.ArgumentParser(description="Add photos to njorda.net gallery")
    parser.add_argument("image", nargs="?", default=None, help="Path to image file")
    parser.add_argument("--title", "-t", help="Title of photo (legacy)")
    parser.add_argument("--caption", "-c", help="Description / caption (legacy)")
    parser.add_argument("--date", "-d", help="Date taken (YYYY-MM-DD or YYYY-MM)")
    parser.add_argument("--location", "-l", help="Location")
    parser.add_argument("--camera", help="Camera model")
    parser.add_argument("--lens", help="Lens model")
    parser.add_argument("--settings", help="Exposure settings string")
    parser.add_argument("--push", action="store_true", help="Git commit and push immediately")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild gallery.html from photos.json without adding new photo")

    args = parser.parse_args()

    if args.rebuild:
        photos = load_photos_json()
        render_gallery_html(photos)
        return

    if not args.image:
        parser.print_help()
        sys.exit(1)

    add_photo(
        Path(args.image),
        date=args.date,
        location=args.location,
        camera=args.camera,
        lens=args.lens,
        settings=args.settings,
        push=args.push
    )


if __name__ == "__main__":
    main()
