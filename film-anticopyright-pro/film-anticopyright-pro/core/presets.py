"""
presets.py - Các cấu hình mẫu (Preset) chống bản quyền YouTube/TikTok/Facebook
"""

from typing import Dict, Any

PRESETS: Dict[str, Dict[str, Any]] = {
    "recommended": {
        "id": "recommended",
        "name": "Khuyên Dùng (Chuẩn Hướng Dẫn Ảnh)",
        "description": "Giảm 70% âm gốc, lặp BGM NCS, lật gương, zoom 105%, viền điện ảnh, tốc độ 1.05x, pitch +2 semitone.",
        "badge": "Chuẩn 100%",
        "settings": {
            "original_audio_volume": 0.30,
            "enable_bgm": True,
            "bgm_volume": 0.25,
            "cut_mode": "micro_cut",
            "scene_interval_sec": 6.0,
            "horizontal_flip": True,
            "zoom_percent": 105,
            "border_mode": "cinematic_bars",
            "voiceover_mode": "none",
            "voiceover_volume": 1.20,
            "voiceover_ducking": True,
            "speed": 1.05,
            "pitch_semitones": 2.0
        }
    },
    "aggressive": {
        "id": "aggressive",
        "name": "Cường Độ Cao (Kháng Quét Tối Đa)",
        "description": "Dành cho phim gắt bản quyền: Giảm 80% âm gốc, zoom 108%, viền mờ + hạt phim, tốc độ 1.08x, pitch +3 semitone, cắt mỗi 5s.",
        "badge": "Mạnh Nhất",
        "settings": {
            "original_audio_volume": 0.20,
            "enable_bgm": True,
            "bgm_volume": 0.30,
            "cut_mode": "micro_cut",
            "scene_interval_sec": 5.0,
            "horizontal_flip": True,
            "zoom_percent": 108,
            "border_mode": "subtle_grain",
            "voiceover_mode": "none",
            "voiceover_volume": 1.20,
            "voiceover_ducking": True,
            "speed": 1.08,
            "pitch_semitones": 3.0
        }
    },
    "review_tts": {
        "id": "review_tts",
        "name": "Review Phim Thuyết Minh AI (Fair Use)",
        "description": "Tích hợp Edge-TTS tiếng Việt (Hoài My / Nam Minh), tự động giảm âm gốc khi đọc bình luận, tốc độ 1.05x, zoom 105%.",
        "badge": "Reviewer",
        "settings": {
            "original_audio_volume": 0.25,
            "enable_bgm": True,
            "bgm_volume": 0.20,
            "cut_mode": "micro_cut",
            "scene_interval_sec": 7.0,
            "horizontal_flip": True,
            "zoom_percent": 105,
            "border_mode": "glow_frame",
            "voiceover_mode": "tts",
            "voiceover_voice": "vi-VN-NamMinhNeural",
            "voiceover_volume": 1.30,
            "voiceover_ducking": True,
            "speed": 1.05,
            "pitch_semitones": 2.0
        }
    },
    "lightweight": {
        "id": "lightweight",
        "name": "Nhẹ Nhàng (Giữ Nguyên Màu & Âm Tự Nhiên)",
        "description": "Giảm 60% âm gốc, lồng BGM, lật gương, zoom 103%, tốc độ 1.03x, pitch +1 semitone.",
        "badge": "Tự Nhiên",
        "settings": {
            "original_audio_volume": 0.40,
            "enable_bgm": True,
            "bgm_volume": 0.20,
            "cut_mode": "none",
            "scene_interval_sec": 6.0,
            "horizontal_flip": True,
            "zoom_percent": 103,
            "border_mode": "none",
            "voiceover_mode": "none",
            "voiceover_volume": 1.10,
            "voiceover_ducking": False,
            "speed": 1.03,
            "pitch_semitones": 1.0
        }
    }
}
