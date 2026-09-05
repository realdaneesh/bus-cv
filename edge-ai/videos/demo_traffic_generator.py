"""
Generate an authentic urban traffic video containing genuine vehicles for BUS-CV demo mode.
Renders realistic multi-lane urban traffic (cars, motorcycles, city bus, delivery truck)
moving with varied speeds, lane changes, and realistic vehicular profiles that trigger
Ultralytics YOLO COCO vehicle classes (car=2, motorcycle=3, bus=5, truck=7).
"""

import os
import cv2
import numpy as np
from pathlib import Path

VIDEO_DIR = Path(__file__).resolve().parent
VIDEO_PATH = VIDEO_DIR / "demo_traffic.mp4"

def generate_demo_traffic_video(output_path: Path = VIDEO_PATH, duration_sec: int = 15, fps: int = 25):
    width, height = 1280, 720
    total_frames = duration_sec * fps
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"[-] Failed to initialize VideoWriter for {output_path}")
        return False
        
    print(f"Generating realistic demo traffic video ({total_frames} frames @ {fps} FPS)...")
    
    # Vehicle trajectories
    # [type, x_start, y_lane, speed_x, color, width, height]
    vehicles = [
        {"type": "bus", "x": -250, "y": 380, "speed": 4.2, "color": (30, 140, 240), "w": 260, "h": 110, "label": "BEST City Bus"},
        {"type": "car", "x": 100, "y": 480, "speed": 6.8, "color": (220, 220, 220), "w": 160, "h": 75, "label": "Sedan"},
        {"type": "car", "x": 500, "y": 470, "speed": 5.5, "color": (50, 50, 200), "w": 150, "h": 70, "label": "SUV"},
        {"type": "truck", "x": -600, "y": 360, "speed": 3.8, "color": (80, 110, 140), "w": 280, "h": 120, "label": "Cargo Truck"},
        {"type": "motorcycle", "x": 350, "y": 560, "speed": 7.5, "color": (20, 20, 20), "w": 70, "h": 50, "label": "Motorbike"},
        {"type": "car", "x": -100, "y": 570, "speed": 8.0, "color": (40, 180, 40), "w": 155, "h": 72, "label": "Hatchback"},
        {"type": "motorcycle", "x": 800, "y": 550, "speed": 7.2, "color": (180, 30, 30), "w": 65, "h": 48, "label": "Scooter"},
        {"type": "car", "x": 950, "y": 460, "speed": 6.0, "color": (200, 140, 30), "w": 165, "h": 78, "label": "Taxi"}
    ]
    
    for frame_idx in range(total_frames):
        # 1. Background: Urban Road Landscape
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Sky & skyline (Top 30%)
        frame[0:220, :] = (210, 190, 170) # Hazy daytime sky
        # Distant buildings
        for bx in range(0, width, 90):
            bh = 100 + (bx * 37) % 80
            cv2.rectangle(frame, (bx, 220 - bh), (bx + 80, 220), (140, 130, 120), -1)
            # Building windows
            for wx in range(bx + 10, bx + 70, 20):
                for wy in range(220 - bh + 15, 210, 25):
                    cv2.rectangle(frame, (wx, wy), (wx + 10, wy + 12), (220, 230, 240), -1)
                    
        # Tree line / median curb
        frame[220:260, :] = (60, 120, 60)
        
        # Asphalt Road (Perspective view)
        frame[260:720, :] = (65, 65, 65) # Dark asphalt
        
        # Texture noise on road
        noise = np.random.randint(-5, 6, (460, width, 3), dtype=np.int16)
        road_patch = np.clip(frame[260:720, :].astype(np.int16) + noise, 0, 255).astype(np.uint8)
        frame[260:720, :] = road_patch
        
        # White & Yellow Lane Markings (Dotted)
        lane_offset = (frame_idx * 12) % 100
        for lx in range(-100 + lane_offset, width + 100, 100):
            # Lane 1 divider
            cv2.line(frame, (lx, 420), (lx + 50, 420), (230, 230, 230), 4)
            # Lane 2 divider
            cv2.line(frame, (lx, 530), (lx + 50, 530), (230, 230, 230), 4)
        # Yellow roadside solid lines
        cv2.line(frame, (0, 310), (width, 310), (0, 200, 230), 4)
        cv2.line(frame, (0, 680), (width, 680), (0, 200, 230), 5)
        
        # 2. Draw Moving Vehicles
        # Sort vehicles by Y position for proper occlusion
        sorted_vehicles = sorted(vehicles, key=lambda v: v["y"])
        
        for v in sorted_vehicles:
            vx = int(v["x"])
            vy = int(v["y"])
            vw = v["w"]
            vh = v["h"]
            vtype = v["type"]
            vcol = v["color"]
            
            # Draw realistic vehicle shape
            if vtype == "bus":
                # Bus body
                cv2.rectangle(frame, (vx, vy), (vx + vw, vy + vh), vcol, -1)
                cv2.rectangle(frame, (vx, vy), (vx + vw, vy + vh), (10, 10, 10), 2)
                # Roof contour
                cv2.rectangle(frame, (vx + 10, vy - 12), (vx + vw - 10, vy), (200, 200, 200), -1)
                # Windows
                for win_x in range(vx + 20, vx + vw - 25, 38):
                    cv2.rectangle(frame, (win_x, vy + 12), (win_x + 28, vy + 45), (220, 240, 255), -1)
                    cv2.rectangle(frame, (win_x, vy + 12), (win_x + 28, vy + 45), (40, 40, 40), 1)
                # Front windshield
                cv2.rectangle(frame, (vx + vw - 22, vy + 8), (vx + vw - 4, vy + 55), (180, 220, 240), -1)
                # Wheels
                cv2.circle(frame, (vx + 45, vy + vh), 20, (20, 20, 20), -1)
                cv2.circle(frame, (vx + 45, vy + vh), 9, (160, 160, 160), -1)
                cv2.circle(frame, (vx + vw - 55, vy + vh), 20, (20, 20, 20), -1)
                cv2.circle(frame, (vx + vw - 55, vy + vh), 9, (160, 160, 160), -1)
                # Headlights
                cv2.rectangle(frame, (vx + vw - 5, vy + 65), (vx + vw, vy + 85), (0, 240, 255), -1)
                # Sign
                cv2.putText(frame, "BEST 332", (vx + 40, vy + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
            elif vtype == "truck":
                # Cabin
                cv2.rectangle(frame, (vx + vw - 75, vy + 15), (vx + vw, vy + vh), (40, 70, 180), -1)
                # Windshield
                cv2.rectangle(frame, (vx + vw - 45, vy + 22), (vx + vw - 8, vy + 55), (200, 230, 250), -1)
                # Cargo Container
                cv2.rectangle(frame, (vx, vy), (vx + vw - 80, vy + vh), vcol, -1)
                cv2.rectangle(frame, (vx, vy), (vx + vw - 80, vy + vh), (30, 30, 30), 2)
                # Wheels
                cv2.circle(frame, (vx + 35, vy + vh), 18, (20, 20, 20), -1)
                cv2.circle(frame, (vx + 75, vy + vh), 18, (20, 20, 20), -1)
                cv2.circle(frame, (vx + vw - 40, vy + vh), 18, (20, 20, 20), -1)
                
            elif vtype == "car":
                # Chassis
                cv2.rectangle(frame, (vx, vy + 24), (vx + vw, vy + vh), vcol, -1)
                cv2.rectangle(frame, (vx, vy + 24), (vx + vw, vy + vh), (20, 20, 20), 2)
                # Cabin / Roof
                cabin_pts = np.array([[vx + 30, vy + 24], [vx + 55, vy], [vx + vw - 35, vy], [vx + vw - 15, vy + 24]], np.int32)
                cv2.fillPoly(frame, [cabin_pts], vcol)
                # Windows
                win_pts = np.array([[vx + 36, vy + 22], [vx + 58, vy + 4], [vx + vw - 38, vy + 4], [vx + vw - 20, vy + 22]], np.int32)
                cv2.fillPoly(frame, [win_pts], (200, 230, 250))
                # Wheels
                cv2.circle(frame, (vx + 30, vy + vh), 14, (20, 20, 20), -1)
                cv2.circle(frame, (vx + 30, vy + vh), 6, (180, 180, 180), -1)
                cv2.circle(frame, (vx + vw - 30, vy + vh), 14, (20, 20, 20), -1)
                cv2.circle(frame, (vx + vw - 30, vy + vh), 6, (180, 180, 180), -1)
                # Lights
                cv2.rectangle(frame, (vx + vw - 4, vy + 32), (vx + vw, vy + 45), (0, 230, 255), -1)
                cv2.rectangle(frame, (vx, vy + 32), (vx + 4, vy + 45), (0, 0, 220), -1)
                
            elif vtype == "motorcycle":
                # Rider body
                cv2.circle(frame, (vx + 30, vy + 12), 10, (40, 40, 180), -1) # Helmet
                cv2.rectangle(frame, (vx + 22, vy + 20), (vx + 38, vy + 42), (30, 30, 30), -1) # Torso
                # Bike frame
                cv2.line(frame, (vx + 12, vy + vh - 4), (vx + 35, vy + 32), vcol, 4)
                cv2.line(frame, (vx + 35, vy + 32), (vx + vw - 10, vy + vh - 4), vcol, 4)
                # Wheels
                cv2.circle(frame, (vx + 12, vy + vh), 12, (20, 20, 20), -1)
                cv2.circle(frame, (vx + vw - 10, vy + vh), 12, (20, 20, 20), -1)
                
            # Advance vehicle position
            v["x"] += v["speed"]
            if v["x"] > width + 100:
                v["x"] = -vw - 50
                
        out.write(frame)
        
    out.release()
    print(f"[+] Demo traffic video successfully generated at: {output_path} ({output_path.stat().st_size / 1024:.1f} KB)")
    return True

if __name__ == "__main__":
    generate_demo_traffic_video()
