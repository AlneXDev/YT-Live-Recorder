import yt_dlp
import logging

logger = logging.getLogger(__name__)


class YTExtractor:
    def __init__(self, cookies_from_browser=None, cookies_file=None):
        self.cookies_from_browser = cookies_from_browser
        self.cookies_file = cookies_file

    def _ydl_opts(self, quality: str = None) -> dict:
        format_sel = 'bestvideo+bestaudio/best'
        if quality:
            height = quality.replace('p', '')
            if height.isdigit():
                format_sel = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best[height<={height}]/best'

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'format': format_sel,
        }

        if self.cookies_from_browser:
            ydl_opts['cookiesfrombrowser'] = (self.cookies_from_browser,)
        elif self.cookies_file:
            ydl_opts['cookiefile'] = self.cookies_file

        return ydl_opts

    @staticmethod
    def _split_streams(formats) -> tuple:
        """
        Splits a list of yt-dlp format dicts into (video_url, audio_url).
        audio_url is None when the chosen format already muxes audio+video.
        """
        video_url = None
        audio_url = None

        for f in formats:
            url = f.get('url')
            if not url:
                continue
            vcodec = f.get('vcodec')
            acodec = f.get('acodec')

            if vcodec not in (None, 'none'):
                # Has a real video stream (muxed or video-only)
                if video_url is None:
                    video_url = url
            elif vcodec == 'none':
                # Explicitly audio-only
                if audio_url is None:
                    audio_url = url
            elif acodec not in (None, 'none'):
                # Video codec unknown but audio present
                if video_url is None:
                    video_url = url
            else:
                # Both unknown (e.g. minimal manifest entry) -> assume muxed
                if video_url is None:
                    video_url = url

        return video_url, audio_url

    def get_stream_info(self, url: str, quality: str = None):
        """
        Extracts stream information from a YouTube URL.
        Returns a dictionary containing 'stream_url' (video/muxed manifest),
        'audio_url' (separate audio manifest or None), 'title' and 'is_live'.
        """
        with yt_dlp.YoutubeDL(self._ydl_opts(quality)) as ydl:
            logger.info(f"Extracting info for {url} ...")
            try:
                info_dict = ydl.extract_info(url, download=False)
            except yt_dlp.utils.DownloadError as e:
                raise RuntimeError(f"Failed to extract info: {e}")

            if not info_dict:
                raise RuntimeError("Could not retrieve information from the URL.")

            video_url = None
            audio_url = None

            # Preferred: the formats yt-dlp actually selected for
            # "bestvideo+bestaudio" (kept separate for live streams).
            requested = info_dict.get('requested_formats') or []
            if requested:
                video_url, audio_url = self._split_streams(requested)

            # Fallback 1: a single resolved URL (already muxed).
            if not video_url:
                top_url = info_dict.get('url')
                if top_url:
                    video_url, audio_url = top_url, None

            # Fallback 2: scan all available formats for playable manifests.
            if not video_url:
                candidates = [
                    f for f in (info_dict.get('formats') or [])
                    if f.get('protocol') in ('m3u8_native', 'm3u8', 'http_dash_segments')
                ]
                video_url, audio_url = self._split_streams(reversed(candidates))

            if not video_url:
                raise RuntimeError("Could not find a valid stream URL (M3U8/DASH) for this video.")

            return {
                'title': info_dict.get('title', 'Unknown Title'),
                'is_live': info_dict.get('is_live', False),
                'stream_url': video_url,
                'audio_url': audio_url,
                'duration': info_dict.get('duration'),
                'description': info_dict.get('description'),
                'http_headers': info_dict.get('http_headers', {})
            }
