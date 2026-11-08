import os
import pytest
from unittest.mock import patch, MagicMock
from core.recorder import FFmpegRecorder

@patch('core.recorder.subprocess.Popen')
@patch('core.recorder.subprocess.run')
def test_ffmpeg_recorder_success(mock_run, mock_popen):
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stderr.read.side_effect = ["", ""]
    mock_popen.return_value = mock_process
    
    mock_run_res = MagicMock()
    mock_run_res.returncode = 0
    mock_run.return_value = mock_run_res
    
    with patch('core.recorder.os.path.exists', return_value=True), \
         patch('core.recorder.os.path.getsize', return_value=1024), \
         patch('core.recorder.os.remove') as mock_remove, \
         patch('core.recorder.shutil.move') as mock_move, \
         patch('core.recorder.open', create=True):
         
        recorder = FFmpegRecorder(output_file='test.mp4', duration=10, force=True)
        success = recorder.record('https://stream.url')
        
        assert success is True
        assert len(recorder.recorded_parts) == 1
        mock_run.assert_called_once()
        assert 'copy' in mock_run.call_args[0][0]

@patch('core.recorder.subprocess.Popen')
@patch('core.recorder.subprocess.run')
def test_ffmpeg_recorder_multiple_parts(mock_run, mock_popen):
    mock_process_1 = MagicMock()
    mock_process_1.returncode = 1
    mock_process_1.stderr.read.side_effect = ["", ""]
    
    mock_process_2 = MagicMock()
    mock_process_2.returncode = 0
    mock_process_2.stderr.read.side_effect = ["", ""]
    
    mock_popen.side_effect = [mock_process_1, mock_process_2]
    
    mock_run_res = MagicMock()
    mock_run_res.returncode = 0
    mock_run.return_value = mock_run_res
    
    with patch('core.recorder.os.path.exists', return_value=True), \
         patch('core.recorder.os.path.getsize', return_value=1024), \
         patch('core.recorder.os.remove') as mock_remove, \
         patch('core.recorder.open', create=True):
         
        mock_refresh = MagicMock(return_value='https://new.stream.url')
        recorder = FFmpegRecorder(output_file='test.mp4', duration=10, refresh_url_func=mock_refresh)
        success = recorder.record('https://stream.url')
        
        assert success is True
        assert len(recorder.recorded_parts) == 2
        mock_run.assert_called_once()
        assert 'concat' in mock_run.call_args[0][0]
        assert mock_remove.call_count >= 3
        mock_refresh.assert_called_once()
