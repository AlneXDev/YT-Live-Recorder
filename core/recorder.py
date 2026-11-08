import os
import re
import time
import shutil
import signal
import subprocess
import logging
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn

logger = logging.getLogger(__name__)

class FFmpegRecorder:
    def __init__(self, output_file: str, quality: str = "1080p", duration: int = -1, force: bool = False, http_headers: dict = None, refresh_url_func = None, transcode: bool = False):
        self.output_file = output_file
        self.quality = quality
        self.duration = duration
        self.force = force
        self.http_headers = http_headers or {}
        self.refresh_url_func = refresh_url_func
        self.transcode = transcode
        self.process = None
        self.is_interrupted = False
        self.recorded_parts = []
        self.total_elapsed = 0.0
        
        self.quality_map = {
            "720p": "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            "1080p": "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "1440p": "scale=2560:1440:force_original_aspect_ratio=decrease,pad=2560:1440:(ow-iw)/2:(oh-ih)/2",
            "2160p": "scale=3840:2160:force_original_aspect_ratio=decrease,pad=3840:2160:(ow-iw)/2:(oh-ih)/2"
        }

    def _handle_sigint(self, sig, frame):
        if not self.is_interrupted:
            logger.info("\nInterrupt received! Shutting down gracefully...")
            self.is_interrupted = True
            if self.process:
                try:
                    self.process.terminate()
                except Exception:
                    pass

    def _parse_time_us(self, us_str: str) -> float:
        """Parses FFmpeg out_time_us string to seconds."""
        try:
            return float(us_str) / 1000000.0
        except ValueError:
            return 0.0

    def _merge_parts(self) -> bool:
        if not self.recorded_parts:
            logger.error("No recorded parts found.")
            return False
            
        if len(self.recorded_parts) == 1:
            part = self.recorded_parts[0]
            try:
                if os.path.exists(self.output_file) and not self.force:
                    logger.error(f"Output file {self.output_file} already exists. To overwrite, use -f/--force.")
                    return False
                if os.path.exists(self.output_file):
                    os.remove(self.output_file)
                
                # Remux to standard MP4 for 100% player compatibility (defragment)
                remux_cmd = [
                    'ffmpeg',
                    '-y',
                    '-hide_banner',
                    '-loglevel', 'error',
                    '-i', part,
                    '-c', 'copy',
                    '-movflags', '+faststart',
                    self.output_file
                ]
                logger.debug(f"Remuxing part to standard MP4: {' '.join(remux_cmd)}")
                res = subprocess.run(remux_cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    try:
                        os.remove(part)
                    except Exception:
                        pass
                    logger.info("Recording finished successfully.")
                    return True
                else:
                    logger.error(f"Failed to remux temp part: {res.stderr}")
                    return False
            except Exception as e:
                logger.error(f"Failed to finalize output: {e}")
                return False
                
        # Multiple parts, need to concat them
        dir_name = os.path.dirname(self.output_file) or '.'
        concat_txt = os.path.join(dir_name, ".temp_concat_list.txt")
        try:
            with open(concat_txt, "w") as f:
                for part in self.recorded_parts:
                    abs_path = os.path.abspath(part)
                    f.write(f"file '{abs_path}'\n")
                    
            concat_cmd = [
                'ffmpeg',
                '-y',
                '-hide_banner',
                '-loglevel', 'error',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_txt,
                '-c', 'copy',
                '-movflags', '+faststart',
                self.output_file
            ]
            
            logger.info(f"Merging {len(self.recorded_parts)} parts into {self.output_file}...")
            res = subprocess.run(concat_cmd, capture_output=True, text=True)
            if res.returncode == 0:
                logger.info("Merge completed successfully.")
                # Clean up parts
                for part in self.recorded_parts:
                    try:
                        os.remove(part)
                    except Exception:
                        pass
                return True
            else:
                logger.error(f"Failed to merge parts: {res.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error merging parts: {e}")
            return False
        finally:
            if os.path.exists(concat_txt):
                try:
                    os.remove(concat_txt)
                except Exception:
                    pass

    def record(self, stream_url: str, audio_url: str = None):
        original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._handle_sigint)
        
        vf_filter = self.quality_map.get(self.quality, self.quality_map["1080p"])
        dir_name = os.path.dirname(self.output_file) or '.'
        base_name = os.path.basename(self.output_file)
        name_part, ext_part = os.path.splitext(base_name)
        if not ext_part:
            ext_part = '.mp4'
        
        max_retries = 6
        base_delay = 5
        time_regex = re.compile(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})")
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%") if self.duration > 0 else TextColumn("Recording..."),
            TimeElapsedColumn(),
            TimeRemainingColumn() if self.duration > 0 else TextColumn(""),
            transient=False,
        ) as progress:
            
            task_id = progress.add_task(f"Recording to {os.path.basename(self.output_file)}", total=self.duration if self.duration > 0 else None)
            
            for attempt in range(max_retries):
                if self.is_interrupted:
                    break
                    
                if self.duration > 0 and self.total_elapsed >= self.duration:
                    logger.info("Target duration reached.")
                    break
                    
                if attempt > 0:
                    logger.info(f"Retrying connection... (Attempt {attempt + 1}/{max_retries})")
                
                current_url = stream_url
                current_audio_url = audio_url
                if attempt > 0 and self.refresh_url_func:
                    logger.info("Refreshing stream URL from YouTube...")
                    try:
                        refreshed = self.refresh_url_func()
                        if isinstance(refreshed, (tuple, list)):
                            current_url = refreshed[0]
                            current_audio_url = refreshed[1] if len(refreshed) > 1 else None
                        else:
                            current_url, current_audio_url = refreshed, None
                    except Exception as e:
                        logger.error(f"Failed to refresh stream URL: {e}")
                
                remaining_duration = self.duration - self.total_elapsed if self.duration > 0 else -1
                part_file = os.path.join(dir_name, f".temp_{name_part}_part{attempt + 1}.part")
                
                cmd = [
                    'ffmpeg',
                    '-y',
                    '-hide_banner',
                    '-loglevel', 'info',
                ]
                
                user_agent = self.http_headers.get('User-Agent')
                headers_str = ""
                for k, v in self.http_headers.items():
                    if k.lower() != 'user-agent':
                        headers_str += f"{k}: {v}\r\n"

                # Options that must be repeated before every input URL.
                input_opts = []
                if user_agent:
                    input_opts.extend(['-user_agent', user_agent])
                if headers_str:
                    input_opts.extend(['-headers', headers_str])
                input_opts.extend([
                    '-reconnect', '1',
                    '-reconnect_streamed', '1',
                    '-reconnect_delay_max', '2',
                ])

                cmd.extend(input_opts)
                cmd.extend(['-i', current_url])

                if current_audio_url:
                    # Video and audio are served as separate manifests; feed
                    # both to FFmpeg and map one stream from each input.
                    cmd.extend(input_opts)
                    cmd.extend(['-i', current_audio_url])
                    cmd.extend(['-map', '0:v:0', '-map', '1:a:0'])
                
                if self.transcode:
                    cmd.extend([
                        '-vf', vf_filter,
                        '-c:v', 'libx264',
                        '-preset', 'veryfast',
                        '-crf', '19',
                        '-c:a', 'aac',
                        '-b:a', '128k',
                    ])
                else:
                    # Copy video untouched, but re-encode audio. Copying AAC
                    # straight from HLS can leave the MP4 esds without a
                    # DecoderSpecificInfo (AudioSpecificConfig) box, which
                    # strict players reject as "mp4a not supported".
                    cmd.extend([
                        '-c:v', 'copy',
                        '-c:a', 'aac',
                        '-b:a', '128k',
                    ])
                    
                cmd.extend([
                    '-movflags', 'frag_keyframe+empty_moov',
                ])
                
                if remaining_duration > 0:
                    cmd.extend(['-t', str(int(remaining_duration))])
                
                # Force MP4 muxer regardless of the .part extension so
                # temp files aren't mistaken for finished .mp4 recordings.
                cmd.extend(['-f', 'mp4'])
                cmd.append(part_file)
                
                try:
                    logger.debug(f"Running command: {' '.join(cmd)}")
                    self.process = subprocess.Popen(
                        cmd,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                        bufsize=1
                    )
                    
                    buffer = ""
                    current_part_elapsed = 0.0
                    while True:
                        if self.is_interrupted:
                            break
                            
                        char = self.process.stderr.read(1)
                        if not char:
                            break
                            
                        buffer += char
                        if char in ('\r', '\n'):
                            clean_line = buffer.strip()
                            if clean_line:
                                logger.debug(f"[FFmpeg] {clean_line}")
                                
                            match = time_regex.search(buffer)
                            if match:
                                parts = match.group(1).split(':')
                                if len(parts) == 3:
                                    current_part_elapsed = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                                    progress.update(task_id, completed=self.total_elapsed + current_part_elapsed)
                            buffer = ""
                            
                    self.process.wait()
                    retcode = self.process.returncode
                    
                    self.total_elapsed += current_part_elapsed
                    
                    if os.path.exists(part_file) and os.path.getsize(part_file) > 0:
                        self.recorded_parts.append(part_file)
                    
                    if retcode == 0 or self.is_interrupted:
                        if not self.is_interrupted:
                            logger.info(f"Part {attempt + 1} finished successfully.")
                        else:
                            logger.info("Recording stopped by user.")
                        break
                    else:
                        logger.error(f"FFmpeg exited with error code {retcode} on part {attempt + 1}. Check stream availability.")
                        
                except Exception as e:
                    logger.error(f"Error running FFmpeg on part {attempt + 1}: {e}")
                
                if self.is_interrupted:
                    break
                    
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Connection lost. Retrying in {delay} seconds...")
                
                for _ in range(delay):
                    if self.is_interrupted:
                        break
                    time.sleep(1)
                    
        success = self._merge_parts()
        signal.signal(signal.SIGINT, original_sigint)
        return success
