"""
video_processor.py - Engine xử lý video kháng bản quyền toàn diện
Thực hiện đầy đủ 4 tiêu chuẩn theo hướng dẫn:
1. Xử lý âm thanh & Nhạc nền (OST 70% + BGM NCS)
2. Cắt cảnh ngắn (5-8s) & Đổi góc khung hình (Flip, Zoom 105%, Border/Effects)
3. Lồng tiếng & Bình luận riêng Fair Use (File audio hoặc Edge-TTS AI)
4. Biến đổi tốc độ (1.05x, 1.08x) & Cao độ âm thanh (Pitch +2-3 Semitones)
"""

import asyncio
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Callable, Optional

from core.ffmpeg_utils import get_video_info
from core.audio_processor import semitones_to_pitch_ratio, generate_edge_tts


class VideoProcessor:
    def __init__(self, temp_dir: str = "uploads", output_dir: str = "outputs"):
        self.temp_dir = Path(temp_dir)
        self.output_dir = Path(output_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.active_processes: Dict[str, subprocess.Popen] = {}

    def cancel_job(self, job_id: str) -> bool:
        """Hủy tác vụ đang chạy"""
        proc = self.active_processes.get(job_id)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                return True
            except Exception:
                pass
        return False

    async def process_video(
        self,
        job_id: str,
        input_video_path: str,
        options: Dict[str, Any],
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Thực hiện toàn bộ pipeline xử lý video kháng bản quyền
        """
        # 1. Trích xuất thông tin video đầu vào
        video_info = get_video_info(input_video_path)
        orig_duration = video_info["duration"]
        orig_w = video_info["width"]
        orig_h = video_info["height"]
        has_audio = video_info["has_audio"]
        fps = video_info["fps"] if video_info["fps"] > 0 else 30.0

        # Lấy các tùy chọn
        orig_vol = float(options.get("original_audio_volume", 0.30))  # Giảm 70% -> còn 30%
        enable_bgm = bool(options.get("enable_bgm", True))
        bgm_path = options.get("bgm_path")
        bgm_vol = float(options.get("bgm_volume", 0.25))

        cut_mode = options.get("cut_mode", "micro_cut")  # micro_cut, flash_transition, none
        scene_interval = float(options.get("scene_interval_sec", 6.0))
        horizontal_flip = bool(options.get("horizontal_flip", True))
        zoom_percent = float(options.get("zoom_percent", 105.0))
        border_mode = options.get("border_mode", "cinematic_bars")  # cinematic_bars, glow_frame, subtle_grain, none

        voiceover_mode = options.get("voiceover_mode", "none")  # none, file, tts
        voiceover_file = options.get("voiceover_file")
        voiceover_text = options.get("voiceover_text", "")
        voiceover_voice = options.get("voiceover_voice", "vi-VN-NamMinhNeural")
        voiceover_vol = float(options.get("voiceover_volume", 1.20))
        voiceover_ducking = bool(options.get("voiceover_ducking", True))

        speed = float(options.get("speed", 1.05))  # 1.05x hoặc 1.08x
        pitch_semitones = float(options.get("pitch_semitones", 2.0))  # lệch 2-3 semitone

        if speed <= 0:
            speed = 1.05

        # 2. Xử lý Voiceover nếu là TTS
        voiceover_final_path = None
        if voiceover_mode == "tts" and voiceover_text.strip():
            if progress_callback:
                progress_callback({
                    "job_id": job_id,
                    "percent": 5,
                    "status": "processing",
                    "stage": "Đang sinh giọng đọc thuyết minh AI tiếng Việt...",
                    "details": f"Giọng: {voiceover_voice}"
                })
            tts_output = self.temp_dir / f"tts_{job_id}.mp3"
            await generate_edge_tts(
                text=voiceover_text,
                output_path=str(tts_output),
                voice=voiceover_voice
            )
            voiceover_final_path = str(tts_output)
        elif voiceover_mode == "file" and voiceover_file and os.path.exists(voiceover_file):
            voiceover_final_path = voiceover_file

        # Nếu có voiceover và bật ducking, tự động giảm nhẹ âm lượng nền
        effective_orig_vol = orig_vol * 0.7 if (voiceover_final_path and voiceover_ducking) else orig_vol
        effective_bgm_vol = bgm_vol * 0.7 if (voiceover_final_path and voiceover_ducking) else bgm_vol

        # 3. Tính toán thời lượng đầu ra dự kiến
        expected_duration = orig_duration / speed
        if cut_mode == "micro_cut" and scene_interval > 0.5:
            # Mỗi khoảng scene_interval cắt bỏ 0.25s
            num_cuts = int(orig_duration / scene_interval)
            lost_duration = num_cuts * 0.25
            expected_duration = max(1.0, (orig_duration - lost_duration) / speed)

        # 4. Xây dựng filter graph cho FFmpeg
        # Inputs:
        # 0: input_video
        # 1: BGM (nếu có)
        # 2: Voiceover (nếu có)
        cmd_inputs = ["-i", input_video_path]
        input_count = 1

        bgm_input_idx = -1
        if enable_bgm and bgm_path and os.path.exists(bgm_path):
            cmd_inputs.extend(["-i", bgm_path])
            bgm_input_idx = input_count
            input_count += 1

        voice_input_idx = -1
        if voiceover_final_path and os.path.exists(voiceover_final_path):
            cmd_inputs.extend(["-i", voiceover_final_path])
            voice_input_idx = input_count
            input_count += 1

        # Xây dựng Video Filters
        v_filters = []

        # Cắt cảnh ngắn (5-8s)
        if cut_mode == "micro_cut":
            # Cắt bỏ 0.25s mỗi scene_interval giây
            v_filters.append(f"select='gte(mod(t\\,{scene_interval})\\,0.25)'")
            v_filters.append("setpts=N/FRAME_RATE/TB")
        elif cut_mode == "flash_transition":
            # Chớp sáng chuyển cảnh 0.1s mỗi scene_interval giây
            v_filters.append(f"eq=brightness='if(lt(mod(t\\,{scene_interval})\\,0.10)\\,0.35\\,0.0)'")

        # Lật gương ngang
        if horizontal_flip:
            v_filters.append("hflip")

        # Phóng to 105% và center crop
        if zoom_percent > 100:
            crop_w = f"trunc(iw/({zoom_percent}/100)/2)*2"
            crop_h = f"trunc(ih/({zoom_percent}/100)/2)*2"
            v_filters.append(f"crop={crop_w}:{crop_h}:(in_w-out_w)/2:(in_h-out_h)/2")
            v_filters.append(f"scale={orig_w}:{orig_h}")

        # Khung viền & hiệu ứng chuyển cảnh
        if border_mode == "cinematic_bars":
            bar_h = f"trunc(ih*0.07/2)*2"
            v_filters.append(f"drawbox=x=0:y=0:w=iw:h={bar_h}:color=black:t=fill")
            v_filters.append(f"drawbox=x=0:y=ih-{bar_h}:w=iw:h={bar_h}:color=black:t=fill")
        elif border_mode == "glow_frame":
            v_filters.append("drawbox=x=0:y=0:w=iw:h=ih:color=white@0.25:t=6")
            v_filters.append("drawbox=x=6:y=6:w=iw-12:h=ih-12:color=black@0.2:t=2")
        elif border_mode == "subtle_grain":
            v_filters.append("eq=contrast=1.04:saturation=1.05:brightness=0.01")
            v_filters.append("noise=alls=7:allf=t+u")

        # Biến đổi tốc độ Video
        if abs(speed - 1.0) > 0.001:
            v_filters.append(f"setpts=(PTS-STARTPTS)/{speed}")

        v_filters.append("format=yuv420p")
        video_filter_str = ",".join(v_filters)

        # Xây dựng Audio Filters & Mixing
        filter_complex_parts = []
        filter_complex_parts.append(f"[0:v]{video_filter_str}[outv]")

        audio_outputs_to_mix = []

        # Audio gốc
        pitch_scale = semitones_to_pitch_ratio(pitch_semitones)
        if has_audio:
            orig_af_list = []
            if cut_mode == "micro_cut":
                orig_af_list.append(f"aselect='gte(mod(t\\,{scene_interval})\\,0.25)'")
                orig_af_list.append("asetpts=N/SR/TB")

            # Rubberband: pitch & speed alteration
            orig_af_list.append(f"rubberband=pitch={pitch_scale}:tempo={speed}")
            orig_af_list.append(f"volume={effective_orig_vol:.3f}")
            orig_af_str = ",".join(orig_af_list)
            filter_complex_parts.append(f"[0:a]{orig_af_str}[a_orig]")
            audio_outputs_to_mix.append("[a_orig]")
        else:
            # Nếu video gốc không có âm thanh, tạo luồng âm thanh tĩnh nhỏ
            filter_complex_parts.append("anullsrc=r=44100:cl=stereo[a_orig]")
            audio_outputs_to_mix.append("[a_orig]")

        # BGM
        if bgm_input_idx != -1:
            fade_start = max(0.5, expected_duration - 2.5)
            bgm_af = (
                f"aloop=loop=-1:size=2e+09,"
                f"volume={effective_bgm_vol:.3f},"
                f"afade=t=in:ss=0:d=1.5,"
                f"afade=t=out:st={fade_start:.2f}:d=2.5"
            )
            filter_complex_parts.append(f"[{bgm_input_idx}:a]{bgm_af}[a_bgm]")
            audio_outputs_to_mix.append("[a_bgm]")

        # Voiceover
        if voice_input_idx != -1:
            voice_af = f"volume={voiceover_vol:.3f}"
            filter_complex_parts.append(f"[{voice_input_idx}:a]{voice_af}[a_voice]")
            audio_outputs_to_mix.append("[a_voice]")

        # Trộn các luồng âm thanh
        if len(audio_outputs_to_mix) > 1:
            mix_inputs = "".join(audio_outputs_to_mix)
            filter_complex_parts.append(
                f"{mix_inputs}amix=inputs={len(audio_outputs_to_mix)}:duration=first:dropout_transition=2[outa]"
            )
        else:
            filter_complex_parts.append(f"{audio_outputs_to_mix[0]}anull[outa]")

        filter_complex_str = ";".join(filter_complex_parts)

        # File đầu ra
        out_filename = f"anticopyright_{job_id}_{Path(input_video_path).stem}.mp4"
        out_path = self.output_dir / out_filename

        # Tham số lệnh FFmpeg hoàn chỉnh
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            *cmd_inputs,
            "-filter_complex", filter_complex_str,
            "-map", "[outv]",
            "-map", "[outa]",
            "-r", str(fps),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(out_path)
        ]

        if progress_callback:
            progress_callback({
                "job_id": job_id,
                "percent": 10,
                "status": "rendering",
                "stage": "Bắt đầu render video chống bản quyền bằng FFmpeg...",
                "expected_duration": round(expected_duration, 2)
            })

        # Thực thi FFmpeg và theo dõi progress thời gian thực
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )
        self.active_processes[job_id] = process

        time_pattern = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d+)")
        fps_pattern = re.compile(r"fps=\s*([\d\.]+)")
        speed_pattern = re.compile(r"speed=\s*([\d\.]+)x")

        last_percent = 10.0
        start_render_time = time.time()

        try:
            for line in process.stdout:
                line_str = line.strip()
                if not line_str:
                    continue

                t_match = time_pattern.search(line_str)
                fps_val = 0.0
                speed_str = "1.0x"

                fps_match = fps_pattern.search(line_str)
                if fps_match:
                    try:
                        fps_val = float(fps_match.group(1))
                    except Exception:
                        pass

                sp_match = speed_pattern.search(line_str)
                if sp_match:
                    speed_str = f"{sp_match.group(1)}x"

                if t_match and expected_duration > 0:
                    h, m, s = t_match.groups()
                    curr_sec = float(h) * 3600 + float(m) * 60 + float(s)
                    # Quy đổi thành phần trăm từ 10% đến 98%
                    calc_percent = 10.0 + (curr_sec / expected_duration) * 88.0
                    calc_percent = max(10.0, min(98.0, calc_percent))
                    last_percent = round(calc_percent, 1)

                    elapsed = time.time() - start_render_time
                    eta_sec = (elapsed / (calc_percent - 10.0) * (98.0 - calc_percent)) if calc_percent > 12.0 else 0

                    if progress_callback:
                        progress_callback({
                            "job_id": job_id,
                            "percent": last_percent,
                            "status": "rendering",
                            "fps": fps_val,
                            "speed": speed_str,
                            "current_time_str": f"{h}:{m}:{int(float(s)):02d}",
                            "eta_sec": round(eta_sec, 0),
                            "raw_log": line_str
                        })

            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(f"FFmpeg kết thúc với mã lỗi {return_code}")

        finally:
            self.active_processes.pop(job_id, None)

        # 5. Xử lý hoàn tất
        out_info = get_video_info(str(out_path))

        final_result = {
            "job_id": job_id,
            "status": "completed",
            "percent": 100,
            "output_filename": out_filename,
            "output_path": str(out_path.resolve()),
            "output_url": f"/outputs/{out_filename}",
            "original_info": video_info,
            "output_info": out_info,
            "applied_settings": {
                "original_audio_volume": orig_vol,
                "enable_bgm": enable_bgm,
                "bgm_used": Path(bgm_path).name if bgm_path else None,
                "cut_mode": cut_mode,
                "scene_interval": scene_interval,
                "horizontal_flip": horizontal_flip,
                "zoom_percent": zoom_percent,
                "border_mode": border_mode,
                "voiceover_mode": voiceover_mode,
                "voiceover_voice": voiceover_voice if voiceover_mode == "tts" else None,
                "speed": speed,
                "pitch_semitones": pitch_semitones
            }
        }

        if progress_callback:
            progress_callback({
                "job_id": job_id,
                "percent": 100,
                "status": "completed",
                "stage": "Xử lý thành công! Video đã sẵn sàng tải về hoặc xem thử.",
                "result": final_result
            })

        return final_result
