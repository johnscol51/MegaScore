# time_scoring.py

# =========================================================
#  TIME CONVERSION HELPERS
# =========================================================

def time_to_seconds(tstr):
    """Convert HH:MM:SS to integer seconds."""
    h, m, s = tstr.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def seconds_to_time(sec):
    """Convert seconds to HH:MM:SS (zero padded)."""
    sec = max(0, int(sec))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


# =========================================================
#  CLOSEST APPROACH TIME
# =========================================================

def find_closest_time(lat0, lon0, fixes):
    """
    Given a target lat/lon and a list of fixes:
        fixes = [(timestamp_str, lat, lon), ...]
    return the timestamp of the fix closest to the target.
    """
    best = None
    best_t = None

    for t, lat, lon in fixes:
        d = (lat - lat0)**2 + (lon - lon0)**2
        if best is None or d < best:
            best = d
            best_t = t

    return best_t


# =========================================================
#  SINGLE POINT TIMING SCORE (with 5‑second grace)
# =========================================================

def compute_single_timing(expected_sec, actual_sec, max_score):
    diff = abs(actual_sec - expected_sec)
    if diff <= 5:
        penalty = 0
    else:
        penalty = (diff - 5) * 3

    score = max(0, max_score - penalty)
    return int(round(score))


# =========================================================
#  MAIN TIMING ENGINE
# =========================================================

def compute_timing_scores(
    sp_time_str,
    gs_kph,
    mode,
    max_score,
    taskpoints,
    fixes,
    hit_map,
    sp_actual_time=None,   # NEW
):
    """
    Compute timing scores for a list of TaskPoint objects.
    """

    results = {}

    sp_declared_sec = time_to_seconds(sp_time_str)

    sp_obj = next((tp for tp in taskpoints if tp.name == "SP"), None)
    if sp_obj is None:
        return {tp.name: {"score": 0, "expected": ""} for tp in taskpoints}

    if mode == "None":
        return {tp.name: {"score": 0, "expected": ""} for tp in taskpoints}

    # -----------------------------------------------------
    # Determine SP reference time
    # -----------------------------------------------------
    if mode == "fixed":
        sp_ref_sec = sp_declared_sec

        actual_sp_t = find_closest_time(sp_obj.lat, sp_obj.lon, fixes)
        actual_sp_sec = time_to_seconds(actual_sp_t)

        results["SP"] = {
            "score": compute_single_timing(sp_ref_sec, actual_sp_sec, max_score),
            "expected": seconds_to_time(sp_ref_sec),
        }

    elif mode == "SP":
        # If SP was never hit, no timing scores can be computed
        if not sp_actual_time or ":" not in sp_actual_time:
            return {tp.name: {"score": 0, "expected": ""} for tp in taskpoints}

        # Safe: SP time exists and is valid
        sp_ref_sec = time_to_seconds(sp_actual_time)

        results["SP"] = {
            "score": 0,
            "expected": seconds_to_time(sp_ref_sec),
        }

    # -----------------------------------------------------
    # Score all other points
    # -----------------------------------------------------
    for tp in taskpoints:
        if tp.name == "SP":
            continue

        if not hit_map.get(tp.name, False):
            results[tp.name] = {"score": 0, "expected": ""}
            continue

        if tp.distance_km <= 0:
            results[tp.name] = {"score": 0, "expected": ""}
            continue

        travel_sec = (tp.distance_km / gs_kph) * 3600
        expected_sec = sp_ref_sec + round(travel_sec)

        actual_t = find_closest_time(tp.lat, tp.lon, fixes)
        actual_sec = time_to_seconds(actual_t)

        results[tp.name] = {
            "score": compute_single_timing(expected_sec, actual_sec, max_score),
            "expected": seconds_to_time(expected_sec),
        }

    return results
