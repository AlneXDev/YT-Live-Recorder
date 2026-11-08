import re
import os
import shutil
import datetime

def parse_duration(duration_str: str) -> int:
    """
    Parses a duration string like "1h", "45m", "30s", "1h30m" into seconds.
    Also supports a raw integer string representing seconds.
    Returns -1 if duration_str is "full" or invalid.
    """
    if not duration_str or duration_str.lower() == "full":
        return -1
    
    if isinstance(duration_str, str) and duration_str.isdigit():
        val = int(duration_str)
        if val == 0:
            raise ValueError(f"Duration cannot be zero: {duration_str}")
        return val
        
    pattern = re.compile(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?')
    match = pattern.fullmatch(duration_str.lower())
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")
    
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = int(match.group(3)) if match.group(3) else 0
    
    total_seconds = hours * 3600 + minutes * 60 + seconds
    if total_seconds == 0:
        raise ValueError(f"Duration cannot be zero: {duration_str}")
        
    return total_seconds

def check_dependencies():
    """
    Checks if ffmpeg is installed and available in the system path.
    """
    if shutil.which('ffmpeg') is None:
        raise RuntimeError("ffmpeg is not installed or not in PATH. Please install it to use this tool.")

def generate_output_filename(title: str, output_path: str = None) -> str:
    """
    Generates an output filename. If output_path is provided and is a directory,
    creates the file inside it. If it's a specific filename, uses it.
    Default: youtube_live_{title}_{timestamp}.mp4
    """
    safe_title = re.sub(r'[^\w\-_\. ]', '_', title).replace(' ', '_')
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_name = f"youtube_live_{safe_title}_{timestamp}.mp4"
    
    if output_path:
        if os.path.isdir(output_path):
            return os.path.join(output_path, default_name)
        return output_path
    
    return default_name
