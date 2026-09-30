"""
ffmpeg_utils.py - Tiện ích kiểm tra thông số video và hỗ trợ FFmpeg
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


def check_tool(tool_name: str = "ffmpeg") -> bool:
    """Kiểm tra công cụ có trong PATH hay không"""
    return shutil.which(tool_name) is not None


def get_video_info(file_path: str) -> Dict[str, Any]:
    """
    Sử dụng ffprobe để lấy thông tin chi tiết của video:
    - duration (giây)
    - width, height
    - fps
    - has_audio, has_video
    - video_codec, audio_codec
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path)
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True
        )
        data = json.loads(result.stdout)
    except Exception as e:
        raise RuntimeError(f"Lỗi khi đọc thông tin file qua ffprobe: {e}")

    format_info = data.get("format", {})
    streams = data.get("streams", [])

    duration = float(format_info.get("duration", 0.0))
    size_bytes = int(format_info.get("size", 0))

    has_video = False
    has_audio = False
    width = 0
    height = 0
    fps = 30.0
    video_codec = ""
    audio_codec = ""
    audio_sample_rate = 44100
    audio_channels = 2

    for stream in streams:
        codec_type = stream.get("codec_type")
        if codec_type == "video" and not has_video:
            has_video = True
            width = int(stream.get("width", 0))
            height = int(stream.get("height", 0))
            video_codec = stream.get("codec_name", "")
            
            # Tính FPS từ r_frame_rate hoặc avg_frame_rate
            r_fps = stream.get("r_frame_rate", "30/1")
            try:
                if "/" in r_fps:
                    num, den = r_fps.split("/")
                    fps = round(float(num) / float(den), 2) if float(den) != 0 else 30.0
                else:
                    fps = round(float(r_fps), 2)
            except Exception:
                fps = 30.0

            if duration == 0.0 and "duration" in stream:
                try:
                    duration = float(stream["duration"])
                except Exception:
                    pass

        elif codec_type == "audio" and not has_audio:
            has_audio = True
            audio_codec = stream.get("codec_name", "")
            audio_sample_rate = int(stream.get("sample_rate", 44100))
            audio_channels = int(stream.get("channels", 2))

    return {
        "filename": path.name,
        "filepath": str(path.resolve()),
        "duration": round(duration, 2),
        "duration_formatted": format_duration(duration),
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "has_video": has_video,
        "has_audio": has_audio,
        "width": width,
        "height": height,
        "fps": fps,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "audio_sample_rate": audio_sample_rate,
        "audio_channels": audio_channels
    }


def format_duration(seconds: float) -> str:
    """Định dạng giây thành mm:ss hoặc hh:mm:ss"""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
