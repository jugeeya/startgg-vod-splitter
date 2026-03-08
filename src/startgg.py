"""
start.gg GraphQL client: fetch event sets and filter by station.
Uses the same unauthenticated endpoint as the start.gg website (no API token).
"""
import requests
from typing import List, Optional, Any

# Same endpoint the start.gg site uses; no auth required
API_URL = "https://www.start.gg/api/-/gql"

REQUEST_TIMEOUT = 20.0

EVENT_SETS_QUERY = """
query EventQuery($slug: String!, $page: Int!) {
  event(slug: $slug) {
    id
    name
    sets(
      page: $page
      perPage: 50
      sortType: RECENT
    ) {
      pageInfo {
        totalPages
      }
      nodes {
        id
        startedAt
        completedAt
        fullRoundText
        winnerId
        station {
          number
        }
        games {
          selections {
            entrant {
              id
              name
            }
            character {
              name
            }
          }
        }
      }
    }
  }
}
"""


def fetch_event_sets(slug: str) -> dict:
    """
    Fetch event and all its sets from start.gg (no API token), with pagination.
    Returns the raw 'data' dict with event.sets.nodes merged across all pages.
    """
    headers = {
        "Content-Type": "application/json",
        "client-version": "20",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
    }
    all_nodes: List[dict] = []
    event_info = None  # id, name from first page
    page = 1
    total_pages = 1

    while page <= total_pages:
        payload = {
            "operationName": "EventQuery",
            "variables": {"slug": slug, "page": page},
            "query": EVENT_SETS_QUERY,
        }
        last_error = None
        for _ in range(5):
            r = requests.post(API_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
            if r.status_code == 200:
                out = r.json()
                if "errors" in out and out["errors"]:
                    raise RuntimeError("GraphQL errors: " + str(out["errors"]))
                if "data" not in out or not out["data"] or "event" not in out["data"]:
                    raise RuntimeError("No event in response. Check event slug.")
                data = out["data"]
                ev = data.get("event") or {}
                if event_info is None:
                    event_info = {"id": ev.get("id"), "name": ev.get("name")}
                sets_container = ev.get("sets") or {}
                page_info = sets_container.get("pageInfo") or {}
                total_pages = page_info.get("totalPages") or 1
                nodes = sets_container.get("nodes") or []
                all_nodes.extend(nodes)
                break
            last_error = r
        else:
            raise RuntimeError(f"Request failed after retries (last status {last_error.status_code}). Check event slug.")
        page += 1

    return {
        "event": {
            **(event_info or {}),
            "sets": {"nodes": all_nodes},
        }
    }


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
