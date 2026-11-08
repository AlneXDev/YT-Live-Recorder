<div align="center">

# YT Live Recorder

**Record YouTube live streams without babysitting them.**

A small Python CLI that grabs a live stream from start to finish — or just the chunk you want — and leaves you with a clean MP4.

<br>

[![Made by Alne](https://img.shields.io/badge/made_by-Alne-8A2BE2?style=flat-square)](https://github.com/AlneXDev)
[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-2ea44f?style=flat-square)](LICENSE)
[![Last commit](https://img.shields.io/github/last-commit/AlneXDev/yt-live-recorder?style=flat-square)](https://github.com/AlneXDev/yt-live-recorder/commits/main)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-6e7681?style=flat-square)]()

</div>

---

[Why](#why-this-exists) · [Features](#features) · [Audio](#audio--compatibility) · [Requirements](#requirements) · [Install](#install) · [Usage](#usage) · [How it works](#how-it-works) · [Notes](#notes--limitations) · [Testing](#testing) · [Credits](#credits) · [License](#license)

## Why this exists

I record a lot of live streams, and most tools fall over the moment the connection hiccups. YouTube also rotates the stream URL every so often, so a recording that starts fine just… stops.

This one is built around that problem. It keeps FFmpeg alive through short drops, fetches a fresh URL when the stream goes away, and stitches the pieces back together when it's done. You start it and walk away.

## Features

| Feature | What it does |
|---|---|
| **Auto-reconnect** | FFmpeg's HLS reconnect flags for blips, plus exponential backoff (5s → 10s → 20s, up to 6 tries) for real drops. |
| **Fresh URLs** | When the stream URL expires, it asks `yt-dlp` for a new one before reconnecting. |
| **Lossless video** | Video is copied bit-for-bit. Only the audio is re-encoded to AAC so the file plays everywhere. |
| **Clean Ctrl+C** | Interrupt it any time — the parts are still merged and remuxed into a playable MP4. |
| **Quality presets** | `720p`, `1080p`, `1440p`, `2160p`, plus optional `--transcode` for scaling and letterboxing. |
| **Cookies** | Pull them from your browser or a `cookies.txt` for private and members-only streams. |
| **Readable progress** | A `rich` progress bar with elapsed time and ETA. |
| **Debug log** | Everything is written to `yt-live-recorder.log`. |

## Audio & compatibility

A few deliberate choices so the files actually play everywhere:

- **Both streams are captured.** Live YouTube serves video and audio as two separate HLS manifests, so the recorder pulls both and maps them into one file.
- **Valid AAC.** Audio is encoded to AAC-LC, which keeps the MP4 `esds` box (`DecoderSpecificInfo` / AudioSpecificConfig) correct for strict players.
- **Standard, seekable MP4.** Output is remuxed with `+faststart` — no fragmented MP4, `moov` up front, works in browsers, phones, and TVs.
- **`.part` temp files.** In-progress chunks use `.part`, so they can't be mistaken for finished `.mp4` recordings.

## Requirements

- Python 3.9+
- FFmpeg on your `PATH`

```bash
# macOS
brew install ffmpeg

# Debian / Ubuntu
sudo apt install ffmpeg

# Windows
winget install Gyan.FFmpeg
```

## Install

```bash
git clone https://github.com/AlneXDev/yt-live-recorder.git
cd yt-live-recorder
pip install -r requirements.txt
```

## Usage

```bash
python yt_live_recorder.py -u URL [options]
```

| Option | What it does |
|---|---|
| `-u`, `--url` | Stream URL (required) |
| `-t`, `--time` | `full` (default), `1h`, `45m`, `30s`, `1h30m`, or raw seconds |
| `-o`, `--output` | Output file or directory |
| `--quality` | `720p`, `1080p` (default), `1440p`, `2160p` |
| `-f`, `--force` | Overwrite an existing file |
| `--cookies-from-browser` | e.g. `chrome`, `firefox`, `edge` |
| `--cookies` | Path to a `cookies.txt` |
| `--transcode` | Re-encode video instead of copying it |

**Record until the stream ends**

```bash
python yt_live_recorder.py -u "https://www.youtube.com/watch?v=VIDEO_ID"
```

**Record the next 90 minutes**

```bash
python yt_live_recorder.py -u "https://www.youtube.com/watch?v=VIDEO_ID" -t 1h30m
```

**Pick a name and overwrite if needed**

```bash
python yt_live_recorder.py -u "https://www.youtube.com/watch?v=VIDEO_ID" -o "show.mp4" -f
```

**Members-only stream, logged in through Chrome**

```bash
python yt_live_recorder.py -u "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-from-browser chrome
```

Files default to `youtube_live_<title>_<timestamp>.mp4` in the current folder.

## How it works

`yt-dlp` resolves the watch page into live manifests. The recorder hands the video and audio URLs to FFmpeg, watches its output for progress, and retries with a refreshed URL if the stream drops. Recordings are written as `.part` files and merged losslessly (stream copy) at the end.

```
yt_live_recorder.py   CLI, args, logging
core/extractor.py     yt-dlp wrapper -> video + audio URLs
core/recorder.py      FFmpeg subprocess, retries, merge
core/utils.py         duration parsing, ffmpeg check, filenames
```

## Notes & limitations

- Default mode copies video and re-encodes audio. That's intentional — a straight AAC copy can produce files some players refuse to play.
- It doesn't use your GPU. `--transcode` runs `libx264` on the CPU. For plain recording that's fine: the stream arrives in real time, so there's nothing to accelerate.
- YouTube live only. VODs will technically extract, but this isn't a general-purpose downloader.
- Reconnects keep the quality you started with; changing `--quality` mid-run isn't supported.

## Testing

```bash
pytest tests/
```

13 tests covering duration parsing, extraction, and the FFmpeg argument and merge logic.

## Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — the actual heavy lifting
- [FFmpeg](https://ffmpeg.org/) — recording, muxing, merging
- [rich](https://github.com/Textualize/rich) — the progress bar
- Built and maintained by [Alne](https://github.com/AlneXDev)

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

For personal, educational archival use. Recording copyrighted streams may break YouTube's Terms of Service or local law. Make sure you have the right to record something before you do.
