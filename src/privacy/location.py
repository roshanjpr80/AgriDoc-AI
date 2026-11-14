"""Location coarsening for outbreak reporting.

Privacy rule: only district-level aggregates are stored. GPS coordinates are
rounded to the district centroid and the raw lat/lon is discarded immediately.
"""
from __future__ import annotations

from typing import Optional, Tuple

# District centroids (lat, lon) for major Indian agro-climatic regions.
# Used only to bucket a GPS point into a district; the raw point is never
# stored. Source: India Meteorological Department district gazetteer.
DISTRICT_CENTROIDS = {
    "Punjab_Ludhiana": (30.9010, 75.8573),
    "Punjab_Amritsar": (31.6340, 74.8723),
    "Haryana_Karnal": (29.6975, 76.9870),
    "Haryana_Hisar": (29.1492, 75.7217),
    "Uttar_Pradesh_Kanpur_Nagar": (26.4499, 80.3319),
    "Uttar_Pradesh_Lucknow": (26.8467, 80.9462),
    "Uttar_Pradesh_Varanasi": (25.3176, 82.9739),
    "Maharashtra_Nagpur": (21.1458, 79.0882),
    "Maharashtra_Akola": (20.7033, 76.9975),
    "Maharashtra_Aurangabad": (19.8762, 75.3433),
    "Karnataka_Bengaluru_Urban": (12.9716, 77.5946),
    "Karnataka_Belagavi": (15.8497, 74.4977),
    "Karnataka_Mysuru": (12.2958, 76.6394),
    "Tamil_Nadu_Coimbatore": (11.0168, 76.9558),
    "Tamil_Nadu_Madurai": (9.9252, 78.1198),
    "Tamil_Nadu_Thanjavur": (10.7870, 79.1378),
    "Telangana_Hyderabad": (17.3850, 78.4867),
    "Telangana_Warangal": (17.9784, 79.6010),
    "Andhra_Pradesh_Guntur": (16.3067, 80.4365),
    "Andhra_Pradesh_Vijayawada": (16.5062, 80.6480),
    "Gujarat_Surat": (21.1702, 72.8311),
    "Gujarat_Anand": (22.5645, 72.9289),
    "Rajasthan_Jaipur": (26.9124, 75.7873),
    "Rajasthan_Kota": (25.2138, 75.8648),
    "Bihar_Patna": (25.5941, 85.1376),
    "West_Bengal_Kolkata": (22.5726, 88.3639),
    "Odisha_Bhubaneswar": (20.2961, 85.8245),
    "Assam_Guwahati": (26.1445, 91.7362),
}


def coarsen_location(lat: float, lon: float) -> Optional[str]:
    """Map a GPS point to the nearest known district centroid.

    Returns the district key (e.g. 'Karnataka_Bengaluru_Urban') or None if
    the point is more than 200 km from every centroid (likely outside India
    or a bad reading).
    """
    best_key = None
    best_dist = float("inf")
    for key, (clat, clon) in DISTRICT_CENTROIDS.items():
        # Haversine distance in km.
        d = _haversine(lat, lon, clat, clon)
        if d < best_dist:
            best_dist = d
            best_key = key
    if best_dist > 200:
        return None
    return best_key


def is_valid_district(district: str) -> bool:
    return district in DISTRICT_CENTROIDS


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import radians, sin, cos, sqrt, atan2

    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    return 2 * r * atan2(sqrt(a), sqrt(1 - a))