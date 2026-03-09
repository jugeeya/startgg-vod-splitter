# Start.gg VOD Splitter

Small desktop app for turning a **full-station VOD** (e.g. from OBS) into **per-set clips** using start.gg set times. Use one PC/station per run: pick the event, station number, and VOD file; the app computes cut times and can export a cut list (CSV/JSON) or split the file with ffmpeg.

Works on **Windows, macOS, and Linux** (Python 3.10+).

**macOS (Homebrew):** If you get `No module named '_tkinter'`, install Tk support for your Python version, then try again:
```bash
brew install python-tk@3.14   # match your Python version, e.g. 3.11 → python-tk@3.11
```
If that formula doesn’t exist, install `tcl-tk` and reinstall Python: `brew install tcl-tk` then `brew reinstall python@3.14`.

## Quick start

1. **Install Python 3.10+** and create a virtualenv (recommended):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
   Minimum: `pip install requests`. The app will use standard Tkinter. Install `customtkinter` as well for a darker, modern look.

2. **Run the app**
   - **macOS / Linux:** From project root, `python3 -m src.main` (or `./run.sh`).
   - **Windows:** From project root in Command Prompt or PowerShell: `py -3 -m src.main` or `python -m src.main`. Or double‑click `run.bat` (after installing Python and dependencies).

3. **Workflow**
   - Enter **event slug** (e.g. `tournament/joshu-s-test-tourney/event/rivals-of-aether-ii-singles`). (No API token needed — the app uses the same public endpoint as the start.gg site.)
   - Click **Fetch sets** to load the event from start.gg.
   - Choose **Station** (the station number for this VOD).
   - Click **Choose VOD…** and select your full recording file.
   - Click **Use file time** to fill recording start from the file’s creation time (or type an ISO time in **Recording start** if you need to override).
   - Click **Compute cuts** to see the list of segments.
   - **Export cut list (CSV/JSON)** for use in Lossless Cut or other tools, or **Split with ffmpeg** to generate one clip per set (requires [ffmpeg](https://ffmpeg.org/) in PATH).

## Running on Windows

- Install Python from [python.org](https://www.python.org/downloads/) (check “Add Python to PATH”).
- Open Command Prompt or PowerShell in the project folder, then:
  ```bat
  py -3 -m venv .venv
  .venv\Scripts\activate
  pip install -r requirements.txt
  python -m src.main
  ```
- Or run `run.bat` (tries `py -3` then `python`). If the window closes with an error, open it from Command Prompt so you can see the message.

## Optional: ffmpeg

For **Split with ffmpeg**, install ffmpeg and ensure it’s on your PATH:

- **Windows**: e.g. [ffmpeg releases](https://www.gyan.dev/ffmpeg/builds/) or `winget install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg` / `sudo dnf install ffmpeg`

Output clips are written as `.mp4` (stream copy, no re-encode) in the folder you choose.

## Time zones

start.gg returns `startedAt` / `completedAt` in ISO 8601 (usually UTC). The app treats your **recording start** as the same timezone (or UTC). If you use **Use file time**, the file’s creation time is interpreted as UTC. If your recording PC uses local time, set **Recording start** manually to the correct UTC time (or same zone as the API) so cuts line up.

## completedAt and duration warning

On start.gg, **completedAt** can be updated when a set is edited later (e.g. character corrections). The API does not expose a separate “actual” completion time, so the app cannot fix this automatically. Each set row shows an uneditable **Duration** (start → end). If a duration is longer than 45 minutes, a red warning appears: *“Set too long; may have incorrect end time”* — adjust the set’s **End** date/time manually if the match was shorter, then click **Refresh durations** to update.

## Building the Windows exe

To build a standalone `.exe` (no Python install needed on the target PC):

1. **Locally (Windows):** Install Python 3.11+, then from the project root:
   ```bat
   pip install -r requirements.txt pyinstaller
   pyinstaller --noconfirm StartGG-VOD-Splitter.spec
   ```
   The exe is written to `dist/StartGG-VOD-Splitter.exe`. Copy it (and optionally ffmpeg) to any Windows machine.

2. **GitHub Actions:** On every push to `main`/`master`, a workflow builds the exe and uploads it as an artifact. In your repo: **Actions** → **Build Windows exe** → select the latest run → **Artifacts** → download **StartGG-VOD-Splitter-Windows** (contains the exe). You can also trigger the workflow manually from the **Actions** tab (**Run workflow**).

## Project layout

- `run.py` – entry point for PyInstaller (also `python -m src.main`)
- `StartGG-VOD-Splitter.spec` – PyInstaller spec for the Windows exe
- `src/main.py` – GUI
- `src/startgg.py` – start.gg GraphQL client
- `src/vod.py` – VOD start time and cut list / ffmpeg split
- `PLAN.md` – design and scope

## License

Use and modify as you like.
