import pyodbc
import os
import sys
import difflib
import re
import random
import readchar
import xml.etree.ElementTree as ET
from xml.dom import minidom
from collections import defaultdict
from collections import Counter
from settings import cfg

DB_CREDS = cfg.db_creds
LINE_CONFIGS = cfg.line_configs


class SyncApp:
    def __init__(self):
        self.current_tool = ""
        self.remaining = 0
        self.total = 0
        self.highlight_enabled = True  # Default to ON
        self.random_order_enabled = False  # default OFF

    def header(self, title=""):
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\033[1;35m--- MAS-A5 DESCRIPTION STANDARDIZATION TOOL ---\033[0m")
        # Updated header to show current progress vs total
        progress = self.total - self.remaining + 1
        print(f"\033[1;33mTOOL: {self.current_tool} \033[1;37m| \033[1;32mPROGRESS: {progress}/{self.total}\033[0m")
        print("\033[1;35m" + "—" * 55 + "\033[0m")
        if title:
            print(f"\033[1;97m[ {title.upper()} ]\033[0m\n")

    def get_menu_choice(self, options, title, initial_idx=0):
        keys = list(options.keys())
        idx = initial_idx
        num_options = len(keys)

        PREFIX_WIDTH = 4  # width of " > "

        # --- PRECOMPUTE STYLED OPTIONS (BIG SPEED BOOST) ---
        def get_desc_line(text):
            return text.split("\n")[0].strip()

        max_len = max(len(get_desc_line(k)) for k in keys)

        precomputed_blocks = []

        for name in keys:
            lines = name.split("\n")
            styled_lines = []

            for j, line in enumerate(lines):
                raw = line.lstrip()

                # Description line
                if j == 0 and raw.startswith('"'):
                    if raw.count('"') >= 2:
                        first = raw.find('"')
                        last = raw.rfind('"')

                        inner = raw[first+1:last].strip()

                        styled = (
                            "\033[90m\"\033[0m" +
                            f"\033[96m{inner}\033[0m" +
                            "\033[90m\"\033[0m"
                        )
                    else:
                        styled = f"\033[96m{raw.strip()}\033[0m"

                    styled_lines.append(styled)

                # Found on line
                elif "Found on:" in raw:
                    styled_lines.append(f"\033[90m{raw}\033[0m")

                else:
                    styled_lines.append(raw)

            precomputed_blocks.append(styled_lines)

        # --- INITIAL RENDER ---
        self.header(title)
        sys.stdout.write("\033[?25l")  # hide cursor

        try:
            while True:
                output_lines = []

                for i, block_lines in enumerate(precomputed_blocks):
                    # Prefix
                    prefix_selected = "\033[30;103m > \033[0m "
                    prefix_normal = " " * PREFIX_WIDTH
                    prefix = prefix_selected if i == idx else prefix_normal

                    # Copy block so we don't mutate original
                    rendered = block_lines[:]

                    # Apply prefix
                    rendered[0] = prefix + rendered[0]

                    # Align continuation lines
                    indent = " " * PREFIX_WIDTH
                    for k in range(1, len(rendered)):
                        rendered[k] = indent + rendered[k]

                    # Bold selected
                    if i == idx:
                        rendered = [f"\033[1m{l}\033[0m" for l in rendered]

                    output_lines.extend(rendered)

                # Print
                sys.stdout.write("\n".join(output_lines) + "\n")
                sys.stdout.flush()

                # --- INPUT ---
                key = readchar.readkey()

                if key == readchar.key.UP:
                    idx = (idx - 1) % num_options
                elif key == readchar.key.DOWN:
                    idx = (idx + 1) % num_options
                elif key == readchar.key.ENTER:
                    return options[keys[idx]]

                # --- MOVE CURSOR BACK UP (NO CLEAR = FAST) ---
                sys.stdout.write(f"\033[{len(output_lines)}F")

        finally:
            sys.stdout.write("\033[?25h")  # show cursor

def parse_to_float(value_str):
    """Converts fractions (1/4) or decimals (0.25) to float."""
    try:
        if '/' in value_str:
            num, den = value_str.split('/')
            return float(num) / float(den)
        return float(value_str)
    except (ValueError, ZeroDivisionError):
        return 0.0

def score_description(text):
    """
    Advanced scoring for CNC Tooling Descriptions.
    Prioritizes: Physical Safety (Reach) > Part Numbers > Brand > Technical Spec.
    Penalizes: Line-specific notes and temporary job routing.
    """
    if not text: return -1
    score = 0
    
    # 1. NORMALIZE (Case-insensitive, unify units and common shop shorthand)
    t = text.lower()
    t = t.replace('"', ' inch').replace("'", ' degree')
    t = re.sub(r'\bf\.?h\.?\b|\bfrom holder\b|\booh\b|\bout of holder\b', 'fh', t)
    t = re.sub(r'\bext\.\b|\bextension\b', 'ext', t)
    
    # 2. THE SAFETY CLEARANCE ENGINE (The most important data)
    # Regex captures: .125 FH, 1.500 REACH, 2.5 FROM ER16, 1.15-MIN FH
    num_val = r'(\d+/\d+|\d*\.?\d+)'
    reach_pattern = rf'{num_val}\s*(?:inch|in|mm|")?\s*(?:fh|rel|reach|loc|ooh|min|stickout|protrusion)'
    from_pattern = rf'{num_val}\s*(?:inch|in|mm|")?\s*(?:from|off)'
    
    reach_matches = re.findall(reach_pattern, t)
    from_matches = re.findall(from_pattern, t)
    
    all_lengths = [parse_to_float(v) for v in (reach_matches + from_matches)]
    
    if all_lengths:
        # We value the description that provides the largest/safest clearance value
        max_val = max(all_lengths)
        # Convert metric to inch for scoring consistency if needed
        if 'mm' in t and max_val > 5:
            max_val /= 25.4
        # High base score (80) + dynamic reach weight
        score += 80 + (max_val * 65)

    # 3. TECHNICAL SPECIFICATION WEIGHTING
    # These bonuses ensure specific tool geometry is prioritized
    spec_patterns = {
        r'\bitem\s*#?\s*\d+|\b#\d{4,}\b': 70,  # Specific Item/Catalog numbers (Gold standard)
        r'\b\d+\s*f(l|lute)': 35,              # Flute count
        r'\d+deg|\d+\s*degree': 40,            # Angles/Chamfers
        r'rad|\.\d+r\b|\bradius\b': 50,        # Corner Radii
        r'd[5-9]\b|h[1-6]\b|6h\b': 45,         # Thread limits (H6, D7, etc.)
        r'pitch|\d+\s*tpi': 45,                # Thread mill pitch
        r'thru\s?cool': 40,                    # Coolant delivery
        r'ball\b|b\.?e\.?m\.?': 30,            # Geometry type
        r'm\d+\s?x\s?[\d\.]+': 40              # Metric thread callouts (M8 x 1.25)
    }
    
    for pattern, bonus in spec_patterns.items():
        if re.search(pattern, t):
            score += bonus

    # 4. BRAND RECOGNITION (Trusted Catalog Data)
    brands = {
        'harvey': 40, 'osg': 35, 'iscar': 35, 'carmex': 35, 'seco': 30, 
        'msc': 25, 'robb jack': 30, 'scientific': 25, 'sct': 25, 'gühring': 30, 
        'guhring': 30, 'nachi': 25, 'mitsubishi': 25, 'kennametal': 30
    }
    for brand, bonus in brands.items():
        if brand in t:
            score += bonus

    # 5. HOLDER & EXTENSION CONTEXT
    # Knowing the collet or extension size is vital for shop floor verification
    setup_patterns = {
        r'er-?11': 30, r'er-?16': 30, r'er-?32': 30, 
        r'shrink': 35, r'hydraulic': 35, r'stub': 15,
        r'long': 20, r'extra long': 25, r'skinny': 20
    }
    for pattern, bonus in setup_patterns.items():
        if re.search(pattern, t):
            score += bonus

    # 6. PENALIZE NOISE (Temporary or Local Data)
    # We want to subtract points for data that won't make sense on a different line
    noise_filters = {
        r'\[line\d+\]': -100,      # Specific line tags in brackets
        r'\bline\s?\d+': -50,      # "Line 2"
        r'\bjob\b': -40,           # Job numbers
        r'\bop\d+\b': -30,         # Op 10, Op 20
        r'kit\b': -20,             # "In kit"
        r'talon|cargo|frame': -15, # Part-specific notes
        r'grind|grind off': -10    # Modification notes (sometimes too specific)
    }
    for pattern, penalty in noise_filters.items():
        if re.search(pattern, t):
            score += penalty

    # 7. INFORMATION DENSITY (Tie-breaker)
    # Reward descriptions that use more professional terminology rather than short fragments
    word_count = len(t.split())
    if word_count > 3:
        score += word_count * 2

    return round(score, 2)

def highlight_diff(base, compare):
    sm = difflib.SequenceMatcher(None, base, compare)
    result = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        text = compare[j1:j2]
        if op == "equal":
            result.append(f"\033[38;5;51m{text}\033[0m") # Electric Cyan
        elif op == "replace":
            # Bright Red background for contrast
            result.append(f"\033[48;5;196m\033[38;5;231m{text}\033[0m") 
        elif op == "insert":
            # The "Bright Green" requested
            result.append(f"\033[38;5;46m{text}\033[0m")
    return "".join(result)

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

def broadcast_sync(tool_num, description, lines_to_update):
    """
    Sends XML updates to targeted lines, retrieving the 
    existing TlType for each line individually before sending.
    """
    for cfg in LINE_CONFIGS:
        if cfg['name'] in lines_to_update:
            # --- Per-Line TlType Lookup ---
            current_tl_type = get_line_specific_tl_type(tool_num, cfg)
            
            # --- XML Generation for THIS specific line ---
            root = ET.Element("MASData")
            tools = ET.SubElement(root, "FunctionalTools")
            f_tool = ET.SubElement(tools, "FunctionalTool", {"action": "UPDATE", "number": tool_num})
            ET.SubElement(f_tool, "Comment").text = description
            
            cutter = ET.SubElement(f_tool, "Cutter", {"number": "1"})
            ET.SubElement(cutter, "TlType").text = str(current_tl_type)
            
            xml_str = ET.tostring(root, encoding='utf-8')
            pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
            pretty = "\n".join([l for l in pretty.split('\n') if l.strip()])
            
            # --- Deployment ---
            filename = f"SYNC_{tool_num}.xml"
            try:
                if not os.path.exists(cfg['path']):
                    print(f"  \033[91m[PATH ERR]\033[0m {cfg['name']} unreachable.")
                    continue
                
                with open(os.path.join(cfg['path'], filename), "w", encoding="utf-8") as f:
                    f.write(pretty)
                
                print(f"  \033[92m[SENT]\033[0m {cfg['name']}")
            except Exception as e:
                print(f"  \033[91m[ERR]\033[0m {cfg['name']}: {e}")

def get_consensus_data(comments):
    """Identifies the most frequent Item # and Flute count in a group."""
    items = []
    flutes = []
    for c in comments:
        c_low = c.lower()
        # Find Item numbers
        item_match = re.search(r'item\s?#?\s?(\d+)|#\s?(\d{3,})', c_low)
        if item_match:
            items.append(item_match.group(1) or item_match.group(2))
        # Find Flute counts
        flute_match = re.search(r'(\d+)\s?fl', c_low)
        if flute_match:
            flutes.append(flute_match.group(1))
            
    # Return the most common, or None if no data exists
    top_item = Counter(items).most_common(1) if items else None
    top_flute = Counter(flutes).most_common(1) if flutes else None
    return top_item, top_flute

def confirm_action(prompt="Are you sure? (y/n): "):
    while True:
        print(f"\n\033[1;33m{prompt}\033[0m", end="", flush=True)
        key = readchar.readkey().lower()

        if key == 'y':
            print(" y")
            return True
        elif key == 'n':
            print(" n")
            return False

def setup_prompt(app):
    options = ["sorted", "random"]
    idx = 0

    print("\n\033[1;35m--- SELECT ORDER MODE ---\033[0m")
    print("Use ↑ ↓ and press ENTER\n")

    sys.stdout.write("\033[?25l")  # hide cursor

    try:
        while True:
            output_lines = []

            for i, opt in enumerate(options):
                prefix = "\033[30;103m > \033[0m " if i == idx else "     "

                if opt == "sorted":
                    line = f"{prefix}\033[96mSorted Order\033[0m"
                else:
                    line = f"{prefix}\033[96mRandom Order\033[0m"

                if i == idx:
                    line = f"\033[1m{line}\033[0m"

                output_lines.append(line)

            # draw
            sys.stdout.write("\n".join(output_lines) + "\n")
            sys.stdout.flush()

            key = readchar.readkey()

            if key == readchar.key.UP:
                idx = (idx - 1) % len(options)

            elif key == readchar.key.DOWN:
                idx = (idx + 1) % len(options)

            elif key == readchar.key.ENTER:
                app.random_order_enabled = (options[idx] == "random")
                return

            sys.stdout.write(f"\033[{len(output_lines)}A")  # move up
            for _ in range(len(output_lines)):
                sys.stdout.write("\033[2K")  # clear entire line
                sys.stdout.write("\n")
            sys.stdout.write(f"\033[{len(output_lines)}A")

    finally:
        sys.stdout.write("\033[?25h")  # show cursor

def main():
    import random

    app = SyncApp()
    master_map = defaultdict(lambda: defaultdict(list))
    original_map = defaultdict(dict)

    app.header("Starting System Check")
    print("\033[1;34mScanning all production lines for description conflicts...\033[0m\n")

    # --- SCAN ---
    for cfg in LINE_CONFIGS:
        try:
            conn_str = (
                f"DRIVER={{SQL Server}};"
                f"SERVER={cfg['ip']},1433;"
                f"DATABASE={cfg['db']};"
                f"UID={DB_CREDS['uid']};"
                f"PWD={DB_CREDS['pwd']};"
                f"Connection Timeout=1;"
            )

            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT [FTN], [FTNComment] FROM [dbo].[FunctionalToolData]")

                for row in cursor:
                    ftn = str(row[0]).zfill(8)
                    comment = (row[1] or "").strip()

                    if not comment:
                        continue

                    master_map[ftn][comment].append(cfg['name'])
                    original_map[ftn][cfg['name']] = comment

            print(f"  \033[92m[ONLINE]\033[0m {cfg['name']}")

        except Exception as e:
            print(f"  \033[91m[OFFLINE]\033[0m {cfg['name']} ({e})")

    # --- BUILD CONFLICT LIST (NO ORDER YET) ---
    conflicts_list = [
        ftn for ftn, descs in master_map.items() if len(descs) > 1
    ]

    app.total = len(conflicts_list)
    app.remaining = app.total

    if app.total == 0:
        print("\n\033[92mSuccess: All lines are perfectly synchronized.\033[0m")
        return

    print(f"\n\033[1;33mFound {app.remaining} tools with mismatched comments.\033[0m")

    setup_prompt(app)

    # --- APPLY ORDER BASED ON USER CHOICE ---
    if app.random_order_enabled:
        random.shuffle(conflicts_list)
    else:
        conflicts_list.sort()

    idx = 0
    history = {}

    # --- MAIN LOOP ---
    while idx < app.total:
        ftn = conflicts_list[idx]
        descs = master_map[ftn]

        app.current_tool = ftn
        app.remaining = app.total - idx

        all_comments = list(descs.keys())
        active_lines = sorted({
            line for lines in descs.values() for line in lines
        })

        # --- CONSENSUS DATA ---
        item_nums = []
        flute_counts = []

        for c in all_comments:
            c_low = c.lower()

            i_match = re.search(r'item\s?#?\s?(\d+)|#\s?(\d{4,})', c_low)
            if i_match:
                item_nums.append(i_match.group(1) or i_match.group(2))

            f_match = re.search(r'(\d+)\s?fl', c_low)
            if f_match:
                flute_counts.append(f_match.group(1))

        top_item = Counter(item_nums).most_common(1) if item_nums else None
        top_flute = Counter(flute_counts).most_common(1) if flute_counts else None

        # --- BUILD OPTIONS ---
        options_list = []

        for comment, lines in descs.items():
            score = score_description(comment)

            if "5axis" in lines:
                score += 100

            c_low = comment.lower()

            if top_item:
                item_val = top_item[0][0]
                if item_val in c_low:
                    score += 60
                else:
                    score -= 100

            if top_flute:
                flute_val = top_flute[0][0]
                if f"{flute_val}fl" in c_low.replace(" ", ""):
                    score += 30

            options_list.append({
                "value": comment,
                "lines": lines,
                "score": score
            })

        # --- SORT OPTIONS ---
        options_list.sort(key=lambda x: x["score"], reverse=True)
        base_desc = options_list[0]["value"]

        # --- MENU ---
        menu_dict = {}

        for opt in options_list:
            comment = opt["value"]
            lines = opt["lines"]
            score_val = opt["score"]

            line_tags = f"\033[90m[\033[0m \033[1;34m{' | '.join(lines)}\033[0m \033[90m]\033[0m"

            if not app.highlight_enabled or comment == base_desc:
                display = f"\033[38;5;51m{comment}\033[0m"
            else:
                display = highlight_diff(base_desc, comment)

            label = f"\"{display}\"\n      └─ Found on: {line_tags} \033[2;31m(Score: {score_val})\033[0m"
            menu_dict[label] = comment

        # --- NAVIGATION OPTIONS ---
        if idx > 0:
            menu_dict["\033[1;97m[ << GO BACK (UNDO) ]\033[0m"] = "__BACK__"

        menu_dict["\033[1;97m[ MANUAL OVERRIDE ]\033[0m"] = "__MANUAL__"

        status_text = "\033[38;5;46mON\033[0m" if app.highlight_enabled else "\033[1;31mOFF\033[0m"
        menu_dict[f"\033[1;97m[ TOGGLE HIGHLIGHTS: {status_text} ]\033[0m"] = "__TOGGLE__"

        menu_dict["\033[1;97m[ SKIP THIS TOOL ]\033[0m"] = "__SKIP__"

        choice = app.get_menu_choice(
            menu_dict,
            f"Select the correct description for {ftn}"
        )

        # --- ACTION HANDLING ---
        if choice == "__TOGGLE__":
            app.highlight_enabled = not app.highlight_enabled
            continue
        if choice == "__BACK__":
            prev_idx = max(0, idx - 1)

            if prev_idx in history:
                last = history.pop(prev_idx)
                print(f"\033[90mReverting {last['ftn']}...\033[0m")

                for line, orig_desc in last["originals"].items():
                    broadcast_sync(last["ftn"], orig_desc, [line])
            else:
                print("\033[90mNothing to undo for this step.\033[0m")

            idx = prev_idx
            continue

        if choice == "__SKIP__":
            idx += 1
            continue

        if choice == "__MANUAL__":
            print("\033[1;32m-> MANUAL OVERRIDE MODE\033[0m")
            new_desc = input("   Enter new standard description: ").strip()
        else:
            new_desc = choice

        if not new_desc:
            continue

        print("\n\033[96mSelected Description:\033[0m")
        print(f"\"{new_desc}\"")

        if not confirm_action("Apply this description to all lines? (y/n): "):
            continue

        # --- APPLY ---
        print(f"\n\033[90mPushing to {len(active_lines)} lines...\033[0m")

        history[idx] = {
            "ftn": ftn,
            "originals": {line: original_map[ftn][line] for line in active_lines}
        }

        broadcast_sync(ftn, new_desc, active_lines)

        print("\n\033[92mUpdate Complete.\033[0m Press any key...")
        readchar.readkey()

        idx += 1

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit()