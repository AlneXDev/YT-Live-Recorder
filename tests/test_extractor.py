import pytest
from unittest.mock import patch, MagicMock
from core.extractor import YTExtractor

@patch('core.extractor.yt_dlp.YoutubeDL')
def test_get_stream_info(mock_ydl):
    mock_instance = MagicMock()
    mock_ydl.return_value.__enter__.return_value = mock_instance
    
    # Mock extract_info return value
    mock_instance.extract_info.return_value = {
        'title': 'Test Live Stream',
        'is_live': True,
        'url': 'https://manifest.googlevideo.com/api/manifest/hls_variant/test.m3u8',
        'duration': None
    }
    
    extractor = YTExtractor()
    info = extractor.get_stream_info('https://youtube.com/watch?v=test')
    
    assert info['title'] == 'Test Live Stream'
    assert info['is_live'] is True
    assert info['stream_url'] == 'https://manifest.googlevideo.com/api/manifest/hls_variant/test.m3u8'

@patch('core.extractor.yt_dlp.YoutubeDL')
def test_get_stream_info_with_cookies_file(mock_ydl):
    mock_instance = MagicMock()
    mock_ydl.return_value.__enter__.return_value = mock_instance
    
    mock_instance.extract_info.return_value = {
        'title': 'Test Live Stream',
        'is_live': True,
        'url': 'https://manifest.googlevideo.com/api/manifest/hls_variant/test.m3u8',
        'duration': None
    }
    
    extractor = YTExtractor(cookies_file='/path/to/cookies.txt')
    info = extractor.get_stream_info('https://youtube.com/watch?v=test')
    
    mock_ydl.assert_called_once_with({
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'format': 'bestvideo+bestaudio/best',
        'cookiefile': '/path/to/cookies.txt'
    })

@patch('core.extractor.yt_dlp.YoutubeDL')
def test_get_stream_info_with_formats(mock_ydl):
    mock_instance = MagicMock()
    mock_ydl.return_value.__enter__.return_value = mock_instance
    
    mock_instance.extract_info.return_value = {
        'title': 'Test Live Stream',
        'is_live': True,
        'formats': [
            {'protocol': 'https', 'url': 'https://video.mp4'},
            {'protocol': 'm3u8_native', 'url': 'https://manifest.m3u8'},
        ]
    }
    
    extractor = YTExtractor()
    info = extractor.get_stream_info('https://youtube.com/watch?v=test')
    
    assert info['stream_url'] == 'https://manifest.m3u8'

@patch('core.extractor.yt_dlp.YoutubeDL')
def test_get_stream_info_no_url(mock_ydl):
    mock_instance = MagicMock()
    mock_ydl.return_value.__enter__.return_value = mock_instance
    
    mock_instance.extract_info.return_value = {
        'title': 'Test Live Stream',
        'is_live': True,
        'formats': []
    }
    
    extractor = YTExtractor()
    with pytest.raises(RuntimeError, match="Could not find a valid stream URL"):
        extractor.get_stream_info('https://youtube.com/watch?v=test')

@patch('core.extractor.yt_dlp.YoutubeDL')
def test_get_stream_info_with_quality(mock_ydl):
    mock_instance = MagicMock()
    mock_ydl.return_value.__enter__.return_value = mock_instance
    
    mock_instance.extract_info.return_value = {
        'title': 'Test Live Stream',
        'is_live': True,
        'url': 'https://manifest.googlevideo.com/api/manifest/hls_variant/test.m3u8',
        'duration': None
    }
    
    extractor = YTExtractor()
    extractor.get_stream_info('https://youtube.com/watch?v=test', quality='720p')
    
    mock_ydl.assert_called_once_with({
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best[height<=720]/best'
    })
