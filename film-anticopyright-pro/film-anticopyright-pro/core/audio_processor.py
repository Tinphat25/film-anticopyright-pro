"""
audio_processor.py - Xử lý âm thanh, nhạc nền (BGM), cao độ (Pitch), và AI Voiceover (Edge-TTS)
"""

import asyncio
import math
import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict


def semitones_to_pitch_ratio(semitones: float) -> float:
    """Chuyển đổi số semitones (nửa cung) sang tỉ lệ pitch (tần số)"""
    return round(math.pow(2.0, semitones / 12.0), 6)


async def generate_edge_tts(
    text: str,
    output_path: str,
    voice: str = "vi-VN-HoaiMyNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz"
) -> str:
    """
    Sinh file giọng đọc AI thuyết minh tiếng Việt chất lượng cao.
    Thử nghiệm Edge-TTS trước, tự động fallback sang Google TTS (gTTS) nếu mạng không ổn định.
    """
    if not text.strip():
        raise ValueError("Nội dung kịch bản thuyết minh trống!")

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Thử dùng Edge-TTS
    try:
        import edge_tts
        communicate = edge_tts.Communicate(
            text=text.strip(),
            voice=voice
        )
        await communicate.save(str(out_file))
        if out_file.exists() and out_file.stat().st_size > 500:
            return str(out_file)
    except Exception:
        pass

    # 2. Fallback đáng tin cậy sang gTTS
    try:
        from gtts import gTTS
        tts = gTTS(text=text.strip(), lang="vi", slow=False)
        tts.save(str(out_file))
        return str(out_file)
    except Exception as e:
        raise RuntimeError(f"Không thể sinh giọng đọc TTS: {e}")


def generate_ambient_bgm(output_path: str, duration_sec: int = 60, name: str = "Cinematic Ambient") -> str:
    """
    Tạo một đoạn nhạc nền thư giãn (Ambient Chill) bằng FFmpeg lavfi 
    để người dùng có thể sử dụng ngay mà không cần tải nhạc ngoài.
    """
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    if out_file.exists():
        return str(out_file)

    # Sử dụng các tần số hài âm êm dịu (C major / A minor ambient chords)
    # 220Hz (A3), 261.63Hz (C4), 329.63Hz (E4), 392Hz (G4), 440Hz (A4)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i",
        f"aevalsrc=0.08*sin(2*PI*220*t)+0.06*sin(2*PI*261.63*t)+0.06*sin(2*PI*329.63*t)+0.04*sin(2*PI*392*t)+0.02*sin(2*PI*440*t):s=44100:d={duration_sec}",
        "-af", f"afade=t=in:ss=0:d=3,afade=t=out:st={duration_sec - 3}:d=3,lowpass=f=1200",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        str(out_file)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return str(out_file)


def ensure_default_bgm_library(bgm_dir: str) -> List[Dict[str, str]]:
    """Đảm bảo có ít nhất các bài nhạc nền mẫu trong thư mục bgm/"""
    dir_path = Path(bgm_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    tracks = [
        ("NCS_Chill_Ambient_Relax.mp3", 60, "Ambient Chill Thư Giãn"),
        ("NCS_Cinematic_Tension_Review.mp3", 60, "Cinematic Hồi Hộp Review Phim"),
        ("NCS_LoFi_Acoustic_Calm.mp3", 60, "Lo-Fi Acoustic Nhẹ Nhàng")
    ]

    for filename, dur, label in tracks:
        file_p = dir_path / filename
        if not file_p.exists():
            try:
                generate_ambient_bgm(str(file_p), dur, label)
            except Exception:
                pass

    return list_available_bgm(bgm_dir)


def list_available_bgm(bgm_dir: str) -> List[Dict[str, str]]:
    """Quét và trả về danh sách nhạc nền trong thư mục bgm/"""
    dir_path = Path(bgm_dir)
    if not dir_path.exists():
        return []

    supported_exts = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
    items = []
    for file in sorted(dir_path.iterdir()):
        if file.is_file() and file.suffix.lower() in supported_exts:
            items.append({
                "filename": file.name,
                "filepath": str(file.resolve()),
                "title": file.stem.replace("_", " ")
            })
    return items
