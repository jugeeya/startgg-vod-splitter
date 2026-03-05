# Start.gg VOD Splitter – Plan

## Goal
Reduce manual work when turning full-station VODs into per-set clips for YouTube: use start.gg set times + one VOD file per station to produce split segments (and later metadata for upload).

## Use case (your flow)
1. **During event**: 4+ PCs record full VODs with OBS; each PC = one station number in start.gg.
2. **After event**: One VOD per station; you want segments that match each set (start/end) with names like "Player1 (Char) vs Player2 (Char)".
3. **Optional**: Upload to YouTube with that metadata (can be a later phase).

## What the app will do (v1)

| Input | Description |
|-------|-------------|
| **Event slug** | e.g. `tournament/joshu-s-test-tourney/event/rivals-of-aether-ii-singles` |
| **start.gg API token** | In settings; used for GraphQL API (personal token from start.gg) |
| **Station number** | Which station this VOD is from (integer), so we only use sets for that station |
| **VOD file** | The full recording (e.g. from OBS) for that station |
| **Recording start time (optional)** | Override if file creation time isn’t reliable |

**Logic:**
1. Fetch event sets from start.gg (your existing GraphQL query; we filter by `station.number` in the app).
2. Assume the VOD “timeline” starts at either the file’s creation time or the user-set “recording started at.”
3. For each set on that station:  
   - Start offset in VOD = `set.startedAt - recordingStart`  
   - End offset in VOD = `set.completedAt - recordingStart`  
4. Output:
   - **Cut list** (e.g. CSV or JSON): `start_sec`, `end_sec`, `output_filename` (from players + characters) for use in Lossless Cut or similar.
   - **Optional**: Call **ffmpeg** to actually split the VOD into one file per set (so you can upload without opening Lossless Cut).

**Naming:**  
From `games[].selections` we get entrant names and character names; we’ll build names like  
`Player1 (CharacterA) vs Player2 (CharacterB) - Set 5`  
(sanitized for filenames).

## What we’re not doing in v1
- **YouTube upload** – You can add it later (e.g. YouTube Data API + OAuth). v1 focuses on “correct segments + metadata.”
- **Multiple VODs at once** – One VOD + one station per run keeps the UI simple; you can run the app once per station.

## Tech choices

| Layer | Choice | Reason |
|-------|--------|--------|
| Language | Python 3.10+ | Simple, runs on Windows/Mac/Linux |
| GUI | **Tkinter** (stdlib) or **CustomTkinter** | Tkinter = no extra deps; CustomTkinter = nicer look with one pip install |
| HTTP | `requests` | Simple GraphQL POST to start.gg |
| Config | JSON file in app dir or user config dir | Store API token, last event slug |
| Video | Export cut list (CSV/JSON) + optional **ffmpeg** (subprocess) | Fits “use with Lossless Cut” or “split for me” |

## start.gg API notes
- **Endpoint:** `https://api.start.gg/graphql`
- **Auth:** Header `Authorization: Bearer <token>` (personal API token from start.gg).
- **Query:** Your event query returns all sets with `startedAt`, `completedAt`, `station.number`, `games[].selections` (entrant, character). We **don’t** filter by station in GraphQL (unless start.gg adds that); we fetch all sets and filter by `station.number` in the app.
- **Slug:** You pass the full event slug (e.g. `tournament/.../event/...`) as variable `$slug`.

## Project layout (target)

```
startgg-vod-splitter/
├── README.md           # How to run, get API token, optional ffmpeg
├── requirements.txt    # requests, customtkinter (or none if pure tkinter)
├── PLAN.md             # This file
├── src/
│   ├── __init__.py
│   ├── main.py         # GUI entrypoint
│   ├── startgg.py      # GraphQL client, fetch sets, parse response
│   ├── vod.py          # VOD start time from file (or user), compute cut list
│   └── config.py       # Load/save settings (token, last slug)
└── config.json         # Created at runtime (or in user config dir)
```

## Next steps (implementation order)
1. **Project scaffold** – `requirements.txt`, `src/`, `config.py`, `README.md`.
2. **start.gg client** – `startgg.py`: run GraphQL query, return list of sets (with station, times, games/selections).
3. **VOD logic** – `vod.py`: get recording start from file or user; given sets for one station, compute `(start_sec, end_sec, suggested_filename)` per set.
4. **GUI** – `main.py`: settings (token), event slug, fetch, station selector, VOD file picker, optional “recording started at,” show table of cuts, “Export cut list” and “Split with ffmpeg” (if ffmpeg in PATH).
5. **Polish** – Error messages, timezone note in UI (start.gg times are typically UTC; we’ll assume recording time is same TZ or user enters in same TZ).

If you’re good with this plan, next step is implementing the scaffold and start.gg client, then VOD math, then the GUI.
