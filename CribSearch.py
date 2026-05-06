import json
import os
import re
import sys
from turtle import title
import readchar
import shutil
from readchar import key as rc_key

from MLTE import *
from settings import cfg

C_HDR, C_ITEM, C_DESC, C_ALIAS, C_RESET = "\033[1;36m", "\033[1;33m", "\033[1;37m", "\033[1;32m", "\033[0m"
C_DEBUG = "\033[1;31m" # Red for debug visibility

# -------------------------------
# EXTENSIVE SYNONYM SYSTEM
# -------------------------------
TOOL_CRIB_SEARCH_ALIAS_LIST = cfg.toolCribSearchAliasList


GAUGE_CONSTANTS = {
    # Wire Gauges
    "80": 0.0135, "79": 0.0145, "78": 0.0160, "77": 0.0180, "76": 0.0200,
    "75": 0.0210, "74": 0.0225, "73": 0.0240, "72": 0.0250, "71": 0.0260,
    "70": 0.0280, "69": 0.0292, "68": 0.0310, "67": 0.0320, "66": 0.0330,
    "65": 0.0350, "64": 0.0360, "63": 0.0370, "62": 0.0380, "61": 0.0390,
    "60": 0.0400, "59": 0.0410, "58": 0.0420, "57": 0.0430, "56": 0.0465,
    "55": 0.0520, "54": 0.0550, "53": 0.0595, "52": 0.0635, "51": 0.0670,
    "50": 0.0700, "49": 0.0730, "48": 0.0760, "47": 0.0785, "46": 0.0810,
    "45": 0.0820, "44": 0.0860, "43": 0.0890, "42": 0.0935, "41": 0.0960,
    "40": 0.0980, "39": 0.0995, "38": 0.1015, "37": 0.1040, "36": 0.1065,
    "35": 0.1100, "34": 0.1110, "33": 0.1130, "32": 0.1160, "31": 0.1200,
    "30": 0.1285, "29": 0.1360, "28": 0.1405, "27": 0.1440, "26": 0.1470,
    "25": 0.1495, "24": 0.1520, "23": 0.1540, "22": 0.1570, "21": 0.1590,
    "20": 0.1610, "19": 0.1660, "18": 0.1695, "17": 0.1730, "16": 0.1770,
    "15": 0.1800, "14": 0.1820, "13": 0.1850, "12": 0.1890, "11": 0.1910,
    "10": 0.1935, "9": 0.1960, "8": 0.1990, "7": 0.2010, "6": 0.2040,
    "5": 0.2055, "4": 0.2090, "3": 0.2130, "2": 0.2210, "1": 0.2280,

    # Letter Gauges
    "A": 0.2340, "B": 0.2380, "C": 0.2420, "D": 0.2460, "E": 0.2500, "F": 0.2570,
    "G": 0.2610, "H": 0.2660, "I": 0.2720, "J": 0.2770, "K": 0.2810, "L": 0.2900,
    "M": 0.2950, "N": 0.3020, "O": 0.3160, "P": 0.3230, "Q": 0.3320, "R": 0.3390,
    "S": 0.3480, "T": 0.3580, "U": 0.3680, "V": 0.3770, "W": 0.3860, "X": 0.3970,
    "Y": 0.4040, "Z": 0.4130,
}

class ToolSearcher:
    def __init__(self, main_db_path, shadow_db_path=None):
        self.db_path = main_db_path
        self.shadow_db_path = shadow_db_path
        
        # 1. Load raw sources
        self.raw_main_data = self._load_db() # Your existing list of dicts
        self.shadow_data = {}
        
        if self.shadow_db_path and os.path.exists(self.shadow_db_path):
            try:
                with open(self.shadow_db_path, 'r') as f:
                    self.shadow_data = json.load(f)
            except Exception as e:
                print(f"Error loading shadow database: {e}")

        # 2. CREATE THE SEARCHABLE MASTER DB
        self.data = self._create_searchable_db()

        # 3. State
        self.history = []
        self.results = []
        self.results_stack = []
        self.page = 0
        self.page_size = 15

    def clear(self, title=""):
        os.system('cls' if os.name == 'nt' else 'clear')
        if hasattr(self, 'history') and self.history:
            # Yellow Breadcrumb Bar
            print(f"\033[1;33m{' > '.join(self.history)}\033[0m")
            print("\033[1;33m" + "—" * 85 + "\033[0m")
        else:
            print("\033[1;34m--- TOOL SEARCHER V3 ---\033[0m\n")
        
        if title:
            print(f"\033[1;36m[ {title.upper()} ]\033[0m\n")

    def get_menu_choice(self, options, title):
        keys = list(options.keys())
        idx = 0
        self.clear(title)
        sys.stdout.write("\033[?25l") # Hide cursor
        
        try:
            while True:
                sys.stdout.write("\033[J") # Clear below
                output = []
                for i, name in enumerate(keys):
                    if i == idx:
                        output.append(f"  \033[1;97;42m > {name} \033[0m")
                    else:
                        output.append(f"    {name}")
                
                sys.stdout.write("\n".join(output) + "\n")
                sys.stdout.flush()

                key = readchar.readkey()
                if key == readchar.key.UP:
                    idx = (idx - 1) % len(keys)
                elif key == readchar.key.DOWN:
                    idx = (idx + 1) % len(keys)
                elif key == readchar.key.ENTER:
                    choice_label = keys[idx]
                    if choice_label not in ["EXIT", "BACK"]:
                        self.history.append(choice_label[:15])
                    return options[choice_label]
                elif key in [readchar.key.ESC, readchar.key.BACKSPACE]:
                    return "BACK_REQ"
                
                sys.stdout.write(f"\033[{len(keys)}F") # Move cursor back up
        finally:
            sys.stdout.write("\033[?25h") # Show cursor

    def _create_searchable_db(self):
        merged_list = []
        
        
        for item in self.raw_main_data:
            # --- EXISTING BRIDGE LOGIC ---
            raw_val = item.get("itemAliasNumber", "")
            alias_str = str(raw_val).strip().split('.')[0]
            
            shadow_info = (
                self.shadow_data.get(alias_str) or 
                self.shadow_data.get(alias_str.zfill(8)) or
                self.shadow_data.get(alias_str.zfill(7))
            )
            
            s_desc, s_brand, s_specs_str, raw_specs = "", "", "", []

            if shadow_info:
                s_desc = str(shadow_info.get("description") or shadow_info.get("descr") or "").lower()
                s_brand = str(shadow_info.get("brand") or "").lower()
                raw_specs = shadow_info.get("specs", [])
                if isinstance(raw_specs, list):
                    s_specs_str = " ".join([
                        str(s[1].get("value", "")) if (isinstance(s, list) and len(s) > 1 and isinstance(s[1], dict))
                        else str(s) for s in raw_specs
                    ]).lower()

            # Inject pre-processed shadow fields
            item["shadow_desc"] = s_desc
            item["shadow_brand"] = s_brand
            item["shadow_specs"] = s_specs_str
            item["specs"] = raw_specs 

            # --- NEW: PRE-BUILD THE SEARCH BLOB ---
            # This is the "Master String" we will search against later
            item_desc_orig = str(item.get("descr", "")).lower()
            item["search_blob"] = " ".join([
                str(item.get("itemNumber", "")),
                alias_str,
                item_desc_orig,
                str(item.get("itemGroupDescr", "")).lower(),
                str(item.get("itemSubGroupDescr", "")).lower(),
                str(item.get("brand", "")).lower(),
                s_desc,
                s_brand,
                s_specs_str
            ]).lower()

            # --- NEW: PRE-EXTRACT SIZE ---
            # Instead of regexing sizes during every search, do it once here
            item["clean_size"] = self.extract_size(item_desc_orig)

            merged_list.append(item)
    
        return merged_list


    def _load_db(self):
        if not os.path.exists(self.db_path): return []
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []

    def clear(self, title=""):
        os.system('cls' if os.name == 'nt' else 'clear')
        if self.history:
            # Joins all search terms with a ' > ' separator
            breadcrumb = " > ".join(str(h).upper() for h in self.history)
            print(f"\033[1;33mSEARCH PATH: {breadcrumb}\033[0m")
            print("\033[1;33m" + "—" * 80 + "\033[0m")
        else:
            print("\033[1;34m--- TOOL CRIB SEARCH SYSTEM ---\033[0m\n")
        
        if title:
            print(f"\033[1;36m[ {title.upper()} ]\033[0m\n")

    def parse_size(self, text):
        if not text: return None
        try:
            # Clean string: handle European commas and remove gauge prefixes (#, No.)
            s = text.lower().strip().replace(',', '.')
            s = re.sub(r'(no\.|#|num|gauge)\s*', '', s)
            
            # 1. Lookup Gauges/Letters first
            if s.upper() in GAUGE_CONSTANTS:
                return GAUGE_CONSTANTS[s.upper()]

            # 2. Mathematical Fraction Handling (e.g., 1/4 -> 0.25)
            if "/" in s:
                n, d = s.split("/")
                return float(n) / float(d)
            
            # 3. Mathematical Metric Handling (e.g., 5.5mm -> 0.2165)
            if "mm" in s or (s.endswith("m") and not s.endswith("em")):
                clean_val = s.replace("mm", "").replace("m", "").strip()
                return float(clean_val) / 25.4
            
            # 4. Standard Decimal (e.g., 0.5)
            val = float(s)
            
            # 5. Smart Metric Detection: 
            # If the value looks like a standard metric drill (e.g., 5.5, 6.75) 
            # but doesn't have 'mm', your search logic below will handle it via the +-0.005 check.
            return val
        except: 
            return None

    def extract_size(self, text):
        if not text: return None
        # 1. Standardize
        s = text.lower().strip().replace(',', '.')
        
        # 2. Split at 'X'. We use a regex split to catch '1/2X2' or '1/2 X 2'
        # This ensures 'head' is ONLY the first part (the diameter)
        parts = re.split(r'\s*x\s*', s)
        head = parts[0] if parts else s
    
        # 3. PRIORITY 1: Fractions (e.g., 1/2)
        # We look for a fraction anywhere in that first segment
        frac_match = re.search(r'(?<!-)\b(\d+/\d+)\b', head)
        if frac_match:
            try:
                n, d = frac_match.group(1).split('/')
                return float(n) / float(d)
            except: pass
    
        # 4. PRIORITY 2: Gauges/Letters (e.g., #3, No. 3, Letter E)
        gauge_match = re.search(r'(?:#|no\.|size|letter)\s*([a-z0-9]+)', head)
        if gauge_match:
            val = gauge_match.group(1).upper()
            if val in GAUGE_CONSTANTS:
                return GAUGE_CONSTANTS[val]
    
        # 5. PRIORITY 3: Metric (e.g., 3.1mm)
        metric_match = re.search(r'(\d*\.\d+|\d+)\s*mm', head)
        if metric_match:
            return float(metric_match.group(1)) / 25.4
    
        # 6. PRIORITY 4: Decimals (e.g., .5, 0.5, .122)
        # This regex looks for:
        # Option A: A dot followed by 1-4 digits (.5, .122)
        # Option B: A leading digit, then a dot, then 1-4 digits (0.5, 1.25)
        decimal_match = re.search(r'(\.\d{1,4})|(\d\.\d{1,4})', head)
        if decimal_match:
            # group(0) returns the full matched string (e.g., ".5")
            return float(decimal_match.group(0))
    
        return None

    def convert_fraction_to_decimal(self, frac_str):
        try:
            if '/' in frac_str:
                num, denom = frac_str.split('/')
                return float(num) / float(denom)
            return float(frac_str)
        except:
            return None


    def filtered_search(self, cat_name, diam_val, keywords, source_set=None, dynamic_regex=None):
        dataset = source_set if source_set is not None else self.data
        cat_name_std = str(cat_name).upper() 
        group_meta = next((g for g in TOOL_CRIB_SEARCH_ALIAS_LIST if g["name"].upper() == cat_name_std), None)
        
        # Pre-process search parameters once
        search_query_list = [k.lower() for k in keywords] if keywords else []
        compiled_dyn_reg = re.compile(dynamic_regex, re.IGNORECASE) if dynamic_regex else None
        radius_pattern = re.compile(r"(?:\d+\.?\d*|(?:\d+\s+)?\d+/\d+)\s?(?:cr|r|rad)\b")

        # Pre-compile group filters
        pe, we_regexes, wi_regexes, pi = [], [], [], []
        if group_meta:
            pe = [x.lower() for x in group_meta.get("part_exclude", [])]
            we_regexes = [re.compile(rf"\b{re.escape(x.lower())}\b") for x in group_meta.get("word_exclude", [])]
            wi_regexes = [re.compile(rf"\b{re.escape(x.lower())}\b") for x in group_meta.get("word_include", [])]
            pi = [x.lower() for x in group_meta.get("part_include", [])]

        results = []
        for item in dataset:
            combined = item["search_blob"] # <--- FAST ACCESS

        for item in dataset:
            # --- 1. ACCESS PRE-MERGED DATA ---
            # Note: items are now converted to string once
            desc_orig = str(item.get("descr", "")).lower()
            combined = " ".join([
                str(item.get("itemNumber", "")),
                str(item.get("itemAliasNumber", "")),
                desc_orig,
                str(item.get("itemGroupDescr", "")),
                str(item.get("itemSubGroupDescr", "")),
                str(item.get("brand", "")),
                item.get("shadow_desc", ""),
                item.get("shadow_brand", ""),
                item.get("shadow_specs", "")
            ]).lower()

            # --- 3. CATEGORY & GEOMETRY FILTERS ---
            if group_meta:
                match = False

                # A. Hard Excludes
                if any(x in combined for x in pe): continue
                if any(rx.search(combined) for rx in we_regexes): continue

                # B. Radius/Geometry Check
                has_radius = bool(radius_pattern.search(combined))

                if cat_name_std == "SQUARE ENDMILL" and has_radius:
                    continue
                
                # C. Include Logic
                if not wi_regexes and not pi:
                    match = True
                else:
                    if any(rx.search(combined) for rx in wi_regexes):
                        match = True
                    elif any(x in combined for x in pi):
                        match = True

                # D. Bull Mill Override
                if cat_name_std == "BULL MILL" and has_radius:
                    match = True
            else:
                match = (cat_name_std == "SEARCH ALL")

            if not match:
                continue

            # --- 4. KEYWORD & REGEX FILTER ---
            if search_query_list and not all(k in combined for k in search_query_list):
                continue
            if compiled_dyn_reg and not compiled_dyn_reg.search(combined):
                continue

            # --- 5. DIAMETER LOGIC ---
            if diam_val is not None:
                specs = item.get("specs", [])
                item_size_inch = None

                # Internal Spec Helper (remains local to stay clean)
                def get_spec(target_name):
                    if not isinstance(specs, list): return None
                    for s in specs:
                        if isinstance(s, list) and len(s) >= 2 and s[0] == target_name:
                            val_obj = s[1]
                            return val_obj.get("value") if isinstance(val_obj, dict) else val_obj
                    return None

                # Category-Specific Extraction
                if cat_name_std == "DRILLS":
                    item_size_inch = get_spec("Drill Bit Size (Decimal Inch)")
                elif cat_name_std == "SPOT / CENTER DRILLS":
                    item_size_inch = get_spec("Drill Diameter (Decimal Inch)") or get_spec("Drill Bit Size (Decimal Inch)")
                elif "END MILL" in cat_name_std or "ENDMILL" in cat_name_std:
                    item_size_inch = get_spec("Mill Diameter (Decimal Inch)")
                elif cat_name_std == "REAMERS":
                    item_size_inch = get_spec("Reamer Diameter (Decimal Inch)")
                elif cat_name_std == "COUNTERSINKS":
                    item_size_inch = get_spec("Body Diameter (Inch)") or get_spec("Head Diameter (Decimal Inch)")
                elif "DOUBLE ANGLE" in cat_name_std or "UNDERCUT" in cat_name_std:
                    raw_da = get_spec("Cutter Diameter (Inch)")
                    if raw_da: item_size_inch = self.convert_fraction_to_decimal(str(raw_da))
                elif cat_name_std == "CHAMFER MILLS":
                    raw_ch = get_spec("Cutter Head Diameter (Fractional Inch)")
                    if raw_ch: item_size_inch = self.convert_fraction_to_decimal(str(raw_ch))
                elif cat_name_std == "TAPS":
                    item_size_inch = get_spec("Thread Size (Inch)")
                elif "THREAD MILL" in cat_name_std:
                    item_size_inch = get_spec("Teeth Per Inch")

                # Fallback to Regex extraction
                if item_size_inch is None:
                    item_size_inch = self.extract_size(desc_orig)
                else:
                    try:
                        item_size_inch = float(item_size_inch)
                    except (ValueError, TypeError):
                        item_size_inch = self.extract_size(desc_orig)

                if item_size_inch is None:
                    continue
                
                diff = abs(item_size_inch - diam_val)
                if cat_name_std in ["REAMERS", "TAPS"] or "THREAD MILL" in cat_name_std:
                    if diff > 0.0005: continue
                elif cat_name_std in ["DRILLS", "SPOT / CENTER DRILLS"]:
                    direct_match = diff <= 0.005
                    metric_match = (diam_val >= 1.0 and abs(item_size_inch - (diam_val / 25.4)) <= 0.005)
                    if not (direct_match or metric_match): continue
                else:
                    if diff > 0.002: continue

            results.append(item)

        return results
    
        

    def get_menu_choice(self, options, title):
        keys = list(options.keys())
        idx = 0
        num = len(keys)
        self.clear(title)
        sys.stdout.write("\033[?25l") 
        try:
            while True:
                sys.stdout.write("\033[J")
                output = []
                for i, name in enumerate(keys):
                    if i == idx: output.append(f"  \033[1;97;42m > {name} \033[0m")
                    else: output.append(f"    {name}")
                sys.stdout.write("\n".join(output) + "\n")
                sys.stdout.flush()
                k = readchar.readkey()
                if k == rc_key.UP: idx = (idx - 1) % num
                elif k == rc_key.DOWN: idx = (idx + 1) % num
                elif k == rc_key.ENTER:
                    choice = keys[idx]
                    if choice not in ["EXIT", "BACK"]: self.history.append(choice)
                    return options[choice]
                elif k == rc_key.BACKSPACE or k == rc_key.ESC:
                    if self.history: self.history.pop()
                    return "BACK_REQ"
                sys.stdout.write(f"\033[{num}F")
        finally: sys.stdout.write("\033[?25h")

    def run(self):
        while True:
            self.history = []
            categories = {g["name"]: g["name"] for g in TOOL_CRIB_SEARCH_ALIAS_LIST}
            categories["EXIT"] = "EXIT"
            sel_cat = self.get_menu_choice(categories, "Select Tool Category")
            
            if sel_cat == "EXIT" or sel_cat == "BACK_REQ": 
                break

            diam_val = None
            dyn_reg = None
            keywords = ""
            breadcrumb_diam = "ALL" 

            # --- SEARCH ALL ---
            if sel_cat == "SEARCH ALL":
                self.results_stack = []
                self.results = list(self.data)
                self.page = 0
                self.results_loop(sel_cat, "ALL")
                continue 

            # --- SPECIAL CATEGORIES ---
            elif sel_cat == "Taps":
                self.clear("Dynamic Tap Search")
                user_in = input("Enter Tap Size: ").strip()
                if user_in:
                    breadcrumb_diam = user_in
                    self.history.append(user_in)
                    parts = re.split(r'[- Xx]+', user_in)
                    dyn_reg = rf"\b{re.escape(parts[0])}[- X\s]*{re.escape(parts[1])}" if len(parts) >= 2 else rf"\b{re.escape(user_in)}\b"
            
            elif sel_cat == "Thread Mills":
                self.clear("Thread Mill Pitch Search")
                pitch = input("Enter Pitch: ").strip()
                if pitch:
                    breadcrumb_diam = pitch
                    self.history.append(pitch)
                    dyn_reg = rf"[- X\s]{re.escape(pitch)}(\b|[A-Z])"

            # --- STANDARD CATEGORIES ---
            else:
                self.clear("Input Parameters")
                diam_str = input("Diameter (Enter for all): ").strip()
                if diam_str:
                    breadcrumb_diam = diam_str
                    self.history.append(diam_str)
                    diam_val = self.parse_size(diam_str)

            # --- EXECUTE SEARCH ---
            self.results_stack = [] 
            self.results = self.filtered_search(sel_cat, diam_val, keywords, dynamic_regex=dyn_reg)
            self.page = 0
            
            # Pass the category and the diameter string to the loop
            self.results_loop(sel_cat, breadcrumb_diam)

    def deep_clean(self, text):
        if text is None:
            return ""
        return " ".join(str(text).split()).lower()

    def results_loop(self, category_name, diameter):
        # Navigation and Pagination state
        page = 0
        idx = 0
        page_size = 20  
        results_stack = []
        
        # Breadcrumbs initialized with Diameter then Category
        breadcrumbs = [str(diameter), category_name.upper()]

        # ANSI Color codes for UI
        BAR_COLOR = "\033[1;33m"      # Yellow
        HEAD_COLOR = "\033[1;37m"     # Bold White
        SUB_COLOR = "\033[90m"        # Gray
        DESC_COLOR = "\033[1;38;5;51m" # Cyan
        NUM_NORMAL = "\033[1;37m"     # White Num
        NUM_CONFLICT = "\033[1;97;41m" # Red BG
        SEL_CURSOR = "\033[1;30;102m" # Green Arrow Highlight
        COL_CAT = "\033[1;32m"        # Static Green
        RESET = "\033[0m"

        # Widths for table columns
        item_w = 4
        desc_w = 65
        cat_w = 12

        # Initialize screen
        os.system('cls' if os.name == 'nt' else 'clear')
        sys.stdout.write("\033[?25l") # Hide cursor

        while True:
            # --- DYNAMIC SUB-CAT WIDTH CALCULATION ---
            # We calculate the widest sub-category currently in the filtered list
            raw_sub_w = 7 
            if len(self.results) > 0:
                current_max = 0
                for item in self.results:
                    val = str(item.get('itemSubGroupDescr', ''))
                    if len(val) > current_max:
                        current_max = len(val)
                raw_sub_w = current_max
            
            # Clamp the width between 7 and 30 characters
            if raw_sub_w < 7:
                sub_w = 7
            elif raw_sub_w > 30:
                sub_w = 30
            else:
                sub_w = raw_sub_w

            # --- PAGINATION CALCULATIONS ---
            sys.stdout.write("\033[H") # Move cursor to top left
            total_items = len(self.results)
            total_pages = (total_items + page_size - 1) // page_size
            if total_pages < 1:
                total_pages = 1
            
            # Extract only the items for the current page
            start_index = page * page_size
            end_index = start_index + page_size
            batch = self.results[start_index : end_index]
            
            # Ensure the selection cursor doesn't go out of bounds
            if len(batch) > 0:
                if idx >= len(batch):
                    idx = len(batch) - 1
            else:
                idx = 0

            # --- HEADER RENDERING ---
            path_display = " > ".join(breadcrumbs)
            if len(path_display) > 105:
                path_display = "..." + path_display[-102:]

            print(f"{BAR_COLOR} SEARCH PATH: {path_display}{RESET}\033[K")
            print(f"{SUB_COLOR}{'—' * 119}{RESET}\033[K")
            print(f"{DESC_COLOR}[ RESULTS: {total_items} ITEMS | PAGE {page+1} OF {total_pages} ]{RESET}\033[K\n")
            
            header_str = (
                f"    {HEAD_COLOR}{'ITEM':<{item_w}} | "
                f"{'DESCRIPTION':<{desc_w}} | "
                f"{'CAT':<{cat_w}} | "
                f"{'SUB-CAT':<{sub_w}}{RESET}"
            )
            print(f"{header_str}\033[K")
            print(f"{SUB_COLOR}{'—' * 119}{RESET}\033[K")

            # --- DATA ROWS RENDERING ---
            for i in range(len(batch)):
                item = batch[i]
                if i == idx:
                    selector = f"{SEL_CURSOR} > {RESET} "
                else:
                    selector = "    "
                
                # Extract and truncate fields to fit columns
                cat_val = str(item.get('itemGroupDescr', 'None'))[:cat_w]
                sub_val = str(item.get('itemSubGroupDescr', 'None'))[:sub_w]
                item_no = str(item.get('itemNumber', ''))[:item_w]
                descr = str(item.get('descr', ''))[:desc_w]
                
                # Check for conflicts to determine color
                if item.get('has_conflict') == True:
                    num_style = NUM_CONFLICT
                else:
                    num_style = NUM_NORMAL

                row_line = (
                    f"{selector}"
                    f"{num_style}{item_no:<{item_w}}{RESET} {SUB_COLOR}| {RESET}"
                    f"{DESC_COLOR}{descr:<{desc_w}}{RESET} {SUB_COLOR}| {RESET}"
                    f"{COL_CAT}{cat_val:<{cat_w}}{RESET} {SUB_COLOR}| {RESET}"
                    f"{BAR_COLOR}{sub_val:<{sub_w}}{RESET}"
                )
                print(f"{row_line}\033[K")

            # Fill remaining page space with empty lines to prevent UI jumping
            remaining_lines = page_size - len(batch)
            for _ in range(remaining_lines): 
                print("\033[K")
                
            # --- FOOTER RENDERING ---
            print(f"{SUB_COLOR}{'—' * 119}{RESET}\033[K")
            footer_text = " [Arrows] Nav | [I] Specs | [S] Refine | [E] Exclude | [U] Undo | [ESC] Back"
            sys.stdout.write(f"{BAR_COLOR} {footer_text:<117}{RESET}\033[K")
            sys.stdout.flush()

            # --- KEYBOARD INPUT HANDLING ---
            key = readchar.readkey()
            
            if key == readchar.key.UP:
                if len(batch) > 0:
                    if idx > 0:
                        idx = idx - 1
                    else:
                        idx = len(batch) - 1
            
            elif key == readchar.key.DOWN:
                if len(batch) > 0:
                    if idx < (len(batch) - 1):
                        idx = idx + 1
                    else:
                        idx = 0
            
            elif key == readchar.key.LEFT:
                if page > 0:
                    page = page - 1
                    idx = 0
            
            elif key == readchar.key.RIGHT:
                if page < (total_pages - 1):
                    page = page + 1
                    idx = 0

            elif key.lower() == 'i':
                if len(batch) > 0:
                    selected_item_no = batch[idx].get('itemNumber')
                    if selected_item_no:
                        sys.stdout.write("\033[?25h") # Show cursor
                        show_item_specs(ToolApp(), selected_item_no)
                        sys.stdout.write("\033[?25l") # Hide cursor
                        os.system('cls' if os.name == 'nt' else 'clear')

            elif key.lower() == 's' or key.lower() == 'e':
                # Determine Refine vs Exclude
                if key.lower() == 's':
                    mode = "S"
                    label = 'Refine:'
                else:
                    mode = "E"
                    label = 'Exclude:'

                sys.stdout.write("\033[?25h") # Show cursor for typing
                sys.stdout.write(f"\n{BAR_COLOR} {label}: {RESET}")
                sys.stdout.flush()
                
                user_input = input().strip()
                
                if user_input != "":
                    # Push current state to undo stack
                    results_stack.append((list(self.results), list(breadcrumbs)))
                    
                    # Regex for double-double quotes: ""phrase"" or single words
                    import re
                    # Looks for text inside "" "" or sequences of non-whitespace
                    raw_matches = re.findall(r'""([^""]*)""|(\S+)', user_input.lower())
                    
                    search_terms = []
                    for m in raw_matches:
                        if m[0]: # If group 1 (inside quotes) matched
                            search_terms.append(self.deep_clean(m[0]))
                        elif m[1]: # If group 2 (single word) matched
                            search_terms.append(self.deep_clean(m[1]))

                    if len(search_terms) > 0:
                        filtered_list = []
                        for item in self.results:
                            # Build a large searchable string from item fields
                            fields = [
                                str(item.get('itemNumber','')), 
                                str(item.get('itemAliasNumber','')), 
                                str(item.get('descr','')), 
                                str(item.get('brand','')), 
                                str(item.get('itemGroupDescr','')), 
                                str(item.get('itemSubGroupDescr',''))
                            ]
                            combined_data = self.deep_clean(" ".join(fields))
                            
                            # Perform OR check: match is true if ANY term is found
                            has_match = False
                            for t in search_terms:
                                if t in combined_data:
                                    has_match = True
                                    break
                            
                            # Filter logic based on Mode
                            if mode == "S": # Refine (Include matches)
                                if has_match == True:
                                    filtered_list.append(item)
                            else: # Exclude (Remove matches)
                                if has_match == False:
                                    filtered_list.append(item)
                        
                        # Update state
                        self.results = filtered_list
                        page = 0
                        idx = 0
                        
                        # Create Breadcrumb: "INC TERM1 OR TERM2"
                        if mode == "S":
                            prefix = "INC"
                        else:
                            prefix = "NOT"
                        
                        formatted_terms = []
                        for t in search_terms:
                            formatted_terms.append(t.upper())
                        
                        breadcrumb_text = prefix + " " + " OR ".join(formatted_terms)
                        breadcrumbs.append(breadcrumb_text)
                
                # Cleanup the input line visually
                sys.stdout.write("\033[1;A\033[2K\033[?25l")

            elif key.lower() == 'u':
                if len(results_stack) > 0:
                    old_results, old_breadcrumbs = results_stack.pop()
                    self.results = old_results
                    breadcrumbs = old_breadcrumbs
                    page = 0
                    idx = 0
                
            elif key == readchar.key.ESC:
                break

        # Cleanup on exit
        sys.stdout.write("\033[?25h")
if __name__ == "__main__":
    ToolSearcher("database.json", "shadowdatabase.json").run()