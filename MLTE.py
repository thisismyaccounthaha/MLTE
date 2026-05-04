from dataclasses import fields
import importlib.util
import subprocess
import sys


def ensure_package_installed(package_name):
    if importlib.util.find_spec(package_name) is None:
        print(f"{package_name} not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
    else:
        print(f"{package_name} is already installed.")

ensure_package_installed("keyboard")
ensure_package_installed("readchar")
ensure_package_installed("pyodbc")
ensure_package_installed("pyperclip")

import xml.etree.ElementTree as ET
from xml.dom import minidom
import  os, readchar, pyodbc, re, pyperclip, keyboard, json, webbrowser, time
from sync_tool_crib import sync_database
import CribSearch
import SyncLineTool
import EditSettings

from settings import cfg


SHOP_FLOOR_PASSWORD = cfg.shop_floor_password
DB_CREDS = cfg.db_creds
LINE_CONFIGS = cfg.line_configs
SEARCH_RANGES = cfg.search_ranges
KEYWORD_SEARCH_RANGES = cfg.keyword_search_ranges
HOLDER_LIST = cfg.holder_list
TOOL_KINDS = cfg.tool_kinds
TOOL_TYPES = cfg.tool_types
LIFE_TYPES = cfg.life_types
ENDMILL_SUB_TYPES = cfg.endmill_sub_types
SPECIAL_SUB_TYPES = cfg.special_sub_types
TAP_STANDARD = cfg.tap_standard
TAP_METRIC = cfg.tap_metric
IS_PROGRAMMER_MODE = "--programmer" in sys.argv


# UI Constants
BAR_COLOR = "\033[1;33m"      
HEAD_COLOR = "\033[1;37m"     
SUB_COLOR = "\033[90m"        
DESC_COLOR = "\033[1;38;5;51m" 
NUM_NORMAL = "\033[1;37m"      
NUM_CONFLICT = "\033[1;97;41m" 
SEL_CURSOR = "\033[1;30;102m" 
RESET = "\033[0m"


class ToolApp:
    def __init__(self):
        self.history = []

    def push_history(self, item):
        """Manually add a breadcrumb to the top bar."""
        if item:
            self.history.append(str(item)[:15])

    def inject_type(self, text):
        """Pre-fills the console input buffer (requires 'keyboard' lib)."""
        if text:
            import keyboard
            keyboard.write(text)
    
    def confirm(self, title, label):
        """Standard Y/N confirmation using readchar. Clears after selection."""
        self.clear(title)
        print(f"{label} (y/n): ", end="", flush=True)
        while True:
            key = readchar.readkey().lower()
            if key == 'y':
                # Clear the prompt immediately so the next screen is just the results
                self.clear(title) 
                return True
            if key == 'n':
                return False

    def clear(self, title=""):
        os.system('cls' if os.name == 'nt' else 'clear')
        if self.history:
            # This is your yellow 'ADD > Endmills > 00000019' bar
            print(f"\033[1;33m{' > '.join(self.history)}\033[0m")
            print("\033[1;33m" + "—" * 50 + "\033[0m")
        else:
            print("\033[1;34m--- MAS-A5 ADE Multi Line Tool Editor ---\033[0m\n")
        
        if title:
            print(f"\033[1;36m[ {title.upper()} ]\033[0m\n")

    def prompt(self, title, label, default=""):
        self.clear(title)
        val = input(f"{label}: ").strip() or default
        # We only append to history AFTER the input is successful
        if val and val != default:
            self.history.append(val[:15]) 
        return val
    
    def show_help(self):
        help_path = os.path.join(os.path.dirname(__file__), "Help.md")
        if not os.path.exists(help_path):
            return

        # Use 'start' to open a NEW window that runs a small python snippet to display the file
        # This prevents the help text from cluttering your main app menu
        cmd = (
            f'start "{os.path.basename(help_path)}" cmd /k '
            f'"{sys.executable} -c '
            f'\"import sys; '
            f'text = open(r\'{help_path}\').read(); '
            f'text = text.replace(\'**\', \'\033[1m\').replace(\'# \', \'\033[1;36m# \'); '
            f'print(text + \'\033[0m\');\" '
            f'& pause"'
        )
        subprocess.Popen(cmd, shell=True)

    def get_menu_with_header(self, options, title, header_text):
        keys = list(options.keys())
        idx = 0
        num_options = len(keys)
        
        self.clear(title)
        print(header_text)
        print("\033[1;33m" + "—" * 50 + "\033[0m") 

        sys.stdout.write("\033[?25l") 
        
        try:
            while True:
                output = []
                for i, name in enumerate(keys):
                    if i == idx:
                        # Highlight ONLY the text, then clear the rest of the line
                        output.append(f"  \033[1;97;42m > {name} \033[0m\033[K")
                    else:
                        output.append(f"    {name}\033[K")
                
                sys.stdout.write("\n".join(output) + "\n")
                sys.stdout.flush()

                key = readchar.readkey()
                if key == readchar.key.UP:
                    idx = (idx - 1) % num_options
                elif key == readchar.key.DOWN:
                    idx = (idx + 1) % num_options
                elif key == readchar.key.ENTER:
                    choice_label = keys[idx]
                    if choice_label not in ["EXIT", "BACK"]:
                        self.history.append(choice_label[:15])
                    return options[choice_label]
                elif key in [readchar.key.ESC, readchar.key.BACKSPACE]:
                    return "BACK_REQ"

                sys.stdout.write(f"\033[{num_options}A") 
        finally:
            sys.stdout.write("\033[?25h")

    def get_menu_choice(self, options, title):
        keys = list(options.keys())
        idx = 0
        num_options = len(keys)
        
        self.clear(title)

        # --- UPDATE NOTIFICATION ---
        # This only triggers on the top-level menus
        if title in ["Main Menu", "Select Tool Category"]:
            print("\033[1;37m- Ctrl + h for help.\n")
        # ---------------------------
        
        sys.stdout.write("\033[?25l") 
        
        try:
            while True:
                # Use \033[J to clear everything below the menu to prevent ghosting
                sys.stdout.write("\033[J")
                output = []
                for i, name in enumerate(keys):
                    if i == idx:
                        output.append(f"  \033[1;97;42m > {name} \033[0m")
                    else:
                        output.append(f"    {name}")
                
                sys.stdout.write("\n".join(output) + "\n")
                sys.stdout.flush()

                key = readchar.readkey()

                if (key in ['\x08', '\x07'] or key == readchar.key.CTRL_H) and keyboard.is_pressed('h'):
                    self.show_help()
                    self.clear(title)
                    continue
                
                if key == readchar.key.RIGHT:
                    trigger_rain(self, title)
                    continue

                if key == readchar.key.UP:
                    idx = (idx - 1) % num_options
                elif key == readchar.key.DOWN:
                    idx = (idx + 1) % num_options
                elif key == readchar.key.ENTER:
                    choice_label = keys[idx]
                    # Don't add 'EXIT' or 'BACK' to the permanent history bar
                    if choice_label not in ["EXIT", "BACK"]:
                        self.history.append(choice_label)
                    return options[choice_label]
                elif key == readchar.key.BACKSPACE or key == readchar.key.ESC:
                    return "BACK_REQ" 
                
                # Move cursor back up to redraw menu
                sys.stdout.write(f"\033[{num_options}F")
        finally:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

#Easter-Egg
def trigger_rain(app, title):
    import time, random, os, sys
    
    sys.stdout.write("\033[?25h") 
    app.clear("System Override")
    
    try:
        columns, rows = os.get_terminal_size()
    except:
        columns, rows = 80, 30

    asset = [
        "    ⣀⣀    ", "  ⢠⠞⠹⠏⠳⣄  ", " ⢰⠟⠀⠀⠀⠀⠙⡇ ", " ⠘⣷⠤⠖⠳⠤⣴⠋ ",
        "   ⣿⠀⠀⠀⠀⣿  ", "   ⣿⠀⠀⠀⠀⣿  ", "   ⣿⠀⠀⠀⠀⣿  ", "   ⣿⠀⠀⠀⠀⣿  ",
        " ⢀⣠⡿⠀⠀⠀⠀⠿⣤⡀", "⢰⠏⠁⠀⠀⠀⠀⠀⠀⠀⠙⣆", "⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿",
        "⠘⢧⣀⡀⣀⣠⣄⡀⣀⣀⡴⠋", "  ⠈⠉⠉⠉⠈⠉⠉⠁  "
    ]

    # Stream entry: [col, v_pos]
    streams = []
    
    try:
        for frame in range(250):
            # 1. Reset cursor to top-left to redraw
            print("\033[H", end="") 
            
            # 2. Create fresh screen buffer for this frame
            screen = [[" " for _ in range(columns)] for _ in range(rows - 2)]
            
            # 3. Randomly spawn new streams
            if random.random() < 0.2 and len(streams) < 10:
                new_col = random.randint(0, max(0, columns - 5))
                # Start just above the screen (v_pos = -len(asset)) to "slide in"
                # --- NEW: Collision Check ---
                # Check if this new column is too close to any existing stream's column
                col_buffer = 15 
                too_close = False
                for s in streams:
                    if abs(s[0] - new_col) < col_buffer:
                        too_close = True
                        break
                
                # Only add if the "lane" is clear
                if not too_close:
                    streams.append([new_col, -len(asset)])
            
            # 4. Draw each stream into the buffer
            for i in range(len(streams) - 1, -1, -1):
                col, v_pos = streams[i]
                
                # Draw each line of the ASCII asset based on the current v_pos
                for local_idx, line in enumerate(asset):
                    draw_row = v_pos + local_idx
                    
                    # Only draw if the row is actually visible on screen
                    if 0 <= draw_row < len(screen):
                        for char_idx, char in enumerate(line):
                            target_col = col + char_idx
                            if target_col < columns:
                                screen[draw_row][target_col] = char
                
                # 5. Move the stream down for the next frame
                streams[i][1] += 1
                
                # 6. Remove if it's completely off the bottom
                if streams[i][1] > rows:
                    streams.pop(i)
            
            # 7. Print the buffer in Grey
            output = []
            for row in screen:
                output.append("\033[90m" + "".join(row) + "\033[0m")
            sys.stdout.write("\n".join(output) + "\n")
            sys.stdout.flush()
            
            time.sleep(0.02) # Faster fall speed
            
    except KeyboardInterrupt:
        pass

    app.clear(title)
    sys.stdout.write("\033[?25l")

# --- Logic ---
def parse_size_to_float(size_str):
    """Strips 'mm' and converts '1/2', '.5', or '6' into float for comparison."""
    try:
        # 1. Clean the string: lowercase, remove spaces, and strip 'mm'
        clean_str = size_str.lower().replace(' ', '').replace('mm', '')
        
        # 2. Handle fractions (e.g., '1/2')
        if '/' in clean_str:
            num, den = clean_str.split('/')
            return round(float(num) / float(den), 4)
            
        # 3. Handle standard decimals or integers (e.g., '6' or '.5')
        return round(float(clean_str), 4)
    except:
        return None

def extract_first_number(text):
    """Finds the first number or fraction in the tool description."""
    match = re.search(r'(\d+/\d+|\d*\.\d+|\d+)', text)
    if match:
        return parse_size_to_float(match.group(1))
    return None

def extract_item_numbers(comment):
    # 1. (?:item\s*#?\s*|#|(?<=\s)/) -> Matches 'item ', 'item#', '#', or ' /'
    # 2. (\d{4})                     -> Captures exactly 4 digits
    # 3. (?!\d)                      -> Negative lookahead: Ensures no 5th digit follows
    item_pattern = re.compile(
        r"(?:item\s*#?\s*|#|(?<=\s)/)(\d{4})(?!\d)", 
        re.IGNORECASE
    )
    matches = item_pattern.findall(comment)
    return matches if matches else []

def get_conflict_set():
    """Helper: Scans all lines and returns a set of FTNs that have naming mismatches."""
    ftn_data = {} # { "00006093": {"comment1", "comment2"} }
    for cfg in LINE_CONFIGS:
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg['ip']},1433;DATABASE={cfg['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=1;")
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT [FTN], [FTNComment] FROM [dbo].[FunctionalToolData]")
                for row in cursor.fetchall():
                    ftn = str(row[0]).zfill(8)
                    comment = str(row[1] or "").strip()
                    if ftn not in ftn_data: ftn_data[ftn] = set()
                    ftn_data[ftn].add(comment)
        except: continue
    # Return only the FTNs that have more than 1 unique description
    return {ftn for ftn, comments in ftn_data.items() if len(comments) > 1}

def run_keyword_search(app):
    while True:
        # --- Reset State & Select Category ---
        app.history.clear()
        category_name = app.get_menu_choice({k: k for k in SEARCH_RANGES.keys()}, "Category Search")
        if category_name == "BACK_REQ":
            break

        # --- Initialize Search Parameters ---
        params = {
            "sub_filter": None,
            "sub_label": "",
            "radius_pattern": None,
            "flute_pattern": None,
            "pitch_pattern": None,
            "item_pattern": None,
            "size_input": "ALL",
            "target_val": None
        }
        ranges = SEARCH_RANGES[category_name]

        # --- Category-Specific Refinement ---
        if category_name == "Endmills":
            sub_choice = app.get_menu_choice({**{k: k for k in ENDMILL_SUB_TYPES.keys()}, "All Endmills": "ALL"}, "Refine Endmill Type")
            if sub_choice == "BACK_REQ": continue
            if sub_choice != "ALL":
                params["sub_filter"] = ENDMILL_SUB_TYPES[sub_choice]
                params["sub_label"] = f" ({sub_choice})"

            # --- 1. Diameter ---
            size_raw = app.prompt(f"Refine Search: Endmills{params['sub_label']}", "Enter diameter (e.g. '1/2' or '.5') or ENTER for all")
            if size_raw:
                params["size_input"] = size_raw
                params["target_val"] = parse_size_to_float(size_raw)

            # --- 2. Radius (only for Bull Endmill) ---
            if sub_choice == "Bull Endmill":
                radius_input = app.prompt("Bull Endmill Refinement", "Example: '.04' matches .04R, .04RAD")
                if radius_input:
                    params["radius_pattern"] = re.compile(rf"{re.escape(radius_input)}\s?(R|RAD)\b", re.IGNORECASE)
                    params["sub_label"] += f" [R{radius_input}]"

            # --- 3. Flute ---
            flute_input = app.prompt(f"Endmill Flute Filter{params['sub_label']}", "Example: '3' for 3F, '4' for 4FL, or ENTER for all")
            if flute_input:
                params["flute_pattern"] = re.compile(rf"\b{re.escape(flute_input)}\s?(F|FL|FLUTE)\b", re.IGNORECASE)
                params["sub_label"] += f" [{flute_input}F]"

        elif category_name == "Special Tools":
            sub_choice = app.get_menu_choice({**{k: k for k in SPECIAL_SUB_TYPES.keys()}, "All Specials": "ALL"}, "Refine Special Tool Type")
            if sub_choice == "BACK_REQ": continue
            if sub_choice != "ALL":
                params["sub_filter"] = SPECIAL_SUB_TYPES[sub_choice]
                params["sub_label"] = f" ({sub_choice})"

        elif category_name == "Thread Mills":
            pitch_input = app.prompt("Thread Mill Filter", "Example: '20', '1.5', 'NPT', or ENTER for all").upper()
            if pitch_input:
                params["pitch_pattern"] = re.compile(rf"[- X\s]{re.escape(pitch_input)}(\b|[A-Z])", re.IGNORECASE)
                params["sub_label"] = f" [PITCH: {pitch_input}]"

        elif category_name == "Taps":
            system_choice = app.get_menu_choice({"Standard": "STD", "Metric": "MET", "All Taps": "ALL_DUMP"}, "Select Tap Category")
            if system_choice == "BACK_REQ": continue
            if system_choice == "ALL_DUMP":
                params["sub_label"] = " (FULL RANGE DUMP)"
            else:
                size_list = TAP_STANDARD if system_choice == "STD" else TAP_METRIC
                search_term = app.get_menu_choice(size_list, "Select Tap Size")
                if search_term == "BACK_REQ": continue
                params["pitch_pattern"] = re.compile(rf"\b{re.escape(search_term)}\b", re.IGNORECASE)
                params["sub_label"] = f" ({search_term})"
                params["size_input"] = search_term

        # --- Diameter input for all except Taps/Item Number/Endmills ---
        if category_name not in ["Taps", "Item Number", "Endmills"]:
            size_raw = app.prompt(f"Refine Search: {category_name}{params['sub_label']}", "Enter diameter (e.g. '1/2' or '.5') or ENTER for all")
            if size_raw:
                params["size_input"] = size_raw
                params["target_val"] = parse_size_to_float(size_raw)

        # --- 3. DATA ACQUISITION ---
        app.clear("Querying SQL Servers...")
        ftn_list = [] # We switch to a list of objects for easier pagination
        ftn_tracker = {} # To prevent duplicate FTN/Comment pairs
        radius_regex = r'\b(R\s?\.?\d+|\d+\.?\d*\s?R)\b'

        for cfg in LINE_CONFIGS:
            try:
                conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg['ip']},1433;DATABASE={cfg['db']};"
                            f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=2;")
                with pyodbc.connect(conn_str) as conn:
                    cursor = conn.cursor()
                    for min_ftn, max_ftn in ranges:
                        cursor.execute("SELECT [FTN], [FTNComment] FROM [FunctionalToolData] WHERE [FTN] BETWEEN ? AND ?", (min_ftn, max_ftn))
                        for row in cursor.fetchall():
                            ftn_num = str(row[0]).zfill(8)
                            comment = str(row[1] or "").strip()
                            comment_up = comment.upper()

                            # Apply Patterns
                            filters = [(params["radius_pattern"], comment_up), (params["flute_pattern"], comment_up), (params["pitch_pattern"], comment_up)]
                            if any(pat and not pat.search(val) for pat, val in filters): continue
                            if category_name not in ["Taps", "Item Number"] and params["target_val"] is not None:
                                if extract_first_number(comment_up) != params["target_val"]: continue

                            # Apply Sub-Filters (Endmill types)
                            if params["sub_filter"]:
                                sub = params["sub_filter"]
                                if sub.get("include") and not any((re.search(radius_regex, comment_up) if w=="R" else w in comment_up) for w in sub["include"]): continue
                                if sub.get("exclude") and any((re.search(radius_regex, comment_up) if w=="R" else w in comment_up) for w in sub["exclude"]): continue

                            # Grouping Logic
                            key = f"{ftn_num}|{comment}"
                            if key not in ftn_tracker:
                                entry = {"ftn": ftn_num, "comment": comment, "lines": {name: False for name in [c['name'] for c in LINE_CONFIGS]}}
                                ftn_list.append(entry)
                                ftn_tracker[key] = entry
                            
                            ftn_tracker[key]["lines"][cfg['name']] = True
            except: continue

        if not ftn_list:
            print("\033[1;33mNo matches found.\033[0m"); readchar.readkey(); continue

        # --- 4. THE INTERACTIVE RESULTS LOOP ---
        ftn_list.sort(key=lambda x: x['ftn'])
        results_stack = []
        current_results = list(ftn_list)
        page, idx = 0, 0
        page_size = 10
        app.clear()
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
        # --- UI SETUP ---
        conflicts = get_conflict_set()
        
        BAR_COLOR = "\033[1;33m"      
        HEAD_COLOR = "\033[1;37m"     
        SUB_COLOR = "\033[90m"        
        DESC_COLOR = "\033[1;38;5;51m" 
        NUM_NORMAL = "\033[1;37m"      # Bold White
        NUM_CONFLICT = "\033[1;97;41m" # White text on Red background (Number ONLY)
        SEL_CURSOR = "\033[1;30;102m" 
        RESET = "\033[0m"

        # --- 1. SETUP BEFORE THE LOOP ---
        current_refinement = ""  # New: Track the extra search term
        results_stack = []
        original_results = list(ftn_list) # Keep a clean backup
        current_results = list(ftn_list)

        while True:
            print("\033[H", end="") 

            total = len(current_results)
            total_pages = max(1, (total + page_size - 1) // page_size)
            batch = current_results[page * page_size : (page + 1) * page_size]
            idx = min(idx, len(batch) - 1)

            # --- TOP STATUS BAR ---
            # Breadcrumb now includes Category + Sub-Label + Current Refinement
            refine_tag = f" > SEARCH: '{current_refinement}'" if current_refinement else ""
            bread = f" SEARCH: {category_name}{params['sub_label']}{refine_tag}"
            
            stats = f"TOTAL: {total} | PAGE: {page+1}/{total_pages}"
            print(f"{BAR_COLOR} {bread:<55}{stats:>25}{RESET}\033[K")
            
            # --- COLUMN HEADERS ---
            print(f"{SUB_COLOR}{'—' * 85}{RESET}\033[K")
            print(f"{HEAD_COLOR}    {'  FTN':<9}   {'DESCRIPTION / TOOL COMMENTS'}{RESET}\033[K")
            print(f"{SUB_COLOR}{'—' * 85}{RESET}\033[K")

            # --- DATA ROWS ---
            for i, item in enumerate(batch):
                # 1. Selection Cursor
                if i == idx:
                    selector = f"{SEL_CURSOR} > {RESET}"
                else:
                    selector = "   "

                # 2. Item Number with Selective Conflict Highlight
                # Logic: [ is gray, number is (white or red-bg), ] is gray
                is_red = item['ftn'] in conflicts
                num_style = NUM_CONFLICT if is_red else NUM_NORMAL
                
                ftn_display = f"{SUB_COLOR}[{RESET}{num_style}{item['ftn']}{RESET}{SUB_COLOR}]{RESET}"

                # 3. Print Row
                print(f" {selector} {ftn_display} {DESC_COLOR}{item['comment']}{RESET}\033[K")

                # 4. Machine Tags Sub-row (Specific Nested Formatting)
                tags = []
                for ln, active in item['lines'].items():
                    if active:
                        # ACTIVE: Red text 'name', Gray Brackets
                        tag = f"\033[90m[\033[31m{ln:^7}\033[22;90m]\033[0m"
                    else:
                        # INACTIVE: Gray text '-name-', Gray Brackets
                        disp_text = f"-{ln}-"
                        tag = f"\033[2;90m[{disp_text:^7}]\033[0m"
                    tags.append(tag)
                
                print(f"      {SUB_COLOR}└─{RESET} {' '.join(tags)}\033[K")

            # --- FILLER ---
            remaining = (page_size - len(batch)) * 2
            for _ in range(remaining):
                print("\033[K") 

            print(f"{SUB_COLOR}{'—' * 85}{RESET}\033[K")
            footer_text = " [UP/DN] Select  [L/R] Page  [S] Refine  [I] Item Details  [U] Undo  [C] Copy  [ESC] Exit"
            print(f"{BAR_COLOR} {footer_text}{RESET}", end="")
            sys.stdout.flush()
            k = readchar.readkey()

            # --- Vertical Navigation (Selector Only) ---
            if k == readchar.key.UP:
                if idx > 0: 
                    idx -= 1
            elif k == readchar.key.DOWN:
                if idx < len(batch) - 1: 
                    idx += 1

            # --- Horizontal Navigation (Pages Only) ---
            elif k == readchar.key.LEFT:
                if page > 0:
                    page -= 1
                    # Optional: idx = 0 (or keep current idx to stay on the same row)
            elif k == readchar.key.RIGHT:
                if (page + 1) < total_pages:
                    page += 1
                    # Ensure idx isn't out of bounds if the next page is shorter
                    new_batch_len = len(current_results[page * page_size : (page + 1) * page_size])
                    if idx >= new_batch_len:
                        idx = new_batch_len - 1

            # --- Other Controls ---
            if k.lower() == 'i' and batch:
                selected_item = batch[idx]
                item_list = extract_item_numbers(selected_item['comment'])
                
                if item_list:
                    # Show cursor for the spec viewing screens
                    sys.stdout.write("\033[?25h")
                    sys.stdout.flush()
                    
                    for item_no in item_list:
                        show_item_specs(app,item_no)
                    
                    # After returning from all spec screens, hide cursor again
                    sys.stdout.write("\033[?25l")
                    # Clear screen once to wipe the spec data before the loop redraws
                    app.clear() 
                else:
                    # Visual Feedback: Briefly flash a message in the footer area
                    print(f"\r\033[K\033[1;91m NO ITEM # FOUND IN DESCRIPTION \033[0m", end="", flush=True)
                    time.sleep(0.9)

            if k.lower() == 's':
                sys.stdout.write("\033[?25h") # Show cursor
                print(f"\n\033[1;32m REFINE: \033[0m", end="", flush=True)
                
                raw_input = input().upper()
                
                # Clear prompt from screen
                sys.stdout.write("\033[A\033[K") 
                sys.stdout.write("\033[?25l") # Hide cursor
                
                if raw_input:
                    # Save state for Undo
                    results_stack.append((list(current_results), current_refinement))

                    # Extract terms between double-quotes: ""TERM""
                    # This regex looks for double quotes and captures everything inside
                    or_terms = re.findall(r'""(.*?)""', raw_input)

                    if or_terms:
                        # OR Logic: Keep item if ANY term matches
                        current_results = [
                            x for x in current_results 
                            if any(term in x['comment'].upper() or term in x['ftn'] for term in or_terms)
                        ]
                        new_breadcrumb = " | ".join([f"'{t}'" for t in or_terms])
                    else:
                        # Fallback to standard single-term search if no "" are used
                        term = raw_input.strip()
                        current_results = [
                            x for x in current_results 
                            if term in x['comment'].upper() or term in x['ftn']
                        ]
                        new_breadcrumb = f"'{term}'"

                    # Update the Breadcrumb string
                    if current_refinement:
                        current_refinement += f" + {new_breadcrumb}"
                    else:
                        current_refinement = new_breadcrumb
                        
                    page, idx = 0, 0
            elif k.lower() == 'u' and results_stack:
                # Restore both the list and the breadcrumb text
                current_results, current_refinement = results_stack.pop()
                page, idx = 0, 0
            elif k.lower() == 'c' and batch:
                # Get the comment of the item the cursor is pointing at
                desc_to_copy = batch[idx]['comment']
                pyperclip.copy(desc_to_copy)
                
                # Visual Feedback: Briefly flash a message in the footer area
                print(f"\r\033[K\033[1;32m COPIED DESCRIPTION TO CLIPBOARD\033[0m", end="", flush=True)
                time.sleep(0.9)
            elif k == readchar.key.ESC or k == readchar.key.BACKSPACE:
                # IMPORTANT: Reset refinement completely when going back to category selection
                current_refinement = ""
                break

def run_item_search(app, initial_item=None):  # Added optional parameter
    app.history.clear()
    app.push_history("FTN ITEM SEARCH")

    # 1. PRE-FETCH DATA
    app.clear("Loading Tool Database...")
    all_ftn_data = []
    
    for cfg in LINE_CONFIGS:
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg['ip']},1433;DATABASE={cfg['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=2;")
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT [FTN], [FTNComment] FROM [dbo].[FunctionalToolData]")
                for row in cursor.fetchall():
                    all_ftn_data.append({
                        "ftn": str(row[0]).zfill(8),
                        "comment": str(row[1] or "").strip(),
                        "line": cfg['name']
                    })
        except Exception as e:
            print(f"\033[1;31m[ERROR] {cfg['name']}: {e}\033[0m")

    # --- UPDATED LOGIC ---
    # Initialize search_term with the optional parameter
    search_term = str(initial_item) if initial_item is not None else ""
    
    page = 0
    idx = 0
    page_size = 10 
    conflicts = get_conflict_set()
    all_line_names = [cfg['name'] for cfg in LINE_CONFIGS]

    sys.stdout.write("\033[?25l") # Hide cursor

    while True:
        # --- 2. LIVE SEARCH LOGIC ---
        ftn_map = {}
        if search_term:
            safe_term = re.escape(search_term)
            # Ensure the regex lookahead doesn't go negative if search_term > 4 chars
            needed = 4 - len(search_term)
            
            if needed < 0:
                # If user typed more than 4 digits, search for the exact string instead
                pattern_str = rf"(?:item\s*#?\s*|#|/){safe_term}(?!\d|\.|-)"
            else:
                # \d{{{needed}}} ensures we only finish matches that result in 4 digits
                # (?!\d|\.|-) prevents matching things like 1234-5 or 1234.5
                pattern_str = rf"(?:item\s*#?\s*|#|/){safe_term}\d{{{needed}}}(?!\d|\.|-)"
            item_pattern = re.compile(pattern_str, re.IGNORECASE)

            for entry in all_ftn_data:
                if item_pattern.search(entry['comment']):
                    f_num = entry['ftn']
                    if f_num not in ftn_map: 
                        ftn_map[f_num] = {"comments": set(), "lines": {}}
                    ftn_map[f_num]["comments"].add(entry['comment'])
                    ftn_map[f_num]["lines"][entry['line']] = entry['comment']
        
        current_results = []
        for f_num in sorted(ftn_map.keys()):
            for comment in sorted(list(ftn_map[f_num]["comments"])):
                line_status = {n: (ftn_map[f_num]['lines'].get(n) == comment) for n in all_line_names}
                current_results.append({'ftn': f_num, 'comment': comment, 'lines': line_status})

        # --- 3. UI CALCULATION ---
        total = len(current_results)
        total_pages = max(1, (total + page_size - 1) // page_size)
        page = max(0, min(page, total_pages - 1))
        batch = current_results[page * page_size : (page + 1) * page_size]
        idx = min(idx, max(0, len(batch) - 1))

        # --- 4. DRAW UI ---
        sys.stdout.write("\033[H")
        bread = f" SEARCH BY ITEM: {search_term if search_term else '____'}"
        stats = f"TOTAL: {total} | PAGE: {page+1}/{total_pages}"
        sys.stdout.write(f"{BAR_COLOR} {bread:<55}{stats:>29}{RESET}\033[K\n")
        
        sys.stdout.write(f"{SUB_COLOR}{'—' * 85}{RESET}\033[K\n")
        sys.stdout.write(f"{HEAD_COLOR}     {'FTN':<9}   {'DESCRIPTION / TOOL COMMENTS'}{RESET}\033[K\n")
        sys.stdout.write(f"{SUB_COLOR}{'—' * 85}{RESET}\033[K\n")

        content_lines = []
        if not search_term:
            content_lines.append("   \033[1;30mStart typing a 4-digit item number...\033[0m")
        elif not batch:
            content_lines.append("   \033[1;31mNo items found matching this search.\033[0m")
        else:
            for i, item in enumerate(batch):
                selector = f"{SEL_CURSOR} > {RESET}" if i == idx else "   "
                is_red = item['ftn'] in conflicts
                num_style = NUM_CONFLICT if is_red else NUM_NORMAL
                ftn_disp = f"{SUB_COLOR}[{RESET}{num_style}{item['ftn']}{RESET}{SUB_COLOR}]{RESET}"

                content_lines.append(f" {selector} {ftn_disp} {DESC_COLOR}{item['comment']}{RESET}")
                tags = []
                for ln, active in item['lines'].items():
                    tag = f"\033[90m[\033[31m{ln:^7}\033[22;90m]\033[0m" if active else f"\033[2;90m[{f'-{ln}-':^7}]\033[0m"
                    tags.append(tag)
                content_lines.append(f"      {SUB_COLOR}└─{RESET} {' '.join(tags)}")

        while len(content_lines) < (page_size * 2):
            content_lines.append("")

        for line in content_lines:
            sys.stdout.write(f"{line}\033[K\n")

        sys.stdout.write(f"{SUB_COLOR}{'—' * 85}{RESET}\033[K\n")
        footer_text = " [UP/DN] Select  [L/R] Page  [C] Copy  [I] Item Details  [ENTER] Clear  [ESC] Exit"
        sys.stdout.write(f"{BAR_COLOR} {footer_text:<84}{RESET}\033[K")
        sys.stdout.flush()

        # --- 5. INPUT ---
        key = readchar.readkey()
        
        if key == readchar.key.ESC:
            sys.stdout.write("\033[?25h")
            break
        elif key == readchar.key.UP:
            if idx > 0: idx -= 1
        elif key == readchar.key.DOWN:
            if idx < len(batch) - 1: idx += 1
        elif key == readchar.key.LEFT:
            if page > 0: page -= 1; idx = 0
        elif key == readchar.key.RIGHT:
            if (page + 1) < total_pages: page += 1; idx = 0
        elif key.lower() == 'c' and batch:
            pyperclip.copy(batch[idx]['comment'])
            sys.stdout.write(f"\r{BAR_COLOR} \033[1;32m{'>> COPIED DESCRIPTION TO CLIPBOARD':<84}{RESET}")
            sys.stdout.flush()
            time.sleep(0.8)
        elif key.lower() == 'i' and batch:
            item_list = extract_item_numbers(batch[idx]['comment'])
            if item_list:
                sys.stdout.write("\033[?25h")
                for itm in item_list: show_item_specs(app, itm)
                sys.stdout.write("\033[?25l")
                os.system('cls')
            else:
                sys.stdout.write(f"\r{BAR_COLOR} \033[1;91m{'>> NO ITEM # FOUND IN DESCRIPTION':<84}{RESET}")
                sys.stdout.flush()
                time.sleep(0.8)
        elif key in (readchar.key.ENTER, '\r'):
            search_term = ""; page, idx = 0, 0
        elif key == readchar.key.BACKSPACE:
            search_term = search_term[:-1]; page, idx = 0, 0
        elif len(key) == 1 and key.isprintable():
            # Standard logic only allows adding characters if under 4, 
            # but pre-search might already have them.
            if len(search_term) < 4:
                search_term += key; page, idx = 0, 0

def run_db_search(app):
    """Flicker-free search with same layout as Item Search."""
    app.history.clear()
    app.push_history("SEARCH BY FTN")

    # 1. PRE-FETCH DATA
    app.clear("Caching Tool Database with Specs...")
    master_db = {}
    SCALE = 100000.0
    rev_life = {v: k for k, v in LIFE_TYPES.items()}
    rev_kind = {v: k for k, v in TOOL_KINDS.items()}

    for cfg in LINE_CONFIGS:
        cfg_name = cfg['name']
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg['ip']},1433;DATABASE={cfg['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=2;")
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                query = """
                SELECT t.FTN, t.FTNComment, t.Type, c.Kind, 
                       c.StandardDiameter, c.MinimumDiameter, c.MaximumDiameter,
                       c.StandardLength, c.MinimumLength, c.MaximumLength,
                       c.ToolLife, c.ToolLifeWarning, c.ToolLifeType
                FROM [dbo].[FunctionalToolData] t
                LEFT JOIN [dbo].[FunctionalToolCutterData] c ON t.FTNID = c.FTNID
                """
                cursor.execute(query)
                for row in cursor.fetchall():
                    ftn = str(row[0]).zfill(8)
                    comment = str(row[1] or "No Comment").strip()
                    kind_id = str(row[3])
                    life_type_id = str(row[12])
                    
                    spec = {
                        "line": cfg_name, 
                        "type": row[2], 
                        "kind": rev_kind.get(kind_id, f"Unk({kind_id})"),
                        "std_d": (row[4] or 0) / SCALE, "min_d": (row[5] or 0) / SCALE, "max_d": (row[6] or 0) / SCALE,
                        "std_l": (row[7] or 0) / SCALE, "min_l": (row[8] or 0) / SCALE, "max_l": (row[9] or 0) / SCALE,
                        "life": row[10], "warn": row[11], 
                        "l_type": rev_life.get(life_type_id, f"C{life_type_id}")
                    }
                    if ftn not in master_db: master_db[ftn] = {}
                    if comment not in master_db[ftn]: master_db[ftn][comment] = []
                    master_db[ftn][comment].append(spec)
        except Exception:
            pass 

    search_term = ""
    idx = 0
    page = 0
    page_size = 8  # Adjusted for sub-row space
    all_line_names = [cfg['name'] for cfg in LINE_CONFIGS]
    conflicts = get_conflict_set() 

    sys.stdout.write("\033[?25l") # Hide cursor

    search_term = ""
    idx = 0
    page = 0
    page_size = 10
    all_line_names = [cfg['name'] for cfg in LINE_CONFIGS]
    conflicts = get_conflict_set() 

    sys.stdout.write("\033[?25l")

    while True:
        # --- 1. LOGIC FIRST (Define 'total' and 'batch' here) ---
        query = search_term.lstrip('0')
        flat_results = []
        
        if search_term:
            # Match search_term against your master_db keys
            matching_ftns = sorted([f for f in master_db.keys() if f.lstrip('0').startswith(query)])
            for f in matching_ftns:
                for comment, line_specs in master_db[f].items():
                    flat_results.append({'ftn': f, 'comment': comment, 'specs': line_specs})

        total = len(flat_results) # <--- THIS DEFINES 'total'
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        page = max(0, min(page, total_pages - 1))
        batch = flat_results[page * page_size : (page + 1) * page_size]

        # --- 2. DRAW UI SECOND ---
        sys.stdout.write("\033[H") 
        
        # Now 'total' is defined and safe to use
        bread = f"SEARCH BY FTN: {search_term if search_term else '____'}"
        stats = f"TOTAL: {total} | PAGE: {page+1}/{total_pages}"
        sys.stdout.write(f"{BAR_COLOR} {bread:<55}{stats:>29}{RESET}\033[K\n")
        
        # 3. Headers
        sys.stdout.write(f"{SUB_COLOR}{'—' * 85}{RESET}\033[K\n")
        sys.stdout.write(f"{HEAD_COLOR}     {'FTN':<9}   {'DESCRIPTION / TOOL COMMENTS'}{RESET}\033[K\n")
        sys.stdout.write(f"{SUB_COLOR}{'—' * 85}{RESET}\033[K\n")

        max_rows = page_size * 2  # each result uses 2 lines

        content_lines = []

        if not search_term:
            content_lines.append("   \033[1;30mStart typing a Tool Number...\033[0m")
            content_lines.append("")
        elif not batch:
            content_lines.append("   \033[1;31mNo matching database entries found.\033[0m")
            content_lines.append("")
        else:
            for i, res in enumerate(batch):
                selector = f"{SEL_CURSOR} > {RESET}" if i == idx else "   "
                is_red = res['ftn'] in conflicts
                num_style = NUM_CONFLICT if is_red else NUM_NORMAL
                ftn_display = f"{SUB_COLOR}[{RESET}{num_style}{res['ftn']}{RESET}{SUB_COLOR}]{RESET}"

                # Main row
                content_lines.append(
                    f" {selector} {ftn_display} {DESC_COLOR}{res['comment']}{RESET}"
                )

                # Tags row
                active_lines = [s['line'] for s in res['specs']]
                tags = []
                for ln in all_line_names:
                    tags.append(
                        f"\033[90m[\033[31m{ln:^7}\033[22;90m]\033[0m"
                        if ln in active_lines
                        else f"\033[2;90m[{f'-{ln}-':^7}]\033[0m"
                    )

                content_lines.append(f"      {SUB_COLOR}└─{RESET} {' '.join(tags)}")

        while len(content_lines) < max_rows:
            content_lines.append("")

        for line in content_lines:
            sys.stdout.write(f"{line}\033[K\n")


        # 6. Footer
        sys.stdout.write(f"{SUB_COLOR}{'—' * 85}{RESET}\033[K\n")
        footer = " [UP/DN] Select  [L/R] Page  [C] Copy  [S] Specs  [I] Item Details  [ESC] Exit"
        sys.stdout.write(f"{BAR_COLOR} {footer}{RESET}\033[K")
        
        sys.stdout.flush()

        # --- INPUT ---
        key = readchar.readkey()
        if key == readchar.key.ESC:
            sys.stdout.write("\033[?25h")
            break
        elif key == readchar.key.UP:
            if idx > 0: idx -= 1
        elif key == readchar.key.DOWN:
            if idx < len(batch) - 1: idx += 1
        elif key == readchar.key.LEFT:
            if page > 0: page -= 1; idx = 0
        elif key == readchar.key.RIGHT:
            if (page + 1) < total_pages: page += 1; idx = 0
        elif key == readchar.key.BACKSPACE:
            search_term = search_term[:-1]; page, idx = 0, 0
        elif key in (readchar.key.ENTER, '\r'):
            search_term = ""; page, idx = 0, 0
        elif key.lower() == 'c' and batch:
                # Get the comment of the item the cursor is pointing at
                desc_to_copy = batch[idx]['comment']
                pyperclip.copy(desc_to_copy)
                
                # Visual Feedback: Briefly flash a message in the footer area
                sys.stdout.write(f"\r{BAR_COLOR} \033[1;32m{'>> COPIED DESCRIPTION TO CLIPBOARD':<84}{RESET}")
                sys.stdout.flush()
                time.sleep(0.8)
        elif key.lower() == 'i' and batch:
            items = extract_item_numbers(batch[idx]['comment'])
            if items:
                sys.stdout.write("\033[?25h")
                for itm in items: show_item_specs(app,itm)
                sys.stdout.write("\033[?25l")
                os.system('cls')
            else:
                    # Visual Feedback: Briefly flash a message in the footer area
                    sys.stdout.write(f"\r{BAR_COLOR} \033[1;91m{'>> NO ITEM # FOUND IN DESCRIPTION':<84}{RESET}")
                    sys.stdout.flush()
                    time.sleep(0.8)
        elif key.lower() == 's' and batch:
            # Assuming show_specs_subview is defined as discussed before
            show_specs_subview(batch[idx], conflicts) 
            os.system('cls')
        elif len(key) == 1 and key.isprintable():
            if len(search_term) < 8:
                search_term += key; page, idx = 0, 0

def show_specs_subview(selected_item, conflicts):
    """Detailed specifications view with high-visibility range values."""
    sys.stdout.write("\033[?25l")
    os.system('cls')
    
    def print_row(col1_str, col2_str=""):
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        visible_len = len(ansi_escape.sub('', col1_str))
        padding = " " * max(2, (44 - visible_len))
        sys.stdout.write(f" {col1_str}{padding}{col2_str}\n")

    ftn = selected_item['ftn']
    comment = selected_item['comment']
    specs = selected_item['specs']

    # Header
    bread = f" SPECIFICATIONS VIEW: {ftn}"
    print(f"{BAR_COLOR} {bread:<84}{RESET}\033[K")
    print(f"{SUB_COLOR}{'—' * 85}{RESET}\033[K")

    is_red = ftn in conflicts
    num_style = NUM_CONFLICT if is_red else NUM_NORMAL
    ftn_display = f"{SUB_COLOR}[{RESET}{num_style}{ftn}{RESET}{SUB_COLOR}]{RESET}"
    print(f" {ftn_display} {DESC_COLOR}\"{comment}\"{RESET}\033[K")
    print(f"{SUB_COLOR}{'—' * 85}{RESET}\033[K\n")

    # Define the "Pop" color for ranges (Bright Yellow)
    POP = "\033[1;33m" 
    VAL_GRAY = "\033[90m"

    for i in range(0, len(specs), 2):
        s1 = specs[i]
        s2 = specs[i+1] if (i+1) < len(specs) else None

        # Line Titles
        t1 = f"\033[90m[\033[31m {s1['line']:^7} \033[90m]\033[0m"
        t2 = f"\033[90m[\033[31m {s2['line']:^7} \033[90m]\033[0m" if s2 else ""
        print_row(t1, t2)

        # Kind
        k1 = f"{HEAD_COLOR}Kind     :{RESET} {DESC_COLOR}{s1['kind']}{RESET}"
        k2 = f"{HEAD_COLOR}Kind     :{RESET} {DESC_COLOR}{s2['kind']}{RESET}" if s2 else ""
        print_row(k1, k2)

        # Diameter - Pop the Min/Max
        d1 = f"{HEAD_COLOR}Diameter :{RESET} {DESC_COLOR}{s1['std_d']:.4f}{RESET} {VAL_GRAY}({POP}{s1['min_d']:.3f}{VAL_GRAY}/{POP}{s1['max_d']:.3f}{VAL_GRAY}){RESET}"
        d2 = f"{HEAD_COLOR}Diameter :{RESET} {DESC_COLOR}{s2['std_d']:.4f}{RESET} {VAL_GRAY}({POP}{s2['min_d']:.3f}{VAL_GRAY}/{POP}{s2['max_d']:.3f}{VAL_GRAY}){RESET}" if s2 else ""
        print_row(d1, d2)

        # Length - Pop the Min/Max
        l1 = f"{HEAD_COLOR}Length   :{RESET} {DESC_COLOR}{s1['std_l']:.4f}{RESET} {VAL_GRAY}({POP}{s1['min_l']:.3f}{VAL_GRAY}/{POP}{s1['max_l']:.3f}{VAL_GRAY}){RESET}"
        l2 = f"{HEAD_COLOR}Length   :{RESET} {DESC_COLOR}{s2['std_l']:.4f}{RESET} {VAL_GRAY}({POP}{s2['min_l']:.3f}{VAL_GRAY}/{POP}{s2['max_l']:.3f}{VAL_GRAY}){RESET}" if s2 else ""
        print_row(l1, l2)

        # Life - Pop the Limit and Warning
        f1 = f"{HEAD_COLOR}Life     :{RESET} {DESC_COLOR}{s1['l_type']}{RESET} {VAL_GRAY}(L:{POP}{s1['life']}{VAL_GRAY} W:{POP}{s1['warn']}{VAL_GRAY}){RESET}"
        f2 = f"{HEAD_COLOR}Life     :{RESET} {DESC_COLOR}{s2['l_type']}{RESET} {VAL_GRAY}(L:{POP}{s2['life']}{VAL_GRAY} W:{POP}{s2['warn']}{VAL_GRAY}){RESET}" if s2 else ""
        print_row(f1, f2)
        
        print(f"\033[K") 

    # Footer
    print(f"\n{SUB_COLOR}{'—' * 85}{RESET}\033[K")
    print(f"{BAR_COLOR} PRESS ANY KEY TO RETURN TO SEARCH{' ':>50}{RESET}", end="")
    sys.stdout.flush()
    
    readchar.readkey()

def get_first_available(category_name):
    ranges = SEARCH_RANGES.get(category_name, [])
    used_numbers = set()

    for cfg in LINE_CONFIGS:
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg['ip']},1433;DATABASE={cfg['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=1;")
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                for min_ftn, max_ftn in ranges:
                    cursor.execute("SELECT [FTN] FROM [dbo].[FunctionalToolData] WHERE [FTN] BETWEEN ? AND ?", (min_ftn, max_ftn))
                    for row in cursor.fetchall():
                        used_numbers.add(row[0])
        except:
            continue

    for min_ftn, max_ftn in ranges:
        for num in range(min_ftn, max_ftn + 1):
            if num not in used_numbers:
                return str(num).zfill(8)
    return ""

def run_available_search(app):
    app.history.clear()
    menu_options = {k: k for k in SEARCH_RANGES.keys()}
    category_name = app.get_menu_choice(menu_options, "Find Available Numbers")
    
    if category_name == "BACK_REQ":
        return

    ranges = SEARCH_RANGES[category_name]

    app.clear(f"Scanning {category_name}...")
    range_text = ", ".join([f"{a}-{b}" for a, b in ranges])
    print(f"Checking ranges {range_text} across all lines...")

    used_numbers = set()

    for cfg in LINE_CONFIGS:
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg['ip']},1433;DATABASE={cfg['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=1;")
            
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()

                for min_ftn, max_ftn in ranges:
                    query = "SELECT [FTN] FROM [dbo].[FunctionalToolData] WHERE [FTN] BETWEEN ? AND ?"
                    cursor.execute(query, (min_ftn, max_ftn))
                    rows = cursor.fetchall()
                    for row in rows:
                        used_numbers.add(row[0])

            print(f"  \033[92m[OK]\033[0m {cfg['name']} scanned.")
        except Exception:
            print(f"  \033[1;31m[OFFLINE]\033[0m {cfg['name']} skipped.")

    #BUILD FULL RANGE SET
    full_range = set()
    for min_ftn, max_ftn in ranges:
        full_range.update(range(min_ftn, max_ftn + 1))

    available = sorted(full_range - used_numbers)

    app.clear(f"Available {category_name}")
    if not available:
        print(f"\033[1;31mNo available numbers found!\033[0m")
    else:
        print(f"Found \033[1;32m{len(available)}\033[0m available spots.\n")
        
        display_limit = 50
        for i, num in enumerate(available[:display_limit]):
            print(f"  {num:08}", end="  ")
            if (i + 1) % 5 == 0:
                print()
        
        if len(available) > display_limit:
            print(f"\n\n... and {len(available) - display_limit} more.")

        formatted_list = [f"{n:08}" for n in available]
        pyperclip.copy("\n".join(formatted_list))

        print(f"\n\n\033[1;33mCopied {len(formatted_list)} available tool numbers to clipboard.\033[0m")

    print("\nPress any key to return...")
    readchar.readkey()

def check_tool_exists(tool_num):
    found_on = []
    search_target = tool_num.zfill(8)
    for cfg in LINE_CONFIGS:
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg['ip']},1433;DATABASE={cfg['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=1;")
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT [FTN] FROM [dbo].[FunctionalToolData] WHERE [FTN] = ?", (int(search_target),))
                if cursor.fetchone():
                    found_on.append(cfg['name'])
        except Exception:
            pass
    return found_on

def get_longest_comment(tool_num):
    longest_comment = ""
    for cfg in LINE_CONFIGS:
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg['ip']},1433;DATABASE={cfg['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=1;")

            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                query = "SELECT [FTNComment] FROM [dbo].[FunctionalToolData] WHERE [FTN] = ?"
                cursor.execute(query, (int(tool_num),))
                
                row = cursor.fetchone()
                # Use row to get the actual text string
                if row and row[0]:
                    current_text = str(row[0]).strip()
                    if len(current_text) > len(longest_comment):
                        longest_comment = current_text
        except Exception:
            continue

    return longest_comment if longest_comment else "NO COMMENT FOUND"

def save_and_generate(action, tool_num, fields):
    root = ET.Element("MASData")
    func_tools = ET.SubElement(root, "FunctionalTools")
    f_tool = ET.SubElement(func_tools, "FunctionalTool", {"action": action, "number": tool_num})
    data = {"ItfDiameter": "0", "StdLength": "4.0", "MinLength": "2.0", "MaxLength": "14.0", "Coolant": "1", "AtcSpeed": "0"}
    data.update(fields)
    for tag, val in data.items(): 
        ET.SubElement(f_tool, tag).text = str(val)
    xml_str = ET.tostring(root, encoding='utf-8')
    pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
    success_count = 0
    filename = f"Tool_{tool_num}.xml"
    for cfg in LINE_CONFIGS:
        p = cfg['path']
        try:
            if os.path.exists(p): # Check if the network path is reachable
                full_path = os.path.join(p, filename)
                with open(full_path, "w", encoding="utf-8") as f: 
                    f.write(pretty_xml)
                print(f"  \033[92m[OK]\033[0m Saved to {cfg['name']} ({p})")
                success_count += 1
            else:
                print(f"  \033[1;31m[OFFLINE]\033[0m Path unreachable: {p}")
        except Exception as e:
            print(f"  \033[1;31m[ERROR]\033[0m {cfg['name']}: {e}")

    if success_count == 0:
        with open(filename, "w", encoding="utf-8") as f: 
            f.write(pretty_xml)
        print(f"\n\033[93mSaved locally as {filename} (No network paths reached).\033[0m")  

def get_line_specific_tl_type(tool_num, line_cfg):
    """
    Looks up the ToolLifeType for a specific tool on a specific line.
    Returns 1 (Distance) as a safe default if the tool is missing or line is offline.
    """
    ftn_int = int(tool_num)
    try:
        conn_str = (
            f"DRIVER={{SQL Server}};SERVER={line_cfg['ip']},1433;DATABASE={line_cfg['db']};"
            f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};"
            f"Connection Timeout=1;"
        )
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            query = """
                SELECT c.ToolLifeType 
                FROM [dbo].[FunctionalToolData] t
                JOIN [dbo].[FunctionalToolCutterData] c ON t.FTNID = c.FTNID
                WHERE t.FTN = ?
            """
            cursor.execute(query, (ftn_int,))
            row = cursor.fetchone()
            if row:
                return row[0]
    except Exception:
        pass # If the line is offline, we'll fall back to 1
            
    return 1

def get_all_lines_tool_data(tool_num):
    """Scans all lines and stores raw codes (Kind, Type, LifeType) for rebroadcast."""
    SCALE = 100000.0
    results = {}

    for cfg_item in LINE_CONFIGS:
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg_item['ip']},1433;DATABASE={cfg_item['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=1;")
            
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM [dbo].[FunctionalToolData] WHERE [FTN] = ?", (int(tool_num),))
                ft_row = cursor.fetchone()
                if not ft_row: continue

                ft_cols = [col[0] for col in cursor.description]
                ft_dict = dict(zip(ft_cols, ft_row))
                
                cursor.execute("SELECT * FROM [dbo].[FunctionalToolCutterData] WHERE [FTNID] = ?", (ft_dict['FTNID'],))
                c_row = cursor.fetchone()
                
                if c_row:
                    c_cols = [col[0] for col in cursor.description]
                    c_dict = dict(zip(c_cols, c_row))
                    raw_type = ft_dict.get('FTNType') or ft_dict.get('Type') or ""
                    tool_type_code = str(raw_type).strip()
                    
                    # Store the RAW values (e.g., 'EM', '3', '2')
                    results[cfg_item['name']] = {
                        "Comment": (ft_dict.get('FTNComment') or "").strip(),
                        "Type": tool_type_code,   # From TOOL_TYPES (e.g. 'EM')
                        "Kind": c_dict.get('Kind', "0"),        # From TOOL_KINDS (e.g. '3')
                        "StdDiameter": c_dict.get('StandardDiameter', 0) / SCALE,
                        "MinDiameter": c_dict.get('MinimumDiameter', 0) / SCALE,
                        "MaxDiameter": c_dict.get('MaximumDiameter', 0) / SCALE,
                        "StdLength": c_dict.get('StandardLength', 0) / SCALE,
                        "MinLength": c_dict.get('MinimumLength', 0) / SCALE,
                        "MaxLength": c_dict.get('MaximumLength', 0) / SCALE,
                        "Life": int(c_dict.get('ToolLife', 0)),
                        "LifeWarning": int(c_dict.get('ToolLifeWarning', 0)),
                        "TlType": c_dict.get('ToolLifeType', "0") # From LIFE_TYPES (e.g. '2')
                    }
        except:
            continue
    return results
        
def run_update_feature(app, tool_num):
    # Get the snapshot of every line as it is right now
    line_data_map = get_all_lines_tool_data(tool_num)
    
    if not line_data_map:
        print(f"\n\033[91m[ERROR] Tool {tool_num} not found on any active lines.{RESET}")
        readchar.readkey()
        return

    def get_human_name(val, lookup_dict):
        for name, code in lookup_dict.items():
            if str(code) == str(val):
                return name
        return val

    first_line = list(line_data_map.keys())[0]
    tool_comment = line_data_map[first_line]['Comment']

    while True:
        update_options = {
            "Comment": ("Comment", False),
            "Tool Type (EM, DR, etc)": ("Type", False),
            "Tool Kind": ("Kind", True),
            "Clear Diameters": ("CLEAR_DIAM", True), # New Option
            "Standard Diameter": ("StdDiameter", True),
            "Min Diameter": ("MinDiameter", True),
            "Max Diameter": ("MaxDiameter", True),
            "Standard Length": ("StdLength", True),
            "Min Length": ("MinLength", True),
            "Max Length": ("MaxLength", True),
            "Life Value": ("Life", True),
            "Life Warning": ("LifeWarning", True),
            "Life Type (Count/Dist)": ("TlType", True),
            "EXIT": ("EXIT", False) 
        }

        main_title = f"UPDATE {tool_num} | {tool_comment}"
        choice_data = app.get_menu_choice(update_options, main_title)
        
        if choice_data == "BACK_REQ" or choice_data[0] == "EXIT":
            return

        tag_name, is_cutter_field = choice_data

        # --- SPECIAL LOGIC: CLEAR DIAMETER ---
        if tag_name == "CLEAR_DIAM":
            confirm_msg = f"Reset {HEAD_COLOR}Std/Min/Max Diameters{RESET} to {NUM_CONFLICT}0{RESET} on ALL lines?"
            if app.confirm("Clear Diameters", confirm_msg):
                for line_name, existing_data in line_data_map.items():
                    update_payload = existing_data.copy()
                    # Set all three to 0
                    update_payload["StdDiameter"] = "0"
                    update_payload["MinDiameter"] = "0"
                    update_payload["MaxDiameter"] = "0"

                    save_smart_update(
                        "UPDATE", 
                        tool_num, 
                        update_payload, 
                        "DIAM_RESET", # Tag for filename
                        True, 
                        target_line=line_name
                    )
                line_data_map = get_all_lines_tool_data(tool_num)
                print(f"\n{BAR_COLOR}Diameters cleared. Press any key...{RESET}")
                readchar.readkey()
            continue

        # --- SUB-MENU HEADER BUILDER ---
        all_vals = [data.get(tag_name) for data in line_data_map.values()]
        is_conflict = len(set(all_vals)) > 1
        
        header_lines = [f"{HEAD_COLOR}Current {tag_name} values across lines:{RESET}"]
        for line_name, data in line_data_map.items():
            raw_val = data.get(tag_name, "N/A")
            
            if tag_name == "Kind":
                display_val = get_human_name(raw_val, TOOL_KINDS)
            elif tag_name == "Type":
                display_val = get_human_name(raw_val, TOOL_TYPES)
            elif tag_name == "TlType":
                display_val = get_human_name(raw_val, LIFE_TYPES)
            else:
                display_val = raw_val
            
            val_color = NUM_CONFLICT if is_conflict else DESC_COLOR
            header_lines.append(f"  {HEAD_COLOR}{line_name:<12}{RESET} : {val_color}{display_val}{RESET}")
        
        sub_header = "\n".join(header_lines)

        # --- SELECTION LOGIC ---
        if tag_name == "Kind":
            new_val = app.get_menu_with_header(TOOL_KINDS, "SELECT NEW KIND", sub_header)
        elif tag_name == "Type":
            new_val = app.get_menu_with_header(TOOL_TYPES, "SELECT NEW TYPE", sub_header)
        elif tag_name == "TlType":
            new_val = app.get_menu_with_header(LIFE_TYPES, "SELECT LIFE TYPE", sub_header)
        else:
            app.clear(f"UPDATE {tag_name}")
            print(sub_header)
            print(f"{BAR_COLOR}" + "—" * 50 + f"{RESET}")
            new_val = input(f"{HEAD_COLOR}Enter new value for {tag_name}:{RESET} ").strip()
            
            if new_val and new_val != "BACK_REQ":
                app.history.append(new_val[:15])

        if new_val in ["BACK_REQ", "", None]: 
            continue

        # --- PREPARE HUMAN READABLE VALUE FOR CONFIRMATION ---
        if tag_name == "Kind":
            display_new_val = get_human_name(new_val, TOOL_KINDS)
        elif tag_name == "Type":
            display_new_val = get_human_name(new_val, TOOL_TYPES)
        elif tag_name == "TlType":
            display_new_val = get_human_name(new_val, LIFE_TYPES)
        else:
            display_new_val = new_val

        # --- BROADCAST PRESERVING OLD DATA ---
        confirm_msg = f"Push '{DESC_COLOR}{display_new_val}{RESET}' to {HEAD_COLOR}{tag_name}{RESET} on ALL found lines?"
        
        if app.confirm("Finalize", confirm_msg):
            if "FINALIZE" not in app.history:
                app.push_history("FINALIZE")

            for line_name, existing_data in line_data_map.items():
                update_payload = existing_data.copy()
                update_payload[tag_name] = new_val

                save_smart_update(
                    "UPDATE", 
                    tool_num, 
                    update_payload, 
                    tag_name, 
                    is_cutter_field, 
                    target_line=line_name
                )
            line_data_map = get_all_lines_tool_data(tool_num)
        else:
            app.clear(f"UPDATE CANCELLED")
            print(f"\n{NUM_CONFLICT} Update cancelled. {RESET}")
            
        print(f"\n{SUB_COLOR}Press any key to continue...{RESET}")
        readchar.readkey()

def save_smart_update(action, tool_num, tool_data, updated_tag, is_cutter_field, target_line=None):
    """
    Generates XML with line breaks and proper indentation for CNC readability.
    Wraps the tool in a <FunctionalTools> container.
    """
    for cfg_item in LINE_CONFIGS:
        if target_line and cfg_item['name'] != target_line:
            continue

        filename = f"Update_{updated_tag}_{tool_num}.xml"
        
        # Root: <MASData>
        root = ET.Element("MASData")
        
        # Container: <FunctionalTools> (Required by some CNC systems)
        tools_container = ET.SubElement(root, "FunctionalTools")
        
        # Child: <FunctionalTool>
        f_tool = ET.SubElement(tools_container, "FunctionalTool", {
            "action": action, 
            "number": str(tool_num).zfill(8)
        })
        
        # --- HEADER ---
        ET.SubElement(f_tool, "Comment").text = str(tool_data.get("Comment", ""))
        ET.SubElement(f_tool, "Type").text = str(tool_data.get("Type", ""))

        # --- CUTTER ---
        cutter = ET.SubElement(f_tool, "Cutter", {"number": "1"})
        
        tags_to_push = {
            "Kind": "Kind",
            "StdLength": "StdLength",
            "MinLength": "MinLength",
            "MaxLength": "MaxLength",
            "StdDiameter": "StdDiameter",
            "MinDiameter": "MinDiameter",
            "MaxDiameter": "MaxDiameter",
            "Life": "Life",
            "LifeWarning": "LifeWarning",
            "TlType": "TlType"
        }

        for data_key, xml_tag in tags_to_push.items():
            val = tool_data.get(data_key, "0")
            ET.SubElement(cutter, xml_tag).text = str(val)

        # --- FORMATTING WITH LINE BREAKS ---
        raw_xml = ET.tostring(root, encoding='utf-8')
        reparsed = minidom.parseString(raw_xml)
        # Using toprettyxml creates the clean hierarchy and closes tags correctly
        xml_str = reparsed.toprettyxml(indent="  ")

        # Deployment
        path = cfg_item.get('path')
        if path and os.path.exists(path):
            try:
                with open(os.path.join(path, filename), "w", encoding="utf-8") as f:
                    f.write(xml_str)
                # Using your color constants/logic style
                print(f"  \033[92m[OK]\033[0m {cfg_item['name']}")
            except Exception as e:
                print(f"  \033[91m[FAIL]\033[0m {cfg_item['name']}: {e}")

def run_item_number_swap(app):
    app.history.clear()
    app.push_history("UPDATE ITEM #")
    
    app.clear("Update Item Number")
    old_item = input("Enter CURRENT Item Number: ").strip()
    if not old_item: return

    search_pattern = re.compile(
    rf"(?:item\s*#?\s*|#)"            # Trigger: 'item ' or '#'
    rf"{re.escape(old_item)}"         # The old item number
    rf"(?!\d|\.|-)",                  # Block if followed by digits, decimals, or dashes
    re.IGNORECASE
    )
    
    # 1. Map FTN to all its data across lines
    ftn_map = {}
    all_line_names = [cfg['name'] for cfg in LINE_CONFIGS]
    
    app.clear(f"Searching for Item #{old_item}...")
    
    for cfg in LINE_CONFIGS:
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg['ip']},1433;DATABASE={cfg['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=1;")
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT [FTN], [FTNComment] FROM [dbo].[FunctionalToolData]")
                for row in cursor.fetchall():
                    comment = str(row[1] or "").strip()
                    if search_pattern.search(comment):
                        ftn_num = str(row[0]).zfill(8)
                        
                        if ftn_num not in ftn_map:
                            ftn_map[ftn_num] = {"comments": set(), "lines": {}}
                        
                        ftn_map[ftn_num]["comments"].add(comment)
                        ftn_map[ftn_num]["lines"][cfg['name']] = comment
        except Exception:
            continue

    if not ftn_map:
        print(f"\n\033[1;33mNo tools found with Item #{old_item}\033[0m")
        readchar.readkey(); return

    # 2. Display Review
    app.clear("Review Matches Found")
    conflicts = get_conflict_set()
    
    for ftn_num in sorted(ftn_map.keys()):
        data = ftn_map[ftn_num]
        unique_comments = sorted(list(data["comments"]))
        
        is_red = ftn_num in conflicts
        color_code = "1;97;101" if is_red else "1;97"
        
        for comment in unique_comments:
            ftn_display = f"\033[90m[\033[{color_code}m{ftn_num}\033[0m\033[90m]\033[0m"
            print(f'  {ftn_display} \033[1;38;5;51m{comment}\033[0m')
            
            line_tags = []
            for name in all_line_names:
                if data["lines"].get(name) == comment:
                    # Tight 7-width active tag
                    tag = f"\033[90m[\033[31m{name:^7}\033[90m]\033[0m"
                else:
                    # Tight 7-width dash-wrapped inactive tag
                    inactive_text = f"-{name}-"
                    tag = f"\033[2;90m[{inactive_text:^7}]\033[0m"
                line_tags.append(tag)
            print(f"\033[2;90m    └─ \033[0m{' '.join(line_tags)}")

    print("\n" + "\033[90m—\033[0m" * 50)
    new_item = input("\033[1;97mEnter NEW Item Number (4-digit):\033[0m ").strip()
    if not new_item.isdigit() or len(new_item) != 4:
        print("\033[1;31mInvalid format. Update aborted.\033[0m")
        readchar.readkey(); return

    confirm = input(f"\nProceed with updating {len(ftn_map)} unique tool numbers? (y/n): ").lower()
    if confirm == 'y':
        print("\n\033[1;33m[ EXECUTING GLOBAL UPDATE... ]\033[0m\n")
        
        success_count = 0
        for ftn_num, data in ftn_map.items():
            for line_name, comment in data["lines"].items():
                new_comment = search_pattern.sub(f"#{new_item}", comment)
                
                # Find the config for this specific line to perform the TlType lookup
                target_cfg = next((c for c in LINE_CONFIGS if c['name'] == line_name), None)
                if not target_cfg: continue

                # --- STEP 1: Preserve TlType for this specific line ---
                current_tl_type = get_line_specific_tl_type(ftn_num, target_cfg)

                # --- STEP 2: Build XML with Protection ---
                root = ET.Element("MASData")
                func_tools = ET.SubElement(root, "FunctionalTools")
                f_tool = ET.SubElement(func_tools, "FunctionalTool", {"action": "UPDATE", "number": ftn_num})
                
                # Update the comment
                ET.SubElement(f_tool, "Comment").text = new_comment
                
                # Inject Cutter block to prevent TlType reset
                cutter = ET.SubElement(f_tool, "Cutter", {"number": "1"})
                ET.SubElement(cutter, "TlType").text = str(current_tl_type)
                
                # Stringify
                xml_str = ET.tostring(root, encoding='utf-8')
                pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
                pretty_xml = "\n".join([line for line in pretty_xml.split('\n') if line.strip()])
                
                # --- STEP 3: Deploy ---
                if target_cfg.get('path'):
                    filename = f"Update_{ftn_num}_ItemSwap.xml"
                    p = target_cfg['path']
                    try:
                        if os.path.exists(p):
                            with open(os.path.join(p, filename), "w", encoding="utf-8") as f:
                                f.write(pretty_xml)
                            
                            # Success Log
                            print(f"  \033[92m[OK]\033[0m {ftn_num} on \033[1;31m{line_name:^7}\033[0m -> #{new_item}")
                            success_count += 1
                        else:
                            print(f"  \033[1;31m[FAIL]\033[0m {line_name} path offline.")
                    except Exception as e:
                        print(f"  \033[1;31m[ERR]\033[0m {line_name}: {e}")
        
        print(f"\n\033[1;32mSUCCESS: {success_count} update files generated\033[0m")
    else:
        print("\nUpdate cancelled.")
    
    print("\nPress any key to return...")
    readchar.readkey()

def show_item_specs(app, item_no): # 'app' is now required and first
    DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")
    
    if not os.path.exists(DB_FILE):
        print(f"\n{NUM_CONFLICT} [ERROR] database.json not found. {RESET}")
        readchar.readkey(); return

    with open(DB_FILE, 'r') as f:
        data = json.load(f)

    item = next((i for i in data if str(i.get('itemNumber')) == str(item_no)), None)

    if not item:
        print(f"\n{NUM_CONFLICT} Item {item_no} not found. {RESET}")
        readchar.readkey(); return

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Header
        print(f"{DESC_COLOR}TOOLCRIB ({item_no}){RESET}")
        print(f"{BAR_COLOR}" + "—" * 50 + f"{RESET}")
        print(f"{BAR_COLOR}[ ITEM DETAILS ]{RESET}\n")

        fields = [
            ('itemNumber', 'Item Number'), ('descr', 'Description'),
            ('itemAliasNumber', 'Alias'), ('itemGroupDescr', 'Item Group'),
            ('itemSubGroupDescr', 'Sub Group'), ('supplierNumber', 'Supplier'),
            ('supplierPartNumber', 'Supplier Part #'), ('brand', 'Brand')
        ]

        for key_name, label in fields:
            val = item.get(key_name, 'N/A')
            print(f"{HEAD_COLOR}{label:<18}{RESET}: {val}")

        # --- SEARCH LOGIC ---
        supplier = str(item.get('supplierNumber', '')).lower()
        alias = item.get('itemAliasNumber')
        brand = item.get('brand', '')
        part_no = item.get('supplierPartNumber', '')
        
        can_open_msc = "msc" in supplier and alias
        can_google = not can_open_msc and (brand or part_no)

        # Footer Menu
        print("\n" + f"{SUB_COLOR}—{RESET}" * 50)
        
        # The 'F' key is now always functional because 'app' is guaranteed
        print(f"{BAR_COLOR}[ F ]{RESET} {HEAD_COLOR}Find Functional Tools (FTN){RESET}")

        if can_open_msc:
            print(f"{BAR_COLOR}[ SPACE ]{RESET} Open MSC Webpage")
        elif can_google:
            print(f"{BAR_COLOR}[ SPACE ]{RESET} Search Google for {brand} {part_no}")
        
        print(f"{SUB_COLOR}[ ANY OTHER KEY ]{RESET} Return to Search")

        # Handle Input
        key = readchar.readkey()
        
        if key.lower() == 'f':
            run_item_search(app, initial_item=item_no)
            continue 

        elif key == ' ':
            if can_open_msc:
                webbrowser.open(f"https://www.mscdirect.com/product/details/{alias}")
            elif can_google:
                search_query = f"{brand} {part_no}".strip().replace(" ", "+")
                webbrowser.open(f"https://www.google.com/search?q={search_query}")
            continue
            
        else:
            break

def search_tool_crib(app, initial_query=None):
    DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")
    
    # LOAD ONCE AT START OF SEARCH (Fast)
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = []

    search_term = initial_query if initial_query else ""
    idx = 0 
    last_line_count = 0

    os.system('cls' if os.name == 'nt' else 'clear')

    while True:

        if last_line_count > 0:
            sys.stdout.write(f"\033[{last_line_count}F")

        # HEADER
        sys.stdout.write(
            f"\033[1;36m[ TOOL CRIB ITEM SEARCH ]\033[0m\n"
            f"\033[1;33mSearching:\033[0m {search_term:<20} \033[5m|\033[0m\n"
            f"\033[1;30m(Arrows: Select | Enter: View | 'n': Clear | Esc: Exit)\033[0m\n\033[K\n"
        )

        # FILTERING
        found_items = [
            item for item in data 
            if str(item.get('itemNumber', '')).lower().startswith(search_term.lower())
        ]
        
        # AUTO-DISPLAY (Direct jump if one result found via initial_query)
        if len(found_items) == 1 and search_term != "":
            # Pass 'app' as the first argument here
            show_item_specs(app, found_items[0].get('itemNumber'))
            
            if initial_query: return # Bounce back to DB search
            search_term = ""; idx = 0; last_line_count = 0; os.system('cls'); continue

        # LIST RENDERING
        idx = max(0, min(idx, len(found_items) - 1)) if found_items else 0
        output = []
        if search_term and found_items:
            output.append(f"\033[1;32mMatches Found: {len(found_items)}\033[0m\033[K")
            for i, item in enumerate(found_items[:15]):
                cursor = f"\033[1;97;42m > \033[0m " if i == idx else "   "
                output.append(f"{cursor}{item.get('itemNumber')} : {str(item.get('descr'))[:45]}\033[K")
        elif search_term:
            output.append("\033[1;31mNo matches found.\033[0m\033[K")
        else:
            output.append("\033[1;30mStart typing an Item Number...\033[0m\033[K")

        while len(output) < 17: output.append("\033[K")
        sys.stdout.write("\n".join(output) + "\n")
        sys.stdout.flush()
        last_line_count = 4 + len(output)

        # INPUT
        key = readchar.readkey()
        if key == readchar.key.ESC: break
        elif key == readchar.key.UP: idx -= 1
        elif key == readchar.key.DOWN: idx += 1
        elif key == readchar.key.ENTER and found_items:
            show_item_specs(app,found_items[idx].get('itemNumber'))
            last_line_count = 0; os.system('cls')
        elif key == readchar.key.BACKSPACE: 
            search_term = search_term[:-1]; idx = 0 
        elif key.isprintable(): 
            if key.lower() == 'n': search_term = ""; idx = 0
            else: search_term += key; idx = 0

def get_std_dia(input_str):
    # Clean the string for parsing (remove 'mm' if present)
    clean_str = input_str.lower().replace("mm", "").strip()
    try:
        # Use your existing parse_size_to_float or float()
        val = parse_size_to_float(clean_str) 
        # If "mm" was in the original input, convert to inches
        if "mm" in input_str.lower():
            return round(val / 25.4, 4)
        return val
    except:
        return 0.0

def main():
    app = ToolApp()

    while True:
        app.history.clear()
        
        action = app.get_menu_choice({
            "ADD TOOL": "ADD", 
            "UPDATE TOOL": "UPDATE", 
            "DELETE TOOL": "DELETE",
            "SYNC TOOL": "SYNCTOOL", 
            "SEARCH (TOOL #)": "SEARCH",
            "SEARCH (BY KEYWORD)": "KSEARCH",
            "SEARCH (ITEM #)": "ISEARCH",
            "TOOLCRIB (ITEM #)": "CSEARCH",
            "TOOLCRIB (BY KEYWORD)": "CKSEARCH",
            "OTHER UTILITIES": "UTILITIES",
            "EXIT": "EXIT"
        }, "Main Menu")

        if action == "BACK_REQ" or action is None:
            continue

        if action == "EXIT":
            os._exit(0)

        # --- 1. Security Check ---
        if not IS_PROGRAMMER_MODE and action in ["ADD", "UPDATE", "DELETE", "UTILITIES", "SYNCTOOL"]:
            app.clear("Security Check")
            print("\033[1;33mThis action is restricted\033[0m")
            pw = input("Enter Password: ").strip()
            if pw != SHOP_FLOOR_PASSWORD:
                print("\033[1;31m\nInvalid Password. Access Denied.\033[0m")
                readchar.readkey()
                continue

        # --- 2. Read-Only & Utility Routes ---
        if action == "CKSEARCH": 
            CribSearch.ToolSearcher(os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.json")).run(); continue
        if action == "SEARCH":
            run_db_search(app); continue
        if action == "KSEARCH":
            run_keyword_search(app); continue
        if action =="SYNCTOOL":
            SyncLineTool.process(); continue
        if action == "CSEARCH":
            search_tool_crib(app); continue
        if action == "ISEARCH":
            run_item_search(app); continue
        
        if action == "UTILITIES":
            handle_utilities(app)
            continue

        # --- 3. CRUD Operations ---
        if action == "ADD":
            add(app)
        elif action == "UPDATE":
            update(app)
        elif action == "DELETE":
            delete(app)

def handle_utilities(app):
    sub_action = app.get_menu_choice({
        "UPDATE ITEM #": "ITEM_SWAP",
        "LIST OPEN TOOL #": "AVAILABLE",
        "SYNC TOOL CRIB DB": "SYNCTOOLCRIB",
        "STANDARDIZE DESCRIPTIONS": "STANDARDIZE",
        "MLTE SETTINGS": "SETTINGS",
        "BACK": "BACK"
    }, "Utilities Menu")

    if sub_action == "AVAILABLE":
        run_available_search(app)
    elif sub_action == "ITEM_SWAP":
        run_item_number_swap(app)
    elif sub_action == "SETTINGS":
        editor = EditSettings.SettingsEditor()
        signal = editor.run()
        if signal == "RESTART":
            app.clear("Settings Updated")
            print("\033[1;32mConfig saved successfully.\033[0m")
            print("\033[1;33mPlease relaunch MLTE to apply changes.\033[0m")
            print("\033[90m\nClosing session...\033[0m")
            time.sleep(4)
            sys.exit()
    elif sub_action == "SYNCTOOLCRIB":
        app.clear("Syncing...")
        sync_database()
        readchar.readkey()
    elif sub_action == "STANDARDIZE":
        script_path = os.path.join(os.path.dirname(__file__), "Standardize-Descriptions.py")
        subprocess.Popen(["start", "cmd", "/k", sys.executable, script_path], shell=True)

def add(app):
    tool_cat = app.get_menu_choice({k: k for k in SEARCH_RANGES.keys()}, "Select Category")
    if tool_cat == "BACK_REQ": return

    app.clear("Finding available number...")
    suggested_num = get_first_available(tool_cat)

    app.clear("Identification")
    print(f"Suggested {tool_cat} tool #: confirm or edit:")
    app.inject_type(suggested_num)
    
    raw_num = input("> ").strip()
    if not raw_num.isdigit(): return
    
    tool_num = raw_num.zfill(8)
    app.push_history(tool_num)

    app.clear("Overwrite Warning")
    
    all_line_names = [cfg['name'] for cfg in LINE_CONFIGS]
    conflicts = get_conflict_set()
    local_tool_data = {} 

    # --- Live Scan to find conflicting descriptions ---
    for cfg in LINE_CONFIGS:
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg['ip']},1433;DATABASE={cfg['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=1;")
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT [FTNComment] FROM [dbo].[FunctionalToolData] WHERE [FTN] = ?", (int(tool_num),))
                row = cursor.fetchone()
                if row:
                    comment = str(row[0] or "No Comment").strip()
                    if comment not in local_tool_data: local_tool_data[comment] = []
                    local_tool_data[comment].append(cfg['name'])
        except Exception:
            continue

    if local_tool_data:
        # Header warning in Red
        print(f"{NUM_CONFLICT} WARNING: TOOL {tool_num} ALREADY EXISTS {RESET}")
        
        is_red = tool_num in conflicts
        ftn_color = NUM_CONFLICT if is_red else HEAD_COLOR
        
        for comment, lines_found in local_tool_data.items():
            ftn_display = f"{SUB_COLOR}[{RESET}{ftn_color}{tool_num}{RESET}{SUB_COLOR}]{RESET}"
            print(f'  {ftn_display} {DESC_COLOR}"{comment}"{RESET}')
            
            line_tags = []
            for name in all_line_names:
                if name in lines_found:
                    tag = f"{SUB_COLOR}[{RESET}\033[31m{name:^7}\033[0m{SUB_COLOR}]{RESET}"
                else:
                    tag = f"\033[2;90m[{'-' + name + '-':^7}]\033[0m"
                line_tags.append(tag)
            print(f"{SUB_COLOR}    └─ {RESET}{' '.join(line_tags)}")
            
        print("\n" + f"{SUB_COLOR}—{RESET}" * 50)

        # MANUAL CONFIRM
        print(f"{BAR_COLOR}Overwrite these existing tools with NEW ADD?{RESET} (y/n): ", end="", flush=True)
        conf = readchar.readkey().lower()
        print() 

        if conf != 'y':
            print(f"\n{NUM_CONFLICT} ADD cancelled. {RESET}")
            readchar.readkey()
            return

    # Logic for specific categories
    gen_comment = ""
    dia_raw = "0"

    if tool_cat == "Endmills":
        # Sub-branch for Endmill types
        em_type = app.get_menu_choice({
            "Square Endmill": "SQ",
            "Bull Endmill": "BULL",
            "Ball Endmill": "BALL",
            "Chamfer Mill": "CHAMF"
        }, "Select Endmill Type")
                
        dia_raw = app.prompt("Attributes", "Nominal Diameter")
        dia = dia_raw

        flutes = app.get_menu_choice({f"{i} FL": f"{i}FL" for i in range(2, 13)}, "Flute Count")

        roughfinish = app.get_menu_choice({"NONE":"", "ROUGH":"RGH", "FINISH":"FIN"}, "Cutter Purpose")
        roughfinish_str = f" {roughfinish}" if roughfinish and roughfinish != "NONE" else ""
                
        # --- Specific Attribute Logic ---
        rad_str = ""
        angle_str = ""
                
        if em_type == "BULL":
            rad = app.prompt("Attributes", "Corner Radius")
            rad_str = f"{rad}RAD " if rad else ""
                
        if em_type == "CHAMF":
            angle = app.prompt("Attributes", "Angle (e.g. 45, 60)")
            angle_str = f"{angle}DEG " if angle else ""

        coat = app.get_menu_choice({"NONE":"", "TIN":"TIN", "TICN":"TICN", "TIAIN":"TIAIN", "ALTIN":"ALTIN", "ALCRN":"ALCRN"}, "Coating")
        coat_str = f" {coat} COATED" if coat and coat != "NONE" else ""
                
        loc = app.prompt("Attributes", "L.O.C (Empty if none)")
        loc_str = f"{loc} LOC " if loc else ""
        relief = app.prompt("Attributes", "Relief Length (Empty if none)")
        relief_str = f" W/{relief} REL" if relief else ""
        fh = app.prompt("Attributes", "Length From Holder (FH)")
        holder = app.get_menu_choice({h: h for h in HOLDER_LIST}, "Holder Style")
        item_num = app.prompt("Attributes", "Item #")
                
        # --- Comment Construction ---
        # Example: 1/2 4FL .030RAD BULL EM TIN COATED 1.25 LOC X 1.5 FH...
        # Example: 1/4 2FL 45° CHAMFER EM ALTIN COATED...
        type_label = f"{em_type}{roughfinish_str} EM" if tool_cat == "Endmills" else f"{em_type} INSERTED"
        gen_comment = f"{dia} {flutes} {rad_str}{loc_str}{angle_str}{type_label}{coat_str}{relief_str} X {fh} FH IN {holder} #{item_num}"

    elif tool_cat == "Inserted Tooling":
        # First, ask what this actually is
        special_type = app.prompt("Attributes", "Tool Type (e.g. 45 DEG FACEMILL, INSERTED DRILL, PLUNGEMILL)")
        type_str = special_type.upper() if special_type else "INSERTED TOOL"
        
        dia_raw = app.prompt("Attributes", "Nominal Diameter")
        dia = dia_raw
        
        # Manual flute input for high-density specials
        flutes_raw = app.prompt("Attributes", "Flute Count")
        flutes_str = f"{flutes_raw}FL " if flutes_raw else ""
        
        fh = app.prompt("Attributes", "Length From Holder (FH)")
        holder = app.get_menu_choice({h: h for h in HOLDER_LIST}, "Holder Style")
        item_num = app.prompt("Attributes", "Item #")
        
        # Result: .750 2FL CHAMFER MILL X 1.25 FH IN 3IN GL SHRINK HOLDER #9999
        gen_comment = f"{dia} {flutes_str}{type_str} X {fh} FH IN {holder} #{item_num}"

    # GROUP: Drills (Includes xD Length)
    elif tool_cat == "Drills":
        dia_raw = app.prompt("Attributes", "Nominal Diameter")
        dia = dia_raw
        xd_len = app.prompt("Attributes", "Drill Length (e.g. 3, 5, 7 for xD)")
        xd_str = f"{xd_len}XD " if xd_len else ""
        mat = app.get_menu_choice({"Carbide": "CARB", "Cobalt": "COBALT", "HSS": "HSS"}, "Material")
        cooling = app.get_menu_choice({"None": "", "THRU COOLANT": " THRU COOL"}, "COOLING")
        fh = app.prompt("Attributes", "Length From Holder (FH)")
        holder = app.get_menu_choice({h: h for h in HOLDER_LIST}, "Holder Style")
        item_num = app.prompt("Attributes", "Item #")
        
        gen_comment = f"{dia} {xd_str}{mat.upper()}{cooling} DRILL X {fh} FH IN {holder} #{item_num}"

    # GROUP: Spot & Center Drills
    elif tool_cat == "Spot & Center Drills":
        dia_raw = app.prompt("Attributes", "Nominal Diameter")
        dia = dia_raw
        mat = app.get_menu_choice({"Carbide": "CARB", "Cobalt": "COBALT", "HSS": "HSS"}, "Material")
        angle = app.prompt("Attributes", "Angle (e.g. 90, 120, 140)")
        angle_str = f"{angle}DEG " if angle else ""
        fh = app.prompt("Attributes", "Length From Holder (FH)")
        holder = app.get_menu_choice({h: h for h in HOLDER_LIST}, "Holder Style")
        item_num = app.prompt("Attributes", "Item #")
        
        # Result: 1/2 CARB 90° SPOT/CTR X 1.5 FH IN 3IN GL ER16 HOLDER #1234
        gen_comment = f"{dia} {mat.upper()} {angle_str}SPOT/CTR X {fh} FH IN {holder} #{item_num}"

    # GROUP: Boring Bars & Reamers
    elif tool_cat == "Boring Bars & Reamers":
        dia_raw = app.prompt("Attributes", "Nominal Diameter")
        dia = dia_raw
        mat = app.get_menu_choice({"Carbide": "CARB", "Cobalt": "COBALT", "HSS": "HSS"}, "Material")
        fh = app.prompt("Attributes", "Length From Holder (FH)")
        holder = app.get_menu_choice({h: h for h in HOLDER_LIST}, "Holder Style")
        item_num = app.prompt("Attributes", "Item #")
        
        # Result: .250 CARB BAR/REAM X 2.0 FH IN 4IN GL HYD HOLDER #5678
        gen_comment = f"{dia} {mat.upper()} BAR/REAM X {fh} FH IN {holder} #{item_num}"
    # GROUP: Taps
    elif tool_cat == "Taps":
        t_type = app.get_menu_choice({"Standard": "STD", "STI": "STI", "Locking": "LOCKING"}, "Thread Type")
        t_style = app.get_menu_choice({"Hi-Spiral": "HI-SPIRAL CUT", "Form": "FORM TAP", "Cut": "CUT TAP"}, "Tap Style")
        dia = app.prompt("Attributes", "Tap Size (e.g. 1/4-20 or M6x1.0)")
        item_num = app.prompt("Attributes", "Item #")
        
        # Only include the type if it's special (STI or LOCKING)
        type_str = f"{t_type} " if t_type != "STD" else ""
        
        # Result: "1/4-20 HI-SPIRAL CUT (STD) #1234" 
        # OR:     "1/4-20 STI HI-SPIRAL CUT (STD) #1234"
        gen_comment = f"{dia} {type_str}{t_style} #{item_num}"
    # GROUP: Woodruff Cutters
    elif tool_cat == "Woodruff Cutters":
        dia_raw = app.prompt("Attributes", "Nominal Diameter")
        dia = dia_raw
        width = app.prompt("Attributes", "Cut Width")
        
        # Changed to manual input for high flute counts
        flutes_raw = app.prompt("Attributes", "Flute Count (e.g. 12, 18, 24)")
        flutes_str = f"{flutes_raw}FL " if flutes_raw else ""
        
        rad = app.prompt("Attributes", "Radius (Empty for Sq)")
        rad_str = f"{rad}RAD " if rad else ""
        
        coat = app.get_menu_choice({"NONE":"", "TIN":"TIN", "TICN":"TICN", "TIAIN":"TIAIN", "ALTIN":"ALTIN", "ALCRN":"ALCRN"}, "Coating")
        coat_str = f"{coat} COATED " if coat and coat != "NONE" else ""
        
        neck = app.prompt("Attributes", "Neck Length")
        fh = app.prompt("Attributes", "Length From Holder (FH)")
        holder = app.get_menu_choice({h: h for h in HOLDER_LIST}, "Holder Style")
        item_num = app.prompt("Attributes", "Item #")
        
        # Result: 1.0DIA X .125WIDTH 18FL .015RAD WOODRUFF TIN COATED .500 NECK X 1.5 FH IN 3IN GL SHRINK HOLDER #1234
        gen_comment = f"{dia}DIA X {width}WIDTH {flutes_str}{rad_str}WOODRUFF {coat_str}{neck} NECK X {fh} FH IN {holder} #{item_num}"

    # GROUP: Thread Mills
    elif tool_cat == "Thread Mills":
        dia_raw = app.prompt("Attributes", "Nominal Diameter")
        dia = dia_raw
        pitch = app.prompt("Attributes", "Pitch (TPI or mm)")
        fl_str = app.get_menu_choice({f"{i} FL": f"{i}FL" for i in range(2, 11)}, "Flute Count")
        coat = app.get_menu_choice({"NONE":"", "TIN":"TIN", "TICN":"TICN", "TIAIN":"TIAIN", "ALTIN":"ALTIN", "ALCRN":"ALCRN"}, "Coating")
        coat_str = f"{coat} COATED " if coat and coat != "NONE" else ""
        # --- New Thread Point Logic ---
        pt_raw = app.prompt("Attributes", "Number of Thread Points (1 for single, or enter count)")
        if pt_raw == "1":
            pt_str = "SINGLE POINT "
        elif pt_raw.isdigit() and int(pt_raw) > 1:
            pt_str = f"{pt_raw}X POINT "
        else:
            pt_str = "" # Fallback if empty
        neck = app.prompt("Attributes", "Neck Length")
        fh = app.prompt("Attributes", "Length From Holder (FH)")
        holder = app.get_menu_choice({h: h for h in HOLDER_LIST}, "Holder Style")
        item_num = app.prompt("Attributes", "Item #")
        
        # Result Example: .500 20 TPI 4FL 3X POINTS TM TIN COATED .750 NECK X 1.5 FH IN 3IN GL ER16 HOLDER #1234
        gen_comment = f"{dia} {pitch} PITCH {fl_str} {pt_str}Thread Mill {coat_str}{neck} NECK X {fh} FH IN {holder} #{item_num}"

    # GROUP: Special Tools
    elif tool_cat == "Special Tools":
        # First, ask what this actually is
        special_type = app.prompt("Attributes", "Tool Type (e.g. LOLLIPOP MILL, COUNTERSINK)")
        type_str = special_type.upper() if special_type else "SPECIAL TOOL"
        
        dia_raw = app.prompt("Attributes", "Nominal Diameter")
        dia = dia_raw
        
        # Manual flute input for high-density specials
        flutes_raw = app.prompt("Attributes", "Flute Count")
        flutes_str = f"{flutes_raw}FL " if flutes_raw else ""
        
        fh = app.prompt("Attributes", "Length From Holder (FH)")
        holder = app.get_menu_choice({h: h for h in HOLDER_LIST}, "Holder Style")
        item_num = app.prompt("Attributes", "Item #")
        
        # Result: .750 2FL CHAMFER MILL X 1.25 FH IN 3IN GL SHRINK HOLDER #9999
        gen_comment = f"{dia} {flutes_str}{type_str} X {fh} FH IN {holder} #{item_num}"

    # Finalize ADD
    app.clear("Review Comment")
    print(f"Edit comment:")
    keyboard.write(gen_comment) 
    final_comment = input("> ").strip() or gen_comment

    if tool_cat == "Drills": dia_raw = "0"

    fields = {
        "Comment": final_comment,
        "Kind": app.get_menu_choice(TOOL_KINDS, "Tool Kind (XML Code)"),
        "Type": app.get_menu_choice(TOOL_TYPES, "Tool Type (XML Code)"),
        "StdDiameter": get_std_dia(dia_raw) or 0.0,
        "TlType": app.get_menu_choice(LIFE_TYPES, "Life Management"),
        "Life": int(app.prompt("Life", "Enter Life Value", "0"))
    }
    fields["LifeWarning"] = max(0.0, fields["Life"] - 10)

    if tool_cat == "Drills":
        fields["MaxDiameter"], fields["MinDiameter"] = 0.0, 0.0
    else:
        fields["MaxDiameter"] = round(fields["StdDiameter"] + 0.1, 4)
        fields["MinDiameter"] = round(max(0.0, fields["StdDiameter"] - 0.1), 4)
    

        # --- MANUAL CONFIRM ---
    # --- MANUAL CONFIRM FOR ADD ---
    print("\n" + f"{SUB_COLOR}—{RESET}" * 50)
    print(f"{BAR_COLOR}Proceed with {HEAD_COLOR}ADD{RESET} for {HEAD_COLOR}{tool_num}{RESET}? (y/n): ", end="", flush=True)
    
    conf = readchar.readkey().lower()
    print()  # Pushes the deployment status ([OK] lines) to a new line

    if conf == 'y':
        # Broadcast the new tool to all lines
        save_and_generate("ADD", tool_num, fields)
        print(f"\n{BAR_COLOR}Operation Complete. Press any key...{RESET}")
    else:
        print(f"\n{NUM_CONFLICT} ADD aborted. {RESET}")
    
    readchar.readkey()

def update(app):
    raw_num = app.prompt("Identification", "Enter Tool Number")
    if not raw_num.isdigit() or len(raw_num) > 8:
        print(f"\n{NUM_CONFLICT} Error: Numeric Tool Number required (max 8 digits). {RESET}")
        readchar.readkey(); return
            
    tool_num = raw_num.zfill(8)
    app.clear("Update Confirmation")
    
    all_line_names = [cfg['name'] for cfg in LINE_CONFIGS]
    conflicts = get_conflict_set()
    local_tool_data = {} 

    # --- Live Scan Logic ---
    for cfg in LINE_CONFIGS:
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg['ip']},1433;DATABASE={cfg['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=1;")
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT [FTNComment] FROM [dbo].[FunctionalToolData] WHERE [FTN] = ?", (int(tool_num),))
                row = cursor.fetchone()
                if row:
                    comment = str(row[0] or "No Comment").strip()
                    if comment not in local_tool_data: local_tool_data[comment] = []
                    local_tool_data[comment].append(cfg['name'])
        except Exception:
            continue

    if local_tool_data:
        is_red = tool_num in conflicts
        ftn_color = NUM_CONFLICT if is_red else HEAD_COLOR
        
        for comment, lines_found in local_tool_data.items():
            ftn_display = f"{SUB_COLOR}[{RESET}{ftn_color}{tool_num}{RESET}{SUB_COLOR}]{RESET}"
            print(f'  {ftn_display} {DESC_COLOR}"{comment}"{RESET}')
            
            line_tags = []
            for name in all_line_names:
                if name in lines_found:
                    # Target lines are RED
                    tag = f"{SUB_COLOR}[{RESET}\033[31m{name:^7}\033[0m{SUB_COLOR}]{RESET}"
                else:
                    # Inactive lines are DARK GRAY with dashes
                    tag = f"\033[2;90m[{'-' + name + '-':^7}]\033[0m"
                line_tags.append(tag)
            print(f"{SUB_COLOR}    └─ {RESET}{' '.join(line_tags)}")
    else:
        print(f"\n{BAR_COLOR}Note: Tool {tool_num} not found in live database scan.{RESET}")
    
    print("\n" + f"{SUB_COLOR}—{RESET}" * 50)
    
    # --- MANUAL CONFIRM ---
    print(f"{BAR_COLOR}Continue with {HEAD_COLOR}UPDATE{RESET} for {HEAD_COLOR}{tool_num}{RESET}? (y/n): ", end="", flush=True)
    conf = readchar.readkey().lower()
    
    if conf == 'y':
        run_update_feature(app, tool_num)
    else:
        print(f"\n{NUM_CONFLICT} Update cancelled. {RESET}")
        readchar.readkey()

def delete(app):
    raw_num = app.prompt("Identification", "Enter Tool Number")
    if not raw_num.isdigit() or len(raw_num) > 8:
        print(f"\n{NUM_CONFLICT} Error: Numeric Tool Number required (max 8 digits). {RESET}")
        readchar.readkey(); return
    
    tool_num = raw_num.zfill(8)
    app.clear("Delete Confirmation")
    
    all_line_names = [cfg['name'] for cfg in LINE_CONFIGS]
    conflicts = get_conflict_set()
    local_tool_data = {} 

    # --- Live Scan Logic ---
    for cfg in LINE_CONFIGS:
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg['ip']},1433;DATABASE={cfg['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=1;")
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT [FTNComment] FROM [dbo].[FunctionalToolData] WHERE [FTN] = ?", (int(tool_num),))
                row = cursor.fetchone()
                if row:
                    comment = str(row[0] or "No Comment").strip()
                    if comment not in local_tool_data: local_tool_data[comment] = []
                    local_tool_data[comment].append(cfg['name'])
        except Exception:
            continue

    if local_tool_data:
        is_red = tool_num in conflicts
        ftn_color = NUM_CONFLICT if is_red else HEAD_COLOR
        
        for comment, lines_found in local_tool_data.items():
            ftn_display = f"{SUB_COLOR}[{RESET}{ftn_color}{tool_num}{RESET}{SUB_COLOR}]{RESET}"
            print(f'  {ftn_display} {DESC_COLOR}"{comment}"{RESET}')
            
            line_tags = []
            for name in all_line_names:
                if name in lines_found:
                    tag = f"{SUB_COLOR}[{RESET}\033[31m{name:^7}\033[0m{SUB_COLOR}]{RESET}"
                else:
                    tag = f"\033[2;90m[{'-' + name + '-':^7}]\033[0m"
                line_tags.append(tag)
            print(f"{SUB_COLOR}    └─ {RESET}{' '.join(line_tags)}")
    else:
        print(f"\n{BAR_COLOR}Note: Tool {tool_num} not found in live database scan.{RESET}")
    
    print("\n" + f"{SUB_COLOR}—{RESET}" * 50)
    
    # --- MANUAL CONFIRM ---
    print(f"{NUM_CONFLICT} Confirm GLOBAL DELETE for {HEAD_COLOR}{tool_num}{RESET}? (y/n): ", end="", flush=True)
    conf = readchar.readkey().lower()
    print() # <--- CRITICAL: This pushes the next print to a new line

    if conf == 'y':
        # If your save_and_generate handles the broadcast, call it here
        # Assuming save_and_generate prints its own status lines
        save_and_generate("DELETE", tool_num, {}) 
        print(f"\n{BAR_COLOR}Operation Complete. Press any key...{RESET}")
    else:
        print(f"\n{NUM_CONFLICT} Delete aborted. {RESET}")
    
    readchar.readkey()

if __name__ == "__main__":
    try: 
        main()
    except KeyboardInterrupt: 
        print("\nExiting...")
        sys.exit()