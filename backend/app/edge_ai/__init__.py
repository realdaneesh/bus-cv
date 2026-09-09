"""
BUS-CV Edge AI runtime package.

Vendored from the repository-level `edge-ai/` folder so that Railway can deploy
the monitoring + AI pipeline with Root Directory = `backend` only, using proper
package imports (e.g. `from app.edge_ai.processor import VideoProcessor`).

Submodules are imported explicitly (not eagerly re-exported here) so that
lightweight modules like `app.edge_ai.gps_simulator` can be imported without
forcing the heavy CV inference stack (opencv / torch / ultralytics) to load.
"""