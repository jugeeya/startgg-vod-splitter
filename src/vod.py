"""
VOD timing: recording start from file or user, compute cut list from set times.
"""
import os
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

# --- Timezone / local time helpers ---
def _local_tz():
    """System local timezone (for display and picker)."""
    return datetime.now().astimezone().tzinfo


def format_iso_to_local(iso_str: Optional[str], fmt: str = "%Y-%m-%d %I:%M:%S %p") -> str:
    """Convert an ISO timestamp from the API to local time string for display."""
    dt = parse_iso(iso_str)
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(_local_tz())
    return local.strftime(fmt)


def utc_from_local(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    """Build a UTC datetime from local date/time (e.g. from date picker)."""
    local = datetime(year, month, day, hour, minute, 0, tzinfo=_local_tz())
    return local.astimezone(timezone.utc)


# start.gg may return ISO 8601 strings or Unix timestamps (int/float)
def parse_iso(s) -> Optional[datetime]:
    if s is None:
        return None
    try:
        if isinstance(s, (int, float)):
            return datetime.fromtimestamp(s, tz=timezone.utc)
        if not isinstance(s, str) or not s.strip():
            return None
        s = s.strip()
        # Handle Z and +00:00
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except (ValueError, TypeError, OSError):
        return None


def sanitize_filename(name: str, max_len: int = 120) -> str:
    """Make a string safe for use as a filename."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:max_len] if len(name) > max_len else name or "clip"


def get_vod_start_from_file(path: str) -> Optional[datetime]:
    """
    Use file creation time as recording start (UTC).
    Fallback: modification time.
    """
    if not path or not os.path.isfile(path):
        return None
    try:
        stat = os.stat(path)
        # Prefer birth time (creation) on macOS/Windows; fallback to mtime
        ts = getattr(stat, "st_birthtime", None) or stat.st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except OSError:
        return None


def get_vod_start_from_file_local(path: str) -> Optional[Tuple[int, int, int, int, int]]:
    """Return (year, month, day, hour, minute) in local time for the file's creation time."""
    dt = get_vod_start_from_file(path)
    if dt is None:
        return None
    local = dt.astimezone(_local_tz())
    return (local.year, local.month, local.day, local.hour, local.minute)


def compute_cuts(
    sets: List[dict],
    recording_start: datetime,
    display_name_fn,
) -> List[Tuple[float, float, str]]:
    """
    Given sets (with startedAt, completedAt) and recording_start (timezone-aware),
    return list of (start_seconds, end_seconds, suggested_filename).
    """
    out = []
    for i, s in enumerate(sets):
        started = parse_iso(s.get("startedAt"))
        completed = parse_iso(s.get("completedAt"))
        if started is None or completed is None:
            continue
        # Normalize to UTC if needed
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if completed.tzinfo is None:
            completed = completed.replace(tzinfo=timezone.utc)
        start_sec = max(0.0, (started - recording_start).total_seconds())
        end_sec = max(start_sec, (completed - recording_start).total_seconds())
        label = display_name_fn(s)
        base = sanitize_filename(f"{label} - Set {i + 1}")
        out.append((start_sec, end_sec, base))
    return out


def export_cut_list_json(cuts: List[Tuple[float, float, str]], output_path: str, vod_path: str = ""):
    """Write cut list as JSON for use by other tools."""
    import json
    items = [
        {"start_sec": s, "end_sec": e, "filename": name, "vod_path": vod_path}
        for s, e, name in cuts
    ]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)


def export_cut_list_csv(cuts: List[Tuple[float, float, str]], output_path: str):
    """Write cut list as CSV: start_sec,end_sec,filename (for Lossless Cut or manual use)."""
    import csv
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["start_sec", "end_sec", "filename"])
        for s, e, name in cuts:
            w.writerow([s, e, name])


def split_vod_with_ffmpeg(vod_path: str, cuts: List[Tuple[float, float, str]], output_dir: str):
    """
    Run ffmpeg to produce one file per cut. Returns list of (success, message) per cut.
    Requires ffmpeg in PATH. Output files are named {suggested_name}.mp4 in output_dir.
    """
    import subprocess
    results = []
    for start_sec, end_sec, base_name in cuts:
        duration = end_sec - start_sec
        out_path = os.path.join(output_dir, f"{base_name}.mp4")
        try:
            proc = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss", str(start_sec),
                    "-i", vod_path,
                    "-t", str(duration),
                    "-c", "copy",
                    out_path,
                ],
                capture_output=True,
                timeout=600,
            )
            if proc.returncode != 0:
                err = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
                err = err.split("\n")[-5:] if err else []  # last few lines often have the real error
                results.append((False, "\n".join(err) if err else f"ffmpeg exited with code {proc.returncode}"))
            else:
                results.append((True, out_path))
        except FileNotFoundError:
            results.append((False, "ffmpeg not found. Install ffmpeg and add it to PATH."))
        except subprocess.TimeoutExpired:
            results.append((False, "ffmpeg timed out after 10 minutes."))
        except Exception as e:
            results.append((False, str(e)))
    return results
