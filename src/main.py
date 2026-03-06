"""
Start.gg VOD Splitter – GUI entrypoint.
Run: python -m src.main  or  python src/main.py
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

try:
    import customtkinter as ctk
    HAS_CTK = False
except ImportError:
    HAS_CTK = False

try:
    from tkcalendar import DateEntry
    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False

from . import config as app_config
from . import startgg
from . import vod


def run_gui():
    if HAS_CTK:
        # ctk.set_appearance_mode("light")
        # ctk.set_default_color_theme("blue")
        root = ctk.CTk()
        root.title("Start.gg VOD Splitter")
        root.minsize(720, 640)
    else:
        root = tk.Tk()
        root.title("Start.gg VOD Splitter")
        root.minsize(720, 640)
        root.configure(bg="#e8e8e8")
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(".", padding=4)
        style.configure("TFrame", background="#e8e8e8")
        style.configure("TLabel", background="#e8e8e8", padding=(0, 2))
        # Unify all buttons: same look in every frame (avoids mismatched outlines on macOS)
        style.configure(
            "TButton",
            padding=(12, 6),
            relief="flat",
            borderwidth=1,
            background="#d0d0d0",
        )
        style.map(
            "TButton",
            background=[("active", "#b8b8b8"), ("pressed", "#a0a0a0")],
            relief=[("pressed", "sunken"), ("active", "raised")],
        )

    # State
    event_data = {"raw": None, "sets": []}  # raw API data, list of set nodes for selected station
    cuts = []  # list of (start_sec, end_sec, filename)
    recording_start_dt = None

    # --- Settings row ---
    if HAS_CTK:
        frame_settings = ctk.CTkFrame(root, fg_color="transparent")
    else:
        frame_settings = ttk.Frame(root, padding=(12, 8))
    frame_settings.pack(fill="x", padx=12, pady=8)

    ttk.Label(frame_settings, text="Event slug:").pack(side="left", padx=(0, 6))
    slug_var = tk.StringVar(value=app_config.load_settings().get("event_slug", ""))
    slug_entry = ttk.Entry(frame_settings, textvariable=slug_var, width=55)
    slug_entry.pack(side="left", fill="x", expand=True, padx=4)

    ttk.Label(frame_settings, text="API token:").pack(side="left", padx=(12, 4))
    token_var = tk.StringVar(value=app_config.load_settings().get("api_token", ""))
    token_entry = ttk.Entry(frame_settings, textvariable=token_var, width=24, show="*")
    token_entry.pack(side="left", padx=4)

    def save_settings():
        app_config.save_settings(
            api_token=token_var.get().strip(),
            event_slug=slug_var.get().strip(),
            tournament_name=tournament_name_var.get().strip(),
        )
        messagebox.showinfo("Settings", "Settings saved.")

    ttk.Button(frame_settings, text="Save settings", command=save_settings).pack(side="left", padx=8)

    # --- Tournament name (used in video titles: "Tournament | Match | Round") ---
    if HAS_CTK:
        frame_tournament = ctk.CTkFrame(root, fg_color="transparent")
    else:
        frame_tournament = ttk.Frame(root, padding=(12, 2))
    frame_tournament.pack(fill="x", padx=12, pady=2)
    ttk.Label(frame_tournament, text="Tournament name:").pack(side="left", padx=(0, 6))
    tournament_name_var = tk.StringVar(value=app_config.load_settings().get("tournament_name", ""))
    ttk.Entry(frame_tournament, textvariable=tournament_name_var, width=50).pack(side="left", fill="x", expand=True, padx=4)
    ttk.Label(frame_tournament, text="(e.g. The Hangout #1)").pack(side="left", padx=4)

    # --- Fetch + Station + VOD row ---
    if HAS_CTK:
        frame_fetch = ctk.CTkFrame(root, fg_color="transparent")
    else:
        frame_fetch = ttk.Frame(root, padding=(12, 6))
    frame_fetch.pack(fill="x", padx=12, pady=6)

    status_var = tk.StringVar(value="Enter slug and token, then Fetch sets.")

    def fetch_sets():
        slug = slug_var.get().strip()
        token = token_var.get().strip()
        if not slug or not token:
            status_var.set("Please set event slug and API token.")
            return
        status_var.set("Fetching...")
        root.update_idletasks()
        try:
            data = startgg.fetch_event_sets(slug, token)
            event_data["raw"] = data
            stations = set()
            for n in (data.get("event") or {}).get("sets", {}).get("nodes") or []:
                num = (n.get("station") or {}).get("number")
                if num is not None:
                    stations.add(num)
            station_list = sorted(stations)
            station_combo["values"] = station_list
            if station_list:
                station_combo.set(station_list[0])
            event_data["sets"] = []
            cuts.clear()
            update_sets_display()
            update_cuts_display()
            status_var.set(f"Loaded event. Stations: {station_list or 'none'}")
        except Exception as e:
            status_var.set("Error: " + str(e))
            messagebox.showerror("Fetch error", str(e))

    ttk.Button(frame_fetch, text="Fetch sets", command=fetch_sets).pack(side="left", padx=(0, 8))
    ttk.Label(frame_fetch, text="Station:").pack(side="left", padx=(8, 4))
    station_combo = ttk.Combobox(frame_fetch, values=[], width=6, state="readonly")
    station_combo.pack(side="left", padx=4)

    def _on_station_changed(*args):
        if event_data["raw"] is not None:
            update_sets_display()
            update_cuts_display()

    station_combo.bind("<<ComboboxSelected>>", _on_station_changed)

    vod_path_var = tk.StringVar()

    def pick_vod():
        path = filedialog.askopenfilename(
            title="Select VOD file",
            filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi"), ("All", "*.*")],
        )
        if path:
            vod_path_var.set(path)
            auto_fill_recording_start()

    ttk.Button(frame_fetch, text="Choose VOD…", command=pick_vod).pack(side="left", padx=(12, 4))
    vod_entry = ttk.Entry(frame_fetch, textvariable=vod_path_var, width=40)
    vod_entry.pack(side="left", fill="x", expand=True, padx=4)

    # --- Recording start: date picker + time (local time) ---
    if HAS_CTK:
        frame_rec = ctk.CTkFrame(root, fg_color="transparent")
    else:
        frame_rec = ttk.Frame(root, padding=(12, 6))
    frame_rec.pack(fill="x", padx=12, pady=4)

    ttk.Label(frame_rec, text="Recording start (local):").pack(side="left", padx=(0, 6))
    rec_hour_var = tk.StringVar(value="12")
    rec_minute_var = tk.StringVar(value="0")
    rec_second_var = tk.StringVar(value="0")
    rec_start_fallback_var = tk.StringVar()  # used when HAS_CALENDAR is False

    if HAS_CALENDAR:
        from datetime import date
        _today = date.today()
        rec_date_entry = DateEntry(frame_rec, width=12, year=_today.year, month=_today.month, day=_today.day)
        rec_date_entry.pack(side="left", padx=2)
    else:
        rec_date_entry = ttk.Entry(frame_rec, textvariable=rec_start_fallback_var, width=22)
        rec_date_entry.pack(side="left", padx=2)
        ttk.Label(frame_rec, text="(YYYY-MM-DD HH:MM:SS)").pack(side="left", padx=2)

    ttk.Label(frame_rec, text="Time:").pack(side="left", padx=(8, 2))
    hour_spin = ttk.Spinbox(frame_rec, from_=0, to=23, width=3, textvariable=rec_hour_var)
    hour_spin.pack(side="left", padx=2)
    ttk.Label(frame_rec, text=":").pack(side="left")
    min_spin = ttk.Spinbox(frame_rec, from_=0, to=59, width=3, textvariable=rec_minute_var)
    min_spin.pack(side="left", padx=2)
    ttk.Label(frame_rec, text=":").pack(side="left")
    sec_spin = ttk.Spinbox(frame_rec, from_=0, to=59, width=3, textvariable=rec_second_var)
    sec_spin.pack(side="left", padx=2)

    def auto_fill_recording_start():
        path = vod_path_var.get().strip()
        if not path or not os.path.isfile(path):
            return
        tup = vod.get_vod_start_from_file_local(path)
        if not tup:
            return
        y, mo, d, h, mi, sec = tup
        rec_hour_var.set(str(h))
        rec_minute_var.set(str(mi))
        rec_second_var.set(str(sec))
        if HAS_CALENDAR:
            rec_date_entry.set_date(__import__("datetime").date(y, mo, d))
        else:
            rec_start_fallback_var.set(f"{y:04d}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}:{sec:02d}")

    ttk.Button(frame_rec, text="Use file time", command=auto_fill_recording_start).pack(side="left", padx=(10, 4))

    # --- Compute cuts ---
    def get_recording_start():
        path = vod_path_var.get().strip()
        if HAS_CALENDAR:
            try:
                d = rec_date_entry.get_date()
                h = int(rec_hour_var.get())
                mi = int(rec_minute_var.get())
                sec = int(rec_second_var.get())
                if 0 <= h <= 23 and 0 <= mi <= 59 and 0 <= sec <= 59:
                    return vod.utc_from_local(d.year, d.month, d.day, h, mi, sec)
            except (ValueError, TypeError):
                pass
            if path:
                return vod.get_vod_start_from_file(path)
            return None
        else:
            override = rec_start_fallback_var.get().strip()
            if override:
                dt = vod.parse_iso(override)
                if dt is None:
                    try:
                        from datetime import datetime
                        s = override.strip()
                        if len(s) >= 19:
                            dt_naive = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
                        else:
                            dt_naive = datetime.strptime(s[:16], "%Y-%m-%d %H:%M")
                        sec = getattr(dt_naive, "second", 0)
                        return vod.utc_from_local(dt_naive.year, dt_naive.month, dt_naive.day, dt_naive.hour, dt_naive.minute, sec)
                    except ValueError:
                        pass
                if dt and dt.tzinfo is None:
                    from datetime import timezone
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            if path:
                return vod.get_vod_start_from_file(path)
            return None

    def compute_cuts():
        station_val = station_combo.get()
        try:
            station_num = int(station_val) if station_val else None
        except ValueError:
            station_num = None
        if event_data["raw"] is None:
            status_var.set("Fetch sets first.")
            return
        sets = startgg.get_sets_by_station(event_data["raw"], station_num)
        event_data["sets"] = sets
        rec_start = get_recording_start()
        if rec_start is None:
            status_var.set("Set VOD path and/or recording start (or click Use file time).")
            return
        global recording_start_dt
        recording_start_dt = rec_start
        cuts.clear()
        cuts.extend(vod.compute_cuts(sets, rec_start, startgg.set_display_name, tournament_name_var.get().strip()))
        update_cuts_display()
        status_var.set(f"Computed {len(cuts)} cuts for station {station_val}.")

    # --- Sets from start.gg (what the GraphQL query returned) ---
    if HAS_CTK:
        frame_sets = ctk.CTkFrame(root, fg_color="transparent")
    else:
        frame_sets = ttk.Frame(root, padding=(12, 4))
    frame_sets.pack(fill="both", expand=True, padx=12, pady=4)

    sets_label_var = tk.StringVar(value="Sets from start.gg (fetch event and pick station)")
    ttk.Label(frame_sets, textvariable=sets_label_var).pack(anchor="w")
    sets_text = ScrolledText(frame_sets, height=8, width=90, state="disabled", wrap="none", font=("Menlo", 10) if not HAS_CTK else None)
    sets_text.pack(fill="both", expand=True, pady=(2, 6))
    if not HAS_CTK:
        sets_text.configure(bg="#fff", relief="flat", borderwidth=1)

    def update_sets_display():
        sets_text.config(state="normal")
        sets_text.delete("1.0", "end")
        station_val = station_combo.get()
        try:
            station_num = int(station_val) if station_val else None
        except ValueError:
            station_num = None
        if event_data["raw"] is None:
            sets_label_var.set("Sets from start.gg — fetch event first")
            sets_text.insert("end", "Enter slug and API token, then click Fetch sets.")
        else:
            sets_label_var.set(f"Sets from start.gg — station {station_val or 'all'}")
            sets_for_station = startgg.get_sets_by_station(event_data["raw"], station_num)
            if not sets_for_station:
                sets_text.insert("end", f"No sets with startedAt/completedAt for station {station_val or 'all'}.")
            else:
                for i, s in enumerate(sets_for_station, 1):
                    name = startgg.set_display_name(s)
                    round_text = (s.get("fullRoundText") or "").strip()
                    started = vod.format_iso_to_local(s.get("startedAt"))
                    completed = vod.format_iso_to_local(s.get("completedAt"))
                    st = (s.get("station") or {}).get("number")
                    # [Tournament] Match - Round
                    tournament = tournament_name_var.get().strip()
                    if tournament:
                        title_line = f"[{tournament}] {name}"
                    else:
                        title_line = name
                    if round_text:
                        title_line = f"{title_line} - {round_text}"
                    sets_text.insert("end", f"{i}. {title_line}\n")
                    sets_text.insert("end", f"   started: {started}  completed: {completed}  station: {st}\n\n")
        sets_text.config(state="disabled")

    # --- Cuts list ---
    if HAS_CTK:
        frame_cuts_header = ctk.CTkFrame(root, fg_color="transparent")
    else:
        frame_cuts_header = ttk.Frame(root, padding=(12, 4))
    frame_cuts_header.pack(fill="x", padx=12, pady=(4, 2))
    ttk.Label(frame_cuts_header, text="Computed cuts (start sec, end sec, filename):").pack(side="left", padx=(0, 8))
    ttk.Button(frame_cuts_header, text="Compute cuts", command=compute_cuts).pack(side="left")
    cuts_text = ScrolledText(root, height=6, width=90, state="disabled", wrap="none", font=("Menlo", 10) if not HAS_CTK else None)
    cuts_text.pack(fill="x", padx=12, pady=4)
    if not HAS_CTK:
        cuts_text.configure(bg="#fff", relief="flat", borderwidth=1)

    def update_cuts_display():
        cuts_text.config(state="normal")
        cuts_text.delete("1.0", "end")
        if not cuts:
            cuts_text.insert("end", "Choose VOD, set recording start if needed, then click Compute cuts.")
        else:
            for s, e, name in cuts:
                cuts_text.insert("end", f"{s:.1f} – {e:.1f}  {name}\n")
        cuts_text.config(state="disabled")

    # --- Export / Split row ---
    if HAS_CTK:
        frame_actions = ctk.CTkFrame(root, fg_color="transparent")
    else:
        frame_actions = ttk.Frame(root, padding=(12, 8))
    frame_actions.pack(fill="x", padx=12, pady=8)

    def export_json():
        if not cuts:
            messagebox.showwarning("Export", "Compute cuts first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            vod.export_cut_list_json(cuts, path, vod_path_var.get().strip())
            status_var.set("Exported JSON: " + path)
            messagebox.showinfo("Export", "Cut list saved.")

    def export_csv():
        if not cuts:
            messagebox.showwarning("Export", "Compute cuts first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            vod.export_cut_list_csv(cuts, path)
            status_var.set("Exported CSV: " + path)
            messagebox.showinfo("Export", "Cut list saved.")

    def do_ffmpeg_split():
        if not cuts:
            messagebox.showwarning("Split", "Compute cuts first.")
            return
        vpath = vod_path_var.get().strip()
        if not vpath or not os.path.isfile(vpath):
            messagebox.showwarning("Split", "Choose a valid VOD file.")
            return
        out_dir = filedialog.askdirectory(title="Output folder for split clips")
        if not out_dir:
            return
        status_var.set("Splitting with ffmpeg…")
        root.update_idletasks()
        try:
            results = vod.split_vod_with_ffmpeg(vpath, cuts, out_dir)
            ok = sum(1 for r in results if r[0])
            status_var.set(f"Split: {ok}/{len(results)} clips written to {out_dir}")
            msg = f"Created {ok} of {len(results)} clips in\n{out_dir}"
            failures = [(i + 1, r[1]) for i, r in enumerate(results) if not r[0]]
            if failures:
                msg += "\n\nErrors:\n" + "\n\n".join(f"Clip {n}: {err}" for n, err in failures)
                messagebox.showerror("Split (with errors)", msg)
            else:
                messagebox.showinfo("Split", msg)
        except Exception as e:
            status_var.set("Split error: " + str(e))
            messagebox.showerror("Split error", str(e))

    ttk.Button(frame_actions, text="Export cut list (JSON)", command=export_json).pack(side="left", padx=(0, 6))
    ttk.Button(frame_actions, text="Export cut list (CSV)", command=export_csv).pack(side="left", padx=6)
    ttk.Button(frame_actions, text="Split with ffmpeg", command=do_ffmpeg_split).pack(side="left", padx=6)

    # --- Status ---
    ttk.Label(root, textvariable=status_var, foreground="gray").pack(anchor="w", padx=12, pady=(0, 8))

    # Load saved slug/token already set in vars
    root.mainloop()


if __name__ == "__main__":
    run_gui()
