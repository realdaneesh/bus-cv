"""
Edge AI - GPS Road-Route Simulator (Mumbai Corridor)

Simulates an onboard GPS receiver for BUS_01 along a PLANNED, ROAD-REALISTIC
corridor in Mumbai: Hiranandani Gardens -> JVLR (south bank of Powai Lake) ->
Saki Vihar Road -> Saki Naka -> Marol / Andheri East -> loop back.

Design guarantees:
- Every waypoint is on / immediately adjacent to a roadway corridor.
- The route is DENSELY spaced (no huge straight-line jumps between landmarks).
- The route stays SOUTH of Powai Lake (max latitude < 19.108) so the bus NEVER
  appears to travel across the lake or water.
- Movement between waypoints is continuously interpolated by distance at a
  plausible urban speed, producing a smooth, believable journey and a heading.
- The full planned route is exported (MUMBAI_ROUTE) for the Urban Map polyline.

GPS TELEMETRY IS SIMULATED. The bus is not using physical GPS hardware. This is
an intentional, labelled demonstration behaviour.
"""

import time
import math
from typing import Dict, Any, List

# Approximate meters per degree at Mumbai (~19.1 deg latitude)
_M_PER_DEG_LAT = 111320.0

# Powai Lake rough bounding box (the route must stay OUT of this).
POWAI_LAKE_BBOX = {
    "lat_min": 19.108,
    "lat_max": 19.122,
    "lon_min": 72.903,
    "lon_max": 72.925,
}


def _meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate great-circle-ish distance in meters for short spans."""
    dlat_deg = lat2 - lat1
    mean_lat = (lat1 + lat2) / 2.0
    dlon_deg = (lon2 - lon1) * math.cos(mean_lat * math.pi / 180.0)
    return math.hypot(dlat_deg * _M_PER_DEG_LAT, dlon_deg * _M_PER_DEG_LAT)


class GPSSimulator:
    # Dense, road-following planned route [lat, lon] controls.
    # Corridor: Hiranandani -> JVLR (south of Powai Lake) -> Saki Vihar ->
    # Saki Naka -> Marol/Andheri East -> loop back to Hiranandani.
    MUMBAI_ROUTE: List[List[float]] = [
        [19.1058, 72.9055], [19.1056, 72.9035], [19.1053, 72.9015],
        [19.1050, 72.8995], [19.1048, 72.8975], [19.1046, 72.8955],
        [19.1044, 72.8935], [19.1042, 72.8915], [19.1040, 72.8895],
        [19.1038, 72.8875], [19.1036, 72.8855],
        # Saki Vihar Road -> Saki Naka (heading south-west)
        [19.1025, 72.8840], [19.1015, 72.8825], [19.1005, 72.8810],
        [19.0995, 72.8795], [19.0988, 72.8780], [19.0983, 72.8763],
        # West to Marol / Andheri East
        [19.0995, 72.8740], [19.1008, 72.8720], [19.1018, 72.8700],
        [19.1028, 72.8682],
        # North / loop through Andheri East -> Chakala and back east on JVLR
        [19.1045, 72.8675], [19.1060, 72.8670], [19.1073, 72.8680],
        [19.1076, 72.8700], [19.1070, 72.8725], [19.1060, 72.8750],
        [19.1050, 72.8780], [19.1053, 72.8810], [19.1058, 72.8840],
        [19.1062, 72.8870], [19.1064, 72.8900], [19.1063, 72.8930],
        [19.1061, 72.8960], [19.1059, 72.8990], [19.1058, 72.9020],
        [19.1058, 72.9055],
    ]

    def __init__(self, waypoints: List[Dict[str, float]] = None):
        if waypoints:
            self.DEFAULT_WAYPOINTS = waypoints
        else:
            speeds = [24, 26, 28, 30, 30, 30, 30, 30, 30, 30, 28,
                      27, 26, 25, 24, 22, 20, 22, 24, 25, 26,
                      27, 28, 26, 24, 22, 22, 24, 26, 28, 30, 30,
                      30, 30, 28, 26, 25]
            self.DEFAULT_WAYPOINTS = [
                {"lat": p[0], "lon": p[1],
                 "speed": speeds[min(i, len(speeds) - 1)],
                 "name": f"Route point {i}"}
                for i, p in enumerate(self.MUMBAI_ROUTE)
            ]
        self.waypoints = self.DEFAULT_WAYPOINTS
        self.seg = 1  # index of the NEXT waypoint we are travelling toward
        self.cur_lat = float(self.waypoints[0]["lat"])
        self.cur_lon = float(self.waypoints[0]["lon"])
        self.heading = 0.0
        self.last_update_time = time.time()
        self.loops = 0

    def _snap_to(self, wp: Dict[str, float]) -> None:
        self.cur_lat = float(wp["lat"])
        self.cur_lon = float(wp["lon"])

    def _set_heading(self, lat2: float, lon2: float) -> None:
        dlat = lat2 - self.cur_lat
        dlon = (lon2 - self.cur_lon) * math.cos(self.cur_lat * math.pi / 180.0)
        self.heading = (math.degrees(math.atan2(dlon, dlat)) + 360.0) % 360.0

    def get_current_location(self) -> Dict[str, Any]:
        wp = self.waypoints[self.seg - 1] if self.seg > 0 else self.waypoints[0]
        return {
            "latitude": round(self.cur_lat, 6),
            "longitude": round(self.cur_lon, 6),
            "speed": round(wp["speed"], 1),
            "heading": round(self.heading, 1),
            "waypoint_name": "Mumbai Road Route (simulated)",
            "status": "SIMULATED_MUMBAI_ROAD_ROUTE",
            "gps_mode": "GPS TELEMETRY — SIMULATED MUMBAI ROAD ROUTE",
            "timestamp": time.time()
        }

    def step(self, dt: float = None) -> Dict[str, Any]:
        """
        Advance the simulated bus along the planned route by elapsed time.
        Movement follows the road polyline (interpolated by distance), so the
        bus never teleports between far-apart landmarks or across water.
        """
        now = time.time()
        if dt is None:
            dt = min(max(now - self.last_update_time, 0.4), 10.0)
        self.last_update_time = now

        target = self.waypoints[self.seg]
        speed_mps = target["speed"] * 1000.0 / 3600.0
        remaining_m = speed_mps * dt

        guard = 0
        while remaining_m > 0 and guard < len(self.waypoints) * 2:
            guard += 1
            tgt = self.waypoints[self.seg]
            dist_to_tgt = _meters(self.cur_lat, self.cur_lon, tgt["lat"], tgt["lon"])
            if dist_to_tgt <= 1e-6:
                self._snap_to(tgt)
                self.seg = (self.seg + 1) % len(self.waypoints)
                if self.seg == 1:
                    self.loops += 1
                continue

            if remaining_m >= dist_to_tgt:
                self._set_heading(tgt["lat"], tgt["lon"])
                self._snap_to(tgt)
                remaining_m -= dist_to_tgt
                self.seg = (self.seg + 1) % len(self.waypoints)
                if self.seg == 1:
                    self.loops += 1
            else:
                frac = remaining_m / dist_to_tgt
                self._set_heading(tgt["lat"], tgt["lon"])
                self.cur_lat = self.cur_lat + frac * (tgt["lat"] - self.cur_lat)
                self.cur_lon = self.cur_lon + frac * (tgt["lon"] - self.cur_lon)
                remaining_m = 0.0

        return self.get_current_location()

    def get_planned_route(self) -> List[Dict[str, float]]:
        """Return the planned route as [{'lat':..., 'lon':...}, ...] for map rendering."""
        return [{"lat": p[0], "lon": p[1]} for p in self.MUMBAI_ROUTE]

    @staticmethod
    def route_stays_out_of_lake() -> bool:
        """Sanity check: no planned point inside Powai Lake bounding box."""
        b = POWAI_LAKE_BBOX
        for p in GPSSimulator.MUMBAI_ROUTE:
            if b["lat_min"] < p[0] < b["lat_max"] and b["lon_min"] < p[1] < b["lon_max"]:
                return False
        return True