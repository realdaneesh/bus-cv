import asyncio
import cv2
import numpy as np
import logging
from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse, JSONResponse
from app.services.monitoring import monitoring_service
from app.services.runtime_state import runtime_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video", tags=["Video Stream"])


def _create_placeholder_jpeg(text: str = "BUS-CV · INITIALIZING CAMERA FEED") -> bytes:
    img = np.zeros((360, 640, 3), dtype=np.uint8)
    img[:] = (18, 24, 38)
    cv2.putText(img, text, (70, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 212, 232), 1, cv2.LINE_AA)
    _, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    return buf.tobytes()


async def frame_generator():
    """
    Asynchronous generator yielding live multipart MJPEG frames from the shared runtime frame buffer.
    Consumes already-processed frames; does NOT execute duplicate YOLO inference.
    Handles client disconnects and pauses gracefully without blocking threads.
    """
    try:
        placeholder_bytes = _create_placeholder_jpeg()
        has_sent_initial = False

        while monitoring_service.is_running():
            jpeg_bytes = runtime_state.get_latest_jpeg()
            if not jpeg_bytes and not has_sent_initial:
                jpeg_bytes = placeholder_bytes
                has_sent_initial = True

            if jpeg_bytes:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpeg_bytes)).encode() + b"\r\n\r\n" +
                    jpeg_bytes + b"\r\n"
                )
            await asyncio.sleep(0.04)  # ~25 FPS pacing asynchronously
    except (asyncio.CancelledError, GeneratorExit):
        logger.debug("MJPEG client disconnected from video stream.")
    except Exception as e:
        logger.warning(f"Exception in MJPEG frame generator: {e}")


@router.get("/stream")
async def video_stream():
    """
    Live MJPEG stream endpoint for BUS-CV.
    Streams annotated frames (bounding boxes + vehicle classifications + HUD)
    from the single active Edge AI processor directly to the browser <img> element.
    """
    if not monitoring_service.is_running():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "OFFLINE",
                "message": "Edge AI monitoring pipeline is offline. Start monitoring to activate video stream."
            }
        )

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
