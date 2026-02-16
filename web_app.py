import shutil
import platform
import re
import mimetypes
from urllib.parse import urlparse
from pathlib import Path
from uuid import uuid4

import yt_dlp
from fastapi import BackgroundTasks, FastAPI, Form, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app_meta import APP_DISPLAY_NAME, APP_VERSION

APP_ROOT = Path(__file__).resolve().parent
DOWNLOADS_DIR = APP_ROOT / "downloads" / "web"
TEMPLATES_DIR = APP_ROOT / "templates"
STATIC_DIR = APP_ROOT / "static"

app = FastAPI(title=APP_DISPLAY_NAME, version=APP_VERSION)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def sanitize_error_message(message: str) -> str:
    cleaned = ANSI_ESCAPE_RE.sub("", message)
    cleaned = " ".join(cleaned.split())
    return cleaned.strip()


def is_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme not in {"http", "https"}:
        return False

    host = (parsed.netloc or "").lower()
    return host in YOUTUBE_HOSTS


def normalize_mode(mode: str) -> str:
    return "mp4" if mode == "mp4" else "mp3"


def normalize_quality(quality: str) -> str:
    return quality if quality in {"128", "192", "256"} else "192"


def normalize_video_quality(video_quality: str) -> str:
    return video_quality if video_quality in {"360", "720", "1080"} else "720"


def format_duration(seconds: int | None) -> str:
    if not seconds or seconds <= 0:
        return "--:--"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def get_ffmpeg_path() -> str | None:
    system = platform.system()
    if system == "Windows":
        ffmpeg_path = APP_ROOT / "ffmpeg" / "ffmpeg.exe"
        return str(ffmpeg_path) if ffmpeg_path.exists() else None
    return shutil.which("ffmpeg")


def build_ydl_options(mode: str, quality: str, video_quality: str, output_dir: Path) -> dict:
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        system = platform.system()
        if system == "Windows":
            message = "FFmpeg not found. Add ffmpeg.exe to the project ffmpeg folder."
        elif system == "Darwin":
            message = "FFmpeg not found. Install it with brew install ffmpeg."
        else:
            message = "FFmpeg not found. Install it and add to PATH."
        raise RuntimeError(message)

    output_template = str(output_dir / "%(title)s.%(ext)s")
    options = {
        "outtmpl": output_template,
        "ffmpeg_location": ffmpeg_path,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 3,
        "fragment_retries": 3,
        "skip_unavailable_fragments": True,
        "geo_bypass": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
        },
    }

    if mode == "mp3":
        safe_quality = normalize_quality(quality)
        options.update(
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": safe_quality,
                    }
                ],
            }
        )
    else:
        safe_video_quality = normalize_video_quality(video_quality)
        options.update(
            {
                "format": f"bestvideo[height<={safe_video_quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={safe_video_quality}][ext=mp4]/best[height<={safe_video_quality}]",
                "merge_output_format": "mp4",
            }
        )

    return options


def download_media(url: str, mode: str, quality: str, video_quality: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    options = build_ydl_options(
        normalize_mode(mode),
        normalize_quality(quality),
        normalize_video_quality(video_quality),
        output_dir,
    )

    attempts = [
        options,
        {
            **options,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"],
                }
            },
        },
    ]

    last_error: Exception | None = None
    for attempt_options in attempts:
        try:
            with yt_dlp.YoutubeDL(attempt_options) as ydl:
                ydl.extract_info(url, download=True)
            last_error = None
            break
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        raise RuntimeError(sanitize_error_message(str(last_error))) from last_error

    files = sorted(output_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise RuntimeError("Download failed to produce a file.")

    return files[0]


def get_preview_data(url: str) -> dict:
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "title": info.get("title") or "Sem título",
        "channel": info.get("uploader") or "Canal desconhecido",
        "duration": format_duration(info.get("duration")),
        "thumbnail": info.get("thumbnail"),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
        },
    )


@app.get("/health")
def health_check():
    return JSONResponse({"status": "ok", "app": APP_DISPLAY_NAME, "version": APP_VERSION})


@app.get("/api/preview")
def preview(url: str = Query(...)):
    trimmed = url.strip()
    if not is_youtube_url(trimmed):
        return JSONResponse({"error": "URL do YouTube inválida."}, status_code=400)

    try:
        data = get_preview_data(trimmed)
        return JSONResponse(data)
    except Exception:
        return JSONResponse({"error": "Não foi possível carregar a prévia deste link."}, status_code=422)


@app.post("/api/download")
def download(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    mode: str = Form("mp3"),
    quality: str = Form("192"),
    video_quality: str = Form("720"),
):
    trimmed = url.strip()
    if not trimmed or not is_youtube_url(trimmed):
        return JSONResponse({"error": "Informe uma URL válida do YouTube."}, status_code=400)

    temp_dir = DOWNLOADS_DIR / str(uuid4())
    try:
        file_path = download_media(trimmed, mode, quality, video_quality, temp_dir)
    except Exception as exc:
        return JSONResponse(
            {"error": f"Falha no download: {sanitize_error_message(str(exc))}"},
            status_code=500,
        )

    background_tasks.add_task(shutil.rmtree, temp_dir, ignore_errors=True)
    guessed_media_type, _ = mimetypes.guess_type(file_path.name)
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=guessed_media_type or "application/octet-stream",
    )
