# BUS-CV — Start Project Guide

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm

---

## 1. Backend Setup

```powershell
# Navigate to backend directory
cd bus-cv/backend

# Create virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Copy env config
cp .env.example .env

# Start the backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000
API docs: http://localhost:8000/docs
Health check: http://localhost:8000/health

**On first startup:**
- SQLite database `bus_cv.db` is created automatically
- BUS_01 is seeded with coordinates
- 6 demo urban events are seeded (source=SEED, is_demo_data=true)
- 1 demo traffic observation is seeded

---

## 2. Frontend Setup

```powershell
# Navigate to frontend directory
cd bus-cv/frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend will be available at: http://localhost:5173

---

## 3. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Backend health check |
| GET | `/api/bus/status` | BUS_01 real status |
| GET | `/api/bus/location` | BUS_01 GPS coordinates |
| POST | `/api/bus/location` | Update bus location |
| GET | `/api/events` | List urban events |
| POST | `/api/events` | Create event (via EventProcessor) |
| GET | `/api/events/{id}` | Get specific event |
| PATCH | `/api/events/{id}/resolve` | Resolve event in DB |
| GET | `/api/traffic/current` | Latest traffic observation |
| POST | `/api/traffic` | Store traffic observation |
| GET | `/api/dashboard` | Computed dashboard stats |
| GET | `/api/monitoring/status` | Edge AI monitoring state |
| POST | `/api/monitoring/start` | Start monitoring pipeline |
| POST | `/api/monitoring/stop` | Stop monitoring pipeline |
| GET | `/api/video/stream` | Video stream endpoint (Phase 2) |

---

## 4. Event Processor Rules

Events posted to `POST /api/events` pass through the intelligence layer:

- **Confidence < 0.60** → rejected with HTTP 422
- **Same event type within 35m and 30s** → suppressed as duplicate
- **Priority calculated by backend:**
  - confidence ≥ 0.90 → HIGH
  - confidence ≥ 0.75 → MEDIUM
  - otherwise → LOW

---

## 5. Data Provenance

Every event has:
- `source`: `SEED` | `AI_DETECTION` | `MANUAL_TEST`
- `is_demo_data`: `true` (seeded) | `false` (real AI)

The frontend shows a badge on every event to distinguish demo data from real detections.

---

## 6. Edge AI (Phase 2 Preparation)

```powershell
cd bus-cv/edge-ai

# Ensure backend is running, then:
python processor.py
```

This runs the GPS simulator loop and posts telemetry to the backend.
YOLO/OpenCV video processing will be connected in Phase 2.

---

## 7. Configuration

Edit `backend/.env` (copy from `.env.example`):

```env
DATABASE_URL=sqlite:///./bus_cv.db
CORS_ORIGINS=http://localhost:5173
DETECTION_CONFIDENCE_THRESHOLD=0.60
EVENT_COOLDOWN_SECONDS=30
DUPLICATE_PROXIMITY_METERS=35.0
```
