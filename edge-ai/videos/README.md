# BUS-CV Video Input Directory

Place your road traffic video here for processing by the BUS-CV Edge AI pipeline.

## Default File

The pipeline defaults to looking for:
```
edge-ai/videos/urban_road_sample.mp4
```

## Supported Formats

- `.mp4` (H.264 / AVC recommended)
- `.avi`
- `.mkv`
- `.mov`

## Custom Video Path

You can point to any video file using the `VIDEO_SOURCE` environment variable:

```bash
# In Windows PowerShell:
$env:VIDEO_SOURCE="C:\path\to\your\traffic_video.mp4"

# Or configure in backend/.env:
VIDEO_SOURCE=edge-ai/videos/your_traffic_video.mp4
```

## Video Looping

Control whether the video automatically loops or stops at the end:
```env
VIDEO_LOOP=true   # Loops automatically (ideal for continuous demos)
VIDEO_LOOP=false  # Cleanly shuts down monitoring when video reaches the end
```

## Missing Video Handling

If no valid video file is found at the specified path, the Edge AI processor:
1. Emits a clear logged error explaining the exact missing path.
2. Updates its status to `ERROR`.
3. Reports the error state through `/api/monitoring/status`.
4. Will NOT falsely report "AI ONLINE".
