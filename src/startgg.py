"""
start.gg GraphQL client: fetch event sets and filter by station.
"""
import requests
from typing import List, Optional, Any

API_URL = "https://api.start.gg/gql/alpha"

EVENT_SETS_QUERY = """
query EventQuery($slug: String) {
  event(slug: $slug) {
    id
    name
    sets {
      nodes {
        id
        startedAt
        completedAt
        games {
          selections {
            character {
              name
            }
            entrant {
              name
              id
            }
          }
        }
        station {
          number
        }
        winnerId
        fullRoundText
      }
    }
  }
}
"""


def fetch_event_sets(slug: str, api_token: str) -> dict:
    """
    Fetch event and its sets from start.gg.
    Returns the raw 'data' dict or raises on error.
    """
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    payload = {"query": EVENT_SETS_QUERY, "variables": {"slug": slug}}
    r = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    out = r.json()
    if "errors" in out and out["errors"]:
        raise RuntimeError("GraphQL errors: " + str(out["errors"]))
    if "data" not in out or not out["data"] or "event" not in out["data"]:
        raise RuntimeError("No event in response. Check slug and API token.")
    return out["data"]


def get_sets_by_station(data: dict, station_number: Optional[int]) -> List[dict]:
    """
    From API data, return list of set nodes.
    If station_number is set, only include sets for that station.
    Sorts by startedAt so order matches VOD timeline.
    """
    event = data.get("event") or {}
    sets_container = event.get("sets") or {}
    nodes = sets_container.get("nodes") or []
    if station_number is not None:
        nodes = [n for n in nodes if (n.get("station") or {}).get("number") == station_number]
    # Sort by startedAt (handle None)
    nodes = [n for n in nodes if n.get("startedAt") and n.get("completedAt")]
    nodes.sort(key=lambda n: (n["startedAt"] or ""))
    return nodes


def set_display_name(set_node: dict) -> str:
    """Build a short label for a set from entrants and characters."""
    games = set_node.get("games") or []
    if not games:
        return f"Set {set_node.get('id', '?')}"
    # Use first game selections; could be extended to show multiple games
    selections = games[0].get("selections") or []
    parts = []
    seen = set()
    for s in selections:
        entrant = (s.get("entrant") or {}).get("name") or "?"
        character = (s.get("character") or {}).get("name") or "?"
        key = entrant
        if key in seen:
            continue
        seen.add(key)
        parts.append(f"{entrant} ({character})")
    if len(parts) >= 2:
        return " vs. ".join(parts)
    return " vs. ".join(parts) if parts else f"Set {set_node.get('id', '?')}"
