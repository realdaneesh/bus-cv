# BUS-CV: Mobile Urban Intelligence System

> **SIH Hackathon Prototype — Phase 2: Real Video + YOLO Edge AI**

BUS-CV is an AI-powered mobile urban intelligence prototype. **BUS_01** is equipped with a road-facing camera, real Ultralytics YOLO computer vision, GPS tracking, a real-time event system, and a command center dashboard.

## Pipeline Architecture

```
VIDEO FILE (edge-ai/videos/*.mp4)
              │
              ▼
    OpenCV VideoCapture
              │
              ▼
   Ultralytics YOLO (yolo11n.pt)
              │
   ┌──────────┴─────────────────────────┐
   ▼                                    ▼
Live Frame Detections          Aggregated Window (5s)
(car, motorcycle, bus, truck)           │
   │                                    ▼
   ├─► HUD Frame Annotation       POST /api/traffic
   │   (Bounding boxes + HUD)           │
   │   │                                ▼
   │   ▼                         SQLite Database
   │   Thread-Safe Frame Buffer         │
   │   │                                ▼
   │   ▼                         Command Center
   │   GET /api/video/stream     Traffic Intelligence
   │   (Live MJPEG Stream)
   │
   ▼
Live Intelligence Telemetry
(Live Counts, FPS, GPS)
```

## Project Structure

```
bus-cv/
├── backend/         # FastAPI + SQLAlchemy + SQLite
│   └── app/
│       ├── main.py
│       ├── models.py       # Bus, UrbanEvent, TrafficObservation
│       ├── schemas.py      # Pydantic validation (telemetry & provenance)
│       ├── routers/        # bus, events, analytics, monitoring, video
│       └── services/
│           ├── runtime_state.py    # Thread-safe frame buffer & telemetry
│           ├── monitoring.py       # Thread lifecycle & stop event manager
│           ├── event_processor.py  # Confidence + spatial/temporal dedup
│           └── seed.py             # BUS_01 + baseline data seeder
│
├── frontend/        # Vite + React 18 + TypeScript + Tailwind CSS
│   └── src/
│       ├── pages/          # CommandCenter, LiveIntelligence (MJPEG stream),
│       │                   # UrbanMap, UrbanIssues, TrafficIntelligence
│       ├── components/     # Sidebar, Header, Badges, Loaders
│       ├── services/api.ts # Typed backend API client
│       └── types/index.ts  # TypeScript types
│
└── edge-ai/         # Python Edge AI pipeline
    ├── processor.py        # OpenCV VideoCapture & pipeline orchestrator
    ├── detector.py         # Ultralytics YOLO (yolo11n.pt) & HUD annotation
    ├── gps_simulator.py    # Urban route simulator
    ├── event_sender.py     # Fast backend client with in-process fallback
    └── videos/             # Place real road traffic MP4 videos here
```

## Quick Start

### 1. Run Backend Server
```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Backend API: http://localhost:8000
Interactive Docs: http://localhost:8000/docs

### 2. Run Frontend Command Center
```powershell
cd frontend
npm run dev
```
Frontend UI: http://localhost:5173

### 3. Place Video & Start Monitoring
1. Place any road traffic video file at:
   ```
   edge-ai/videos/urban_road_sample.mp4
   ```
   *(A pipeline verification clip is provided out-of-the-box).*
2. Open http://localhost:5173/live and click **Start Monitoring**.
3. Watch the live annotated YOLO detection stream (`car`, `motorcycle`, `bus`, `truck`) and live vehicle counts.
4. Click **Stop Monitoring** to cleanly release OpenCV and GPU/CPU resources.

## Running Tests
```powershell
python tests/test_phase2_cv.py
```
