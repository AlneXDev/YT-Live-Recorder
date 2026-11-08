# YT Live Recorder - by Alne (https://github.com/AlneXDev)
import argparse
import sys
import logging
from rich.console import Console
from rich.logging import RichHandler
from core.utils import parse_duration, check_dependencies, generate_output_filename
from core.extractor import YTExtractor
from core.recorder import FFmpegRecorder

console = Console()

def setup_logging():
    root_logger = logging.getLogger("")
    root_logger.setLevel(logging.DEBUG)
    
    # Console handler (INFO)
    console_handler = RichHandler(console=console, rich_tracebacks=True)
    console_handler.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    
    # File handler (DEBUG)
    file_handler = logging.FileHandler("yt-live-recorder.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(file_handler)

def main():
    console.print("[bold magenta]YT Live Recorder[/] by [bold cyan]Alne[/]")
    setup_logging()
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description="Record YouTube Live Streams to completion or for a specific duration.")
    parser.add_argument("-u", "--url", required=True, help="YouTube live stream URL")
    parser.add_argument("-t", "--time", default="full", help="Duration to record (e.g., 'full', '1h', '45m', '30s', '1h30m')")
    parser.add_argument("-o", "--output", help="Output filename or directory")
    parser.add_argument("--quality", choices=["720p", "1080p", "1440p", "2160p"], default="1080p", help="Output quality preset")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite output file if it exists")
    parser.add_argument("--cookies-from-browser", help="Browser to extract cookies from (e.g., 'chrome', 'firefox')")
    parser.add_argument("--cookies", help="Path to cookies file (e.g., cookies.txt)")
    parser.add_argument("--transcode", action="store_true", help="Transcode video/audio instead of direct stream copying")
    
    args = parser.parse_args()
    
    try:
        check_dependencies()
        
        duration_seconds = parse_duration(args.time)
        logger.info(f"Target duration: {args.time} ({duration_seconds}s)" if duration_seconds > 0 else "Target duration: Full stream")
        
        extractor = YTExtractor(cookies_from_browser=args.cookies_from_browser, cookies_file=args.cookies)
        info = extractor.get_stream_info(args.url, quality=args.quality)
        
        if not info.get('is_live'):
            logger.warning("The provided URL does not appear to be a live stream. Proceeding anyway...")
            
        output_file = generate_output_filename(info['title'], args.output)
        
        logger.info(f"Stream Title: {info['title']}")
        logger.info(f"Output File: {output_file}")
        logger.info(f"Quality: {args.quality}")
        logger.info(f"Mode: {'Transcoding' if args.transcode else 'Video Copy + AAC Audio (Maximum FPS/Quality)'}")
        
        def refresh_urls():
            fresh = extractor.get_stream_info(args.url, quality=args.quality)
            return fresh['stream_url'], fresh.get('audio_url')

        recorder = FFmpegRecorder(
            output_file=output_file,
            quality=args.quality,
            duration=duration_seconds,
            force=args.force,
            http_headers=info.get('http_headers', {}),
            refresh_url_func=refresh_urls,
            transcode=args.transcode
        )

        recorder.record(info['stream_url'], info.get('audio_url'))
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
