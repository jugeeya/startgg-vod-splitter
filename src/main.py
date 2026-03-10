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

from . import startgg
from . import vod


def run_gui():
    if HAS_CTK:
        # ctk.set_appearance_mode("light")
        # ctk.set_default_color_theme("blue")
        root = ctk.CTk()
        root.title("Start.gg VOD Splitter")
        root.minsize(1150, 640)
        root.geometry("1200x800")
    else:
        root = tk.Tk()
        root.title("Start.gg VOD Splitter")
        root.minsize(1150, 640)
        root.geometry("1200x800")
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

    ttk.Label(frame_settings, text="Event URL or slug:").pack(side="left", padx=(0, 6))
    slug_var = tk.StringVar(value="")
    slug_entry = ttk.Entry(frame_settings, textvariable=slug_var, width=55)
    slug_entry.pack(side="left", fill="x", expand=True, padx=4)

    # --- Tournament name (used in video titles: "Tournament | Match | Round") ---
    if HAS_CTK:
        frame_tournament = ctk.CTkFrame(root, fg_color="transparent")
    else:
        frame_tournament = ttk.Frame(root, padding=(12, 2))
    frame_tournament.pack(fill="x", padx=12, pady=2)
    ttk.Label(frame_tournament, text="Tournament name:").pack(side="left", padx=(0, 6))
    tournament_name_var = tk.StringVar(value="")
    ttk.Entry(frame_tournament, textvariable=tournament_name_var, width=50).pack(side="left", fill="x", expand=True, padx=4)
    ttk.Label(frame_tournament, text="(e.g. The Hangout #1)").pack(side="left", padx=4)

    # --- Fetch + Station + VOD row ---
    if HAS_CTK:
        frame_fetch = ctk.CTkFrame(root, fg_color="transparent")
    else:
        frame_fetch = ttk.Frame(root, padding=(12, 6))
    frame_fetch.pack(fill="x", padx=12, pady=6)

    status_var = tk.StringVar(value="Enter event URL or slug, then Fetch sets.")

    def fetch_sets():
        user_input = slug_var.get().strip()
        if not user_input:
            status_var.set("Please enter event slug or URL.")
            return
        
        # Extract slug pattern: tournament/xxx/event/yyy from anywhere in the string
        slug = user_input
        import re
        match = re.search(r'tournament/[^/\s]+/event/[^/\s]+', user_input)
        if match:
            slug = match.group(0)
        elif user_input.startswith("http://") or user_input.startswith("https://"):
            status_var.set("Invalid start.gg URL. Could not find tournament/event pattern.")
            return
        
        status_var.set("Fetching...")
        root.update_idletasks()
        try:
            data = startgg.fetch_event_sets(slug)
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

    # State for editable sets list: list of (set_node, check_var, title_var)
    sets_ui_rows = []

    def compute_cuts():
        if not sets_ui_rows:
            status_var.set("Fetch sets first and ensure at least one set is checked.")
            return
        rec_start = get_recording_start()
        if rec_start is None:
            status_var.set("Set VOD path and/or recording start (or click Use file time).")
            return
        selection = []
        for row_data in sets_ui_rows:
            set_node, check_var, title_var = row_data[0], row_data[1], row_data[2]
            if not check_var.get():
                continue
            title = title_var.get().strip() or startgg.set_display_name(set_node)
            start_ymdhms = get_ymdhms(row_data[3], row_data[4], row_data[5], row_data[6])
            # Get duration in minutes and seconds
            try:
                duration_min = int(row_data[7].get())
                duration_sec = int(row_data[8].get())
            except (ValueError, IndexError, AttributeError):
                duration_min, duration_sec = 0, 0
            # Calculate end time from start + duration
            if start_ymdhms is not None and (duration_min > 0 or duration_sec > 0):
                from datetime import datetime, timedelta
                start_dt = datetime(*start_ymdhms)
                end_dt = start_dt + timedelta(minutes=duration_min, seconds=duration_sec)
                end_ymdhms = (end_dt.year, end_dt.month, end_dt.day, end_dt.hour, end_dt.minute, end_dt.second)
                selection.append((set_node, title, start_ymdhms, end_ymdhms))
            else:
                selection.append((set_node, title, None, None))
        if not selection:
            status_var.set("Check at least one set to include.")
            return
        global recording_start_dt
        recording_start_dt = rec_start
        cuts.clear()
        cuts.extend(vod.compute_cuts_from_selection(selection, rec_start))
        update_cuts_display()
        status_var.set(f"Computed {len(cuts)} cuts from {len(selection)} selected set(s).")

    # --- Sets from start.gg: editable rows with checkboxes ---
    if HAS_CTK:
        frame_sets = ctk.CTkFrame(root, fg_color="transparent")
    else:
        frame_sets = ttk.Frame(root, padding=(12, 4))
    frame_sets.pack(fill="both", expand=True, padx=12, pady=4)

    sets_label_var = tk.StringVar(value="Sets from start.gg (fetch event and pick station)")
    sets_header_row = ttk.Frame(frame_sets)
    sets_header_row.pack(fill="x")
    ttk.Label(sets_header_row, textvariable=sets_label_var).pack(side="left")

    DURATION_WARN_MINUTES = 45

    def get_ymdhms(date_widget, h_var, m_var, s_var):
        try:
            if hasattr(date_widget, "get_date"):
                d = date_widget.get_date()
                y, mo, day = d.year, d.month, d.day
            else:
                # Plain Entry (used in set rows): .get() returns the date string
                s_str = (date_widget.get() or "").strip()[:10]
                if len(s_str) < 10:
                    return None
                from datetime import datetime
                dt = datetime.strptime(s_str, "%Y-%m-%d")
                y, mo, day = dt.year, dt.month, dt.day
            h, mi, sec = int(h_var.get()), int(m_var.get()), int(s_var.get())
            if 0 <= h <= 23 and 0 <= mi <= 59 and 0 <= sec <= 59:
                return (y, mo, day, h, mi, sec)
        except (ValueError, TypeError, AttributeError):
            pass
        return None

    def update_durations():
        from datetime import datetime
        for row_data in sets_ui_rows:
            try:
                if len(row_data) < 11:
                    continue
                # Get the duration input values
                duration_min_var = row_data[7]
                duration_sec_var = row_data[8]
                duration_label = row_data[9]
                warn_label = row_data[10]
                try:
                    duration_min = int(duration_min_var.get())
                    duration_sec = int(duration_sec_var.get())
                except (ValueError, AttributeError):
                    duration_label.config(text="(invalid)")
                    warn_label.config(text="")
                    continue
                total_sec = duration_min * 60 + duration_sec
                if total_sec <= 0:
                    duration_label.config(text="(no duration)")
                    warn_label.config(text="")
                    continue
                duration_label.config(text="")
                if total_sec > DURATION_WARN_MINUTES * 60:
                    warn_label.config(text=" — Duration too long; verify it's correct", foreground="red")
                else:
                    warn_label.config(text="", foreground="red")
            except Exception:
                if len(row_data) >= 11:
                    row_data[9].config(text="(error)")
                    row_data[10].config(text="")

    ttk.Button(sets_header_row, text="Refresh durations", command=update_durations).pack(side="left", padx=(12, 0))

    # Scrollable container for set rows (vertical + horizontal so duration column is visible)
    sets_canvas = tk.Canvas(frame_sets, highlightthickness=0)
    sets_vscroll = ttk.Scrollbar(frame_sets, orient="vertical", command=sets_canvas.yview)
    sets_hscroll = ttk.Scrollbar(frame_sets, orient="horizontal", command=sets_canvas.xview)
    sets_inner = ttk.Frame(sets_canvas)
    sets_inner.bind("<Configure>", lambda e: sets_canvas.configure(scrollregion=sets_canvas.bbox("all")))
    sets_canvas_window_id = sets_canvas.create_window((0, 0), window=sets_inner, anchor="nw")
    sets_canvas.configure(yscrollcommand=sets_vscroll.set, xscrollcommand=sets_hscroll.set)

    def _on_frame_configure(event):
        sets_canvas.configure(scrollregion=sets_canvas.bbox("all"))

    sets_inner.bind("<Configure>", _on_frame_configure)
    sets_canvas.pack(side="left", fill="both", expand=True, pady=(2, 0))
    sets_vscroll.pack(side="right", fill="y")
    sets_hscroll.pack(side="bottom", fill="x", pady=(2, 0))
    if not HAS_CTK:
        sets_canvas.configure(bg="#fff")

    def update_sets_display():
        for w in sets_inner.winfo_children():
            w.destroy()
        sets_ui_rows.clear()
        station_val = station_combo.get()
        try:
            station_num = int(station_val) if station_val else None
        except ValueError:
            station_num = None
        if event_data["raw"] is None:
            sets_label_var.set("Sets from start.gg — fetch event first")
            ttk.Label(sets_inner, text="Enter event slug, then click Fetch sets.", foreground="gray").pack(anchor="w")
            return
        sets_label_var.set(f"Sets from start.gg — station {station_val or 'all'} (check sets to include, edit titles)")
        sets_for_station = startgg.get_sets_by_station(event_data["raw"], station_num)
        if not sets_for_station:
            ttk.Label(sets_inner, text=f"No sets with startedAt/completedAt for station {station_val or 'all'}.", foreground="gray").pack(anchor="w")
            return
        from datetime import date, datetime, timedelta
        for s in sets_for_station:
            name = startgg.set_display_name(s)
            round_text = (s.get("fullRoundText") or "").strip()
            tournament = tournament_name_var.get().strip()
            if tournament:
                default_title = f"[{tournament}] {name}"
            else:
                default_title = name
            if round_text:
                default_title = f"{default_title} - {round_text}"
            check_var = tk.BooleanVar(value=True)
            title_var = tk.StringVar(value=default_title)
            start_ymdhms, end_ymdhms = vod.get_set_start_end_local(s)
            if start_ymdhms:
                sy, smo, sd, sh, smi, ss = start_ymdhms
                start_date_default = date(sy, smo, sd)
                start_h_var = tk.StringVar(value=str(sh))
                start_m_var = tk.StringVar(value=str(smi))
                start_s_var = tk.StringVar(value=str(ss))
            else:
                start_date_default = date.today()
                start_h_var = tk.StringVar(value="0")
                start_m_var = tk.StringVar(value="0")
                start_s_var = tk.StringVar(value="0")
            # Calculate duration from API start and end times if available
            duration_min_default = 0
            duration_sec_default = 0
            if start_ymdhms and end_ymdhms:
                start_dt = datetime(*start_ymdhms)
                end_dt = datetime(*end_ymdhms)
                delta = end_dt - start_dt
                total_sec = int(delta.total_seconds())
                duration_min_default, duration_sec_default = divmod(max(0, total_sec), 60)
            duration_m_var = tk.StringVar(value=str(duration_min_default))
            duration_s_var = tk.StringVar(value=str(duration_sec_default))
            row = ttk.Frame(sets_inner)
            row.pack(fill="x", pady=2)
            cb = ttk.Checkbutton(row, variable=check_var)
            cb.pack(side="left", padx=(0, 6))
            ent = ttk.Entry(row, textvariable=title_var, width=38)
            ent.pack(side="left", padx=(0, 6))
            # Use plain Entry for dates in the scrollable list — DateEntry's dropdown freezes inside a Canvas
            start_date_str = start_date_default.strftime("%Y-%m-%d")
            ttk.Label(row, text="Start:").pack(side="left", padx=(0, 2))
            start_date_entry = ttk.Entry(row, width=10)
            start_date_entry.insert(0, start_date_str)
            start_date_entry.pack(side="left", padx=2)
            start_h_spin = ttk.Spinbox(row, from_=0, to=23, width=2, textvariable=start_h_var)
            start_h_spin.pack(side="left", padx=1)
            ttk.Label(row, text=":").pack(side="left")
            start_m_spin = ttk.Spinbox(row, from_=0, to=59, width=2, textvariable=start_m_var)
            start_m_spin.pack(side="left", padx=1)
            ttk.Label(row, text=":").pack(side="left")
            start_s_spin = ttk.Spinbox(row, from_=0, to=59, width=2, textvariable=start_s_var)
            start_s_spin.pack(side="left", padx=1)
            ttk.Label(row, text="Duration:").pack(side="left", padx=(4, 2))
            duration_m_spin = ttk.Spinbox(row, from_=0, to=999, width=4, textvariable=duration_m_var)
            duration_m_spin.pack(side="left", padx=1)
            ttk.Label(row, text=":").pack(side="left")
            duration_s_spin = ttk.Spinbox(row, from_=0, to=59, width=2, textvariable=duration_s_var)
            duration_s_spin.pack(side="left", padx=1)
            duration_label = ttk.Label(row, text="")
            duration_label.pack(side="left", padx=(8, 2))
            warn_label = ttk.Label(row, text="", foreground="red")
            warn_label.pack(side="left", padx=2)
            sets_ui_rows.append((s, check_var, title_var, start_date_entry, start_h_var, start_m_var, start_s_var, duration_m_var, duration_s_var, duration_label, warn_label))
        update_durations()

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

    # Load saved slug already set in vars
    root.mainloop()


if __name__ == "__main__":
    run_gui()
