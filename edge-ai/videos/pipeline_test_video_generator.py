"""
BUS-CV — Pipeline Test Video Generator Utility

NOTE: This is a pipeline verification utility only.
It generates a valid test MP4 video file to verify that OpenCV VideoCapture,
frame decoding, loop handling, and MJPEG streaming are operational.
It is NOT a substitute for real road traffic video footage.
For real vehicle detection demonstrations, place actual road video in:
edge-ai/videos/urban_road_sample.mp4
"""

import os
import cv2
import numpy as np

def generate_test_video(output_path: str = "urban_road_sample.mp4", duration_seconds: int = 5, fps: int = 25):
    """Generates a small test video clip for pipeline connectivity tests."""
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)

    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = duration_seconds * fps
    print(f"[TestVideoGenerator] Generating pipeline test clip: {output_path} ({total_frames} frames)")

    for frame_idx in range(total_frames):
        # Create road-like perspective background
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (35, 45, 55)  # Dark asphalt

        # Road boundaries and lane markers
        cv2.line(frame, (100, height), (260, 180), (200, 200, 200), 3)
        cv2.line(frame, (540, height), (380, 180), (200, 200, 200), 3)

        # Dashed center line
        offset = (frame_idx * 6) % 40
        for y in range(180 + offset, height, 40):
            cv2.line(frame, (320, y), (320, min(height, y + 20)), (0, 215, 255), 2)

        # Draw a simulated vehicle shape with realistic car dimensions
        car_x = int(220 + 30 * np.sin(frame_idx * 0.1))
        car_y = int(260 + (frame_idx * 3) % (height - 300))
        cv2.rectangle(frame, (car_x, car_y), (car_x + 70, car_y + 45), (180, 60, 40), -1)
        cv2.rectangle(frame, (car_x + 10, car_y + 10), (car_x + 60, car_y + 35), (230, 220, 210), -1)

        # Test pattern banner
        cv2.putText(
            frame,
            "PIPELINE TEST CLIP - REPLACE WITH REAL ROAD FOOTAGE",
            (25, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 212, 232),
            1,
            cv2.LINE_AA
        )

        out.write(frame)

    out.release()
    print(f"[TestVideoGenerator] Created test clip: {output_path} ({os.path.getsize(output_path)} bytes)")

if __name__ == "__main__":
    out_file = os.path.join(os.path.dirname(__file__), "urban_road_sample.mp4")
    generate_test_video(out_file)
