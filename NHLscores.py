import requests
import os
from urllib.parse import urlparse
import ctypes
from datetime import datetime, timedelta

# GUI and image libs (optional)
try:
    import tkinter as tk
    from tkinter import ttk
except Exception:
    tk = None
    ttk = None
try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None
try:
    import cairosvg
except (ImportError, OSError):
    cairosvg = None

# Alternative SVG converter for Windows
try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
    svglib_available = True
except (ImportError, OSError):
    svglib_available = False

# Get yesterday's date in YYYY-MM-DD format
default_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
print(default_date)
print(f"Libraries: tk={tk is not None}, PIL={Image is not None}, cairosvg={cairosvg is not None}, svglib={svglib_available}")

# Cache directory for team logos
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_DIR = os.path.join(SCRIPT_DIR, "logos")
os.makedirs(LOGO_DIR, exist_ok=True)

def ensure_logo_cached(team_obj):
    abbrev = team_obj.get('abbrev') if isinstance(team_obj, dict) else None
    logo_url = None
    if isinstance(team_obj, dict):
        # Prefer dark logo for light backgrounds if available
        logo_url = team_obj.get('darkLogo') or team_obj.get('logo')
    if not abbrev or not logo_url:
        return None

    parsed = urlparse(logo_url)
    _, ext = os.path.splitext(parsed.path)
    if not ext:
        ext = ".svg"

    # Desired final asset for GUI: PNG if possible
    png_path = os.path.join(LOGO_DIR, f"{abbrev}.png")

    # If we already have a PNG, use it
    if os.path.exists(png_path):
        return png_path

    # Check if SVG already exists and try to convert it
    svg_path = os.path.join(LOGO_DIR, f"{abbrev}.svg")
    if os.path.exists(svg_path):
        # Try cairosvg first
        if cairosvg is not None:
            try:
                print(f"Converting existing {abbrev}.svg to PNG with cairosvg...")
                cairosvg.svg2png(url=svg_path, write_to=png_path)
                print(f"Successfully converted {abbrev}.svg to PNG")
                return png_path
            except Exception as e:
                print(f"Warning: cairosvg conversion failed for {abbrev}: {e}")
        
        # Try svglib as fallback (works better on Windows)
        if svglib_available:
            try:
                print(f"Converting existing {abbrev}.svg to PNG with svglib...")
                drawing = svg2rlg(svg_path)
                renderPM.drawToFile(drawing, png_path, fmt="PNG")
                print(f"Successfully converted {abbrev}.svg to PNG")
                return png_path
            except Exception as e:
                print(f"Warning: svglib conversion failed for {abbrev}: {e}")
        
        # If no converter is available
        if cairosvg is None and not svglib_available:
            print(f"Warning: {abbrev}.svg exists but no SVG converter is available.")
            print(f"Install with: pip install svglib reportlab")
        return None

    # Otherwise, download source asset
    try:
        resp = requests.get(logo_url, timeout=20)
        resp.raise_for_status()
        content = resp.content
    except Exception as e:
        print(f"Warning: Failed to download logo for {abbrev}: {e}")
        return None

    # If it's SVG, try to convert to PNG
    if ext.lower() == ".svg":
        # Try cairosvg first
        if cairosvg is not None:
            try:
                print(f"Converting downloaded {abbrev} SVG to PNG with cairosvg...")
                cairosvg.svg2png(bytestring=content, write_to=png_path)
                print(f"Successfully converted {abbrev} SVG to PNG")
                return png_path
            except Exception as e:
                print(f"Warning: cairosvg conversion failed for {abbrev}: {e}")
        
        # Try svglib as fallback
        if svglib_available:
            # Save SVG first, then convert
            svg_temp = os.path.join(LOGO_DIR, f"{abbrev}.svg")
            try:
                with open(svg_temp, 'wb') as f:
                    f.write(content)
                print(f"Converting downloaded {abbrev} SVG to PNG with svglib...")
                drawing = svg2rlg(svg_temp)
                renderPM.drawToFile(drawing, png_path, fmt="PNG")
                print(f"Successfully converted {abbrev} SVG to PNG")
                return png_path
            except Exception as e:
                print(f"Warning: svglib conversion failed for {abbrev}: {e}")

    # If it's already a raster (e.g., PNG) or conversion failed, save original
    src_path = os.path.join(LOGO_DIR, f"{abbrev}{ext}")
    try:
        with open(src_path, 'wb') as f:
            f.write(content)
    except Exception:
        return None

    # If it's a PNG we can use directly
    if ext.lower() in (".png", ".jpg", ".jpeg"):
        return src_path

    # No usable raster created; return source path (GUI may skip non-raster)
    return None

def fetch_games(date_str):
    """Fetch games for a specific date"""
    url = f"https://api-web.nhle.com/v1/schedule/{date_str}"
    response = requests.get(url)
    data = response.json()
    
    lines = []
    games_data = []
    
    if 'gameWeek' in data and data['gameWeek']:
        for day in data['gameWeek']:
            # Only process games for the exact date requested
            day_date = day.get('date')
            if day_date != date_str:
                continue
                
            if 'games' in day:
                for game in day['games']:
                    away_team_obj = game.get('awayTeam', {})
                    home_team_obj = game.get('homeTeam', {})
                    away_team = away_team_obj.get('abbrev')
                    home_team = home_team_obj.get('abbrev')

                    away_score = away_team_obj.get('score')
                    home_score = home_team_obj.get('score')
                    
                    # Get game start time for future games
                    start_time_utc = game.get('startTimeUTC')
                    game_state = game.get('gameState', '')
                    
                    # Only cache logos for games we're displaying
                    away_logo = ensure_logo_cached(away_team_obj)
                    home_logo = ensure_logo_cached(home_team_obj)

                    # Determine if game has scores or is scheduled
                    if away_score is not None and home_score is not None:
                        # Game has scores (completed or in progress)
                        lines.append(f"{away_team} vs {home_team} - {away_score}:{home_score}")
                        games_data.append({
                            'away_abbrev': away_team,
                            'home_abbrev': home_team,
                            'away_score': away_score,
                            'home_score': home_score,
                            'away_logo': away_logo,
                            'home_logo': home_logo,
                            'is_scheduled': False,
                            'start_time': None,
                        })
                    else:
                        # Future game - show start time
                        time_display = "TBD"
                        if start_time_utc:
                            try:
                                # Convert UTC to local time
                                utc_time = datetime.fromisoformat(start_time_utc.replace('Z', '+00:00'))
                                local_time = utc_time.astimezone()
                                time_display = local_time.strftime('%I:%M %p')
                            except Exception:
                                time_display = "TBD"
                        
                        lines.append(f"{away_team} vs {home_team} - {time_display}")
                        games_data.append({
                            'away_abbrev': away_team,
                            'home_abbrev': home_team,
                            'away_score': None,
                            'home_score': None,
                            'away_logo': away_logo,
                            'home_logo': home_logo,
                            'is_scheduled': True,
                            'start_time': time_display,
                        })
    
    return lines, games_data

# Fetch initial games
lines, games_data = fetch_games(default_date)

if not lines:
    print(f"No games scheduled for {default_date}.")
    ctypes.windll.user32.MessageBoxW(0, f"No games scheduled for {default_date}.", f"NHL Scores {default_date}", 0)

# If GUI libs available, show a window with logos; otherwise, fallback to MessageBox
if tk is not None and Image is not None and ImageTk is not None:
    root = tk.Tk()
    root.title(f"NHL Scores")
    root.minsize(700, 500)  # Set minimum window size

    # Date selector frame at the top
    date_frame = ttk.Frame(root, padding=10)
    date_frame.pack(fill="x")
    
    ttk.Label(date_frame, text="Select Date:", font=('Angular', 12)).pack(side="left", padx=5)
    
    # Date entry
    date_var = tk.StringVar(value=default_date)
    date_entry = ttk.Entry(date_frame, textvariable=date_var, width=12, font=('Angular', 12))
    date_entry.pack(side="left", padx=5)
    
    # Create a canvas with scrollbar for games
    canvas_frame = ttk.Frame(root)
    canvas_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    canvas = tk.Canvas(canvas_frame, highlightthickness=0)
    scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
    
    # Load background image
    bg_image_path = os.path.join(LOGO_DIR, "backround.jpg")
    bg_img_original = None
    bg_image_id = [None]  # Use list to avoid nonlocal issues
    
    if os.path.exists(bg_image_path):
        try:
            bg_img_original = Image.open(bg_image_path)
        except Exception as e:
            print(f"Warning: Could not load background image: {e}")
    
    def update_background(event=None):
        """Update background image to fit canvas size"""
        if bg_img_original is not None:
            try:
                # Get canvas dimensions
                width = canvas.winfo_width()
                height = canvas.winfo_height()
                if width > 1 and height > 1:  # Valid dimensions
                    # Resize image to fit canvas
                    resized_img = bg_img_original.resize((width, height), Image.Resampling.LANCZOS)
                    bg_photo = ImageTk.PhotoImage(resized_img)
                    
                    # Update or create background image
                    if bg_image_id[0]:
                        canvas.delete(bg_image_id[0])
                    bg_image_id[0] = canvas.create_image(0, 0, image=bg_photo, anchor="nw")
                    canvas.bg_photo = bg_photo  # Keep reference
                    canvas.tag_lower(bg_image_id[0])  # Send to back
            except Exception as e:
                print(f"Warning: Could not update background: {e}")
    
    # Bind canvas resize to update background
    canvas.bind("<Configure>", update_background)
    
    scrollable_frame = ttk.Frame(canvas)
    
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Container for games (will be refreshed)
    container = ttk.Frame(scrollable_frame, padding=20)
    container.pack(fill="both", expand=True)
    
    # Enable mouse wheel scrolling
    def on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    canvas.bind_all("<MouseWheel>", on_mousewheel)
    
    def refresh_games():
        """Refresh the games display with the selected date"""
        selected_date = date_var.get()
        
        # Clear existing games
        for widget in container.winfo_children():
            widget.destroy()
        
        # Fetch new games
        new_lines, new_games_data = fetch_games(selected_date)
        
        if not new_games_data:
            ttk.Label(container, text=f"No games scheduled for {selected_date}", 
                     font=('Angular', 14)).pack(pady=20)
            return
        
        # Update window title
        root.title(f"NHL Scores - {selected_date}")
        
        # Display games
        images_refs.clear()
        for game in new_games_data:
            row = ttk.Frame(container)
            row.pack(fill="x", pady=4)
            
            # Away logo
            if game['away_logo'] and os.path.exists(game['away_logo']) and game['away_logo'].lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    img = Image.open(game['away_logo']).resize((64, 64))
                    photo = ImageTk.PhotoImage(img)
                    images_refs.append(photo)
                    tk.Label(row, image=photo).pack(side="left", padx=(0,10))
                except Exception:
                    tk.Label(row, text=game['away_abbrev'], font=('Angular', 12, 'bold')).pack(side="left", padx=(0,10))
            else:
                tk.Label(row, text=game['away_abbrev'], font=('Angular', 12, 'bold')).pack(side="left", padx=(0,10))

            # Text in middle
            if game.get('is_scheduled', False):
                # Future game - show start time
                ttk.Label(row, text=f"{game['away_abbrev']} @ {game['home_abbrev']} - {game['start_time']}", 
                         font=('Angular', 14, 'bold')).pack(side="left", padx=10)
            else:
                # Completed or in-progress game - show scores
                ttk.Label(row, text=f"{game['away_abbrev']} {game['away_score']} vs {game['home_abbrev']} {game['home_score']}", 
                         font=('Angular', 14, 'bold')).pack(side="left", padx=10)

            # Home logo
            if game['home_logo'] and os.path.exists(game['home_logo']) and game['home_logo'].lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    img = Image.open(game['home_logo']).resize((64, 64))
                    photo = ImageTk.PhotoImage(img)
                    images_refs.append(photo)
                    tk.Label(row, image=photo).pack(side="left", padx=(10,0))
                except Exception:
                    tk.Label(row, text=game['home_abbrev'], font=('Angular', 12, 'bold')).pack(side="left", padx=(10,0))
            else:
                tk.Label(row, text=game['home_abbrev'], font=('Angular', 12, 'bold')).pack(side="left", padx=(10,0))
    
    # Refresh button
    ttk.Button(date_frame, text="Refresh", command=refresh_games).pack(side="left", padx=5)
    
    # Auto-refresh toggle
    auto_refresh_var = tk.BooleanVar(value=False)
    auto_refresh_check = ttk.Checkbutton(date_frame, text="Live Games", variable=auto_refresh_var)
    auto_refresh_check.pack(side="left", padx=5)
    
    # Help text
    ttk.Label(date_frame, text="(Format: YYYY-MM-DD)", font=('Angular', 9), foreground="gray").pack(side="left", padx=5)
    
    # Auto-refresh timer
    auto_refresh_job = None
    
    def auto_refresh():
        """Automatically refresh games if enabled"""
        global auto_refresh_job
        if auto_refresh_var.get():
            refresh_games()
            # Schedule next refresh in 30 seconds
            auto_refresh_job = root.after(30000, auto_refresh)
    
    def toggle_auto_refresh():
        """Start or stop auto-refresh based on checkbox"""
        global auto_refresh_job
        if auto_refresh_var.get():
            # Set date to today
            today = datetime.now().strftime('%Y-%m-%d')
            date_var.set(today)
            # Refresh with today's date
            refresh_games()
            # Start auto-refresh
            auto_refresh_job = root.after(30000, auto_refresh)
        else:
            # Stop auto-refresh
            if auto_refresh_job:
                root.after_cancel(auto_refresh_job)
                auto_refresh_job = None
    
    # Bind checkbox to toggle function
    auto_refresh_check.config(command=toggle_auto_refresh)
    
    images_refs = []  # keep references
    
    # Initial display
    if lines:
        for game in games_data:
            row = ttk.Frame(container)
            row.pack(fill="x", pady=4)

        # Away logo
        if game['away_logo'] and os.path.exists(game['away_logo']) and game['away_logo'].lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                img = Image.open(game['away_logo']).resize((64, 64))
                photo = ImageTk.PhotoImage(img)
                images_refs.append(photo)
                tk.Label(row, image=photo).pack(side="left", padx=(0,10))
            except Exception:
                tk.Label(row, text=game['away_abbrev'], font=('Angular', 12, 'bold')).pack(side="left", padx=(0,10))
        else:
            tk.Label(row, text=game['away_abbrev'], font=('Angular', 12, 'bold')).pack(side="left", padx=(0,10))

        # Text in middle
        if game.get('is_scheduled', False):
            # Future game - show start time
            ttk.Label(row, text=f"{game['away_abbrev']} @ {game['home_abbrev']} - {game['start_time']}", 
                     font=('Arial', 14, 'bold')).pack(side="left", padx=10)
        else:
            # Completed or in-progress game - show scores
            ttk.Label(row, text=f"{game['away_abbrev']} {game['away_score']} vs {game['home_abbrev']} {game['home_score']}", font=('Arial', 14, 'bold')).pack(side="left", padx=10)

        # Home logo
        if game['home_logo'] and os.path.exists(game['home_logo']) and game['home_logo'].lower().endswith(('.png', '.jpg', '.jpeg')):
            try:
                img = Image.open(game['home_logo']).resize((64, 64))
                photo = ImageTk.PhotoImage(img)
                images_refs.append(photo)
                tk.Label(row, image=photo).pack(side="left", padx=(10,0))
            except Exception:
                tk.Label(row, text=game['home_abbrev'], font=('Angular', 12, 'bold')).pack(side="left", padx=(10,0))
        else:
            tk.Label(row, text=game['home_abbrev'], font=('Angular', 12, 'bold')).pack(side="left", padx=(10,0))

    # Close button at bottom
    close_frame = ttk.Frame(root, padding=10)
    close_frame.pack(fill="x")
    ttk.Button(close_frame, text="Close", command=root.destroy).pack()

    # Automatically refresh once when panel opens
    root.after(100, refresh_games)
    # Update background after window is displayed
    root.after(200, update_background)

    root.mainloop()
elif lines:
    ctypes.windll.user32.MessageBoxW(0, "\n".join(lines), f"NHL Scores {default_date}", 0)
