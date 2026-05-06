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
    def __init__(self, db_path):
        self.db_path = db_path
        self.history = []
        self.data = self._load_db()
        self.results = []
        self.results_stack = []
        self.page = 0
        self.page_size = 15


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
        frac_match = re.search(r'(\d+/\d+)', head)
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

    def filtered_search(self, cat_name, diam_val, keywords, source_set=None, dynamic_regex=None):
        dataset = source_set if source_set is not None else self.data
        cat_name_std = str(cat_name).upper() 
        group_meta = next((g for g in TOOL_CRIB_SEARCH_ALIAS_LIST if g["name"].upper() == cat_name_std), None)
        
        results = []
        search_query = str(keywords).lower() if keywords else ""

        for item in dataset:
            # Extract fields safely
            desc = str(item.get("descr", "")).lower()
            alias = str(item.get("itemAliasNumber", "")).lower()
            item_n = str(item.get("itemNumber", "")).lower()
            i_grp = str(item.get("itemGroupDescr", "")).upper()
            i_sub = str(item.get("itemSubGroupDescr", "")).upper()
            brand = str(item.get("brand", "")).lower() # <--- NEW: Extract Brand
            
            # --- UPDATED: ADDED BRAND TO SEARCH STRING ---
            # Search now covers: Item#, Alias, Description, Group, Sub-Group, and Brand
            combined = f"{item_n} {alias} {desc} {i_grp.lower()} {i_sub.lower()} {brand}"

            if cat_name_std == "SEARCH ALL":
                match = True 
            else:
                match = False
                # EXCLUDE Spot Drills from main Drills category
                if cat_name_std == "DRILLS":
                    if i_grp == "DRILL" and i_sub != "SPOT DRILL": 
                        match = True
                
                # INCLUDE Spot Drills specifically here
                elif cat_name_std == "SPOT / CENTER DRILLS":
                    if i_sub == "SPOT DRILL" or i_grp == "SPOT": 
                        match = True
                
                # Standard category matches
                elif cat_name_std == "CHAMFER MILLS" and i_sub == "CHMF MILL": match = True
                elif cat_name_std == "COUNTERSINKS" and i_grp == "COUNTERSINK": match = True
                elif cat_name_std == "REAMERS" and i_grp == "REAMER": match = True
                elif cat_name_std == "TAPS" and (
                    i_sub == "FORM TAP" or 
                    i_sub == "GUN TAP" or 
                    i_sub == "HELICOIL TAP" or 
                    i_sub == "HIGH SPIRAL TAP" or 
                    i_sub == "METRIC TAP" or 
                    i_sub == "SPIRALOK TAP"
                ):
                    match = True
                
                # Synonym Fallback
                if not match and group_meta:
                    he = group_meta.get("hard_exclude", set())
                    ws = group_meta.get("word_syns", set())
                    ps = group_meta.get("part_syns", set())
                    if any(re.search(rf"\b{re.escape(x)}\b", combined) for x in he): continue
                    if any(re.search(rf"\b{re.escape(s)}(?=[,\s]|$)", combined) for s in ws) or \
                       any(s in combined for s in ps):
                        match = True

            if not match: continue

            # The search query now automatically checks the brand as well
            if search_query and search_query not in combined:
                continue

            if dynamic_regex:
                if not re.search(dynamic_regex, combined, re.IGNORECASE): continue

            if diam_val is not None:
                item_size_inch = self.extract_size(desc)
                
                if item_size_inch is not None:
                    # 1. REAMER LOGIC: Strict +/- 0.0005
                    if cat_name_std == "REAMERS":
                        if abs(item_size_inch - diam_val) <= 0.0005:
                            pass # Match
                        else:
                            continue

                    # 2. DRILL LOGIC: Similarity Bridge +/- 0.005
                    elif cat_name_std in ["DRILLS", "SPOT / CENTER DRILLS"]:
                        # Direct check
                        if abs(item_size_inch - diam_val) <= 0.005:
                            pass 
                        # 2. REFINED METRIC FALLBACK
                        # Only trigger if the input 'looks' like a metric number (e.g., 1.0 or higher)
                        # This prevents .122 from being converted into .0048 inches.
                        elif diam_val >= 1.0 and abs(item_size_inch - (diam_val / 25.4)) <= 0.005:
                            pass
                        
                        else:
                            continue

                    # 3. ALL OTHER CATEGORIES: Standard check
                    else:
                        if abs(item_size_inch - diam_val) <= 0.002:
                            pass
                        else:
                            continue
                else:
                    # If tool has no size in description, skip it during a diameter search
                    continue
            
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
            if sel_cat == "EXIT" or sel_cat == "BACK_REQ": break

            diam_val = None
            dyn_reg = None
            keywords = ""

            # --- SEARCH ALL: Jump straight to view ---
            if sel_cat == "SEARCH ALL":
                self.results_stack = []
                self.results = list(self.data) # Load everything
                self.page = 0
                self.results_loop(sel_cat)
                continue # Return to categories after exiting results_loop

            # Standard category logic for others...
            elif sel_cat == "Taps":
                self.clear("Dynamic Tap Search")
                user_in = input("Enter Tap Size: ").strip()
                if user_in:
                    self.history.append(user_in)
                    parts = re.split(r'[- Xx]+', user_in)
                    dyn_reg = rf"\b{re.escape(parts[0])}[- X\s]*{re.escape(parts[1])}" if len(parts) >= 2 else rf"\b{re.escape(user_in)}\b"
            elif sel_cat == "Thread Mills":
                self.clear("Thread Mill Pitch Search")
                pitch = input("Enter Pitch: ").strip()
                if pitch:
                    self.history.append(pitch)
                    dyn_reg = rf"[- X\s]{re.escape(pitch)}(\b|[A-Z])"

            else:
                self.clear("Input Parameters")
                diam_str = input("Diameter (Enter for all): ").strip()
                if diam_str:
                    self.history.append(diam_str) # Add diameter to history
                    diam_val = self.parse_size(diam_str)
            # Inside the run(self) method, right before initial search:
            self.results_stack = [] # Reset stack for a new top-level search
            self.results = self.filtered_search(sel_cat, diam_val, keywords, dynamic_regex=dyn_reg)
            # Initial search
            self.results = self.filtered_search(sel_cat, diam_val, keywords, dynamic_regex=dyn_reg)
            self.page = 0
            self.results_loop(sel_cat)

    def results_loop(self, title):
        while True:
            total_items = len(self.results)
            total_pages = max(1, (total_items + self.page_size - 1) // self.page_size)
            current_page_display = self.page + 1

            self.clear(f"Results: {title} ({total_items}) | Page {current_page_display} of {total_pages}")
            
            # (Keep your existing table drawing logic here...)
            # --- TABLE DRAWING START ---
            W_ITEM = 5 
            start = self.page * self.page_size
            batch = self.results[start:start + self.page_size]
            current_max_info, current_max_desc, formatted_data = 0, 0, []
            for m in batch:
                item_n, alias, grp, sub, descr = str(m.get('itemNumber', ''))[:W_ITEM], str(m.get('itemAliasNumber', '')), str(m.get('itemGroupDescr', '')), str(m.get('itemSubGroupDescr', '')), str(m.get('descr', ''))
                cat_tag = f"[{grp}/{sub}]"; alias_part = f"{alias} " if alias else ""; plain_info = f"{alias_part}{cat_tag}"
                current_max_info = max(current_max_info, len(plain_info)); current_max_desc = max(current_max_desc, len(descr))
                formatted_data.append({'item': item_n, 'alias': alias_part, 'cat': cat_tag, 'desc': descr, 'plain_len': len(plain_info)})
            W_INFO = current_max_info + 1
            total_bar_length = W_ITEM + 3 + W_INFO + 3 + current_max_desc
            print(f"{'ITEM#':<{W_ITEM}} | {'ALIAS & CATEGORY':<{W_INFO}} | {'DESCRIPTION'}\n" + "—" * total_bar_length)
            for d in formatted_data:
                info_col = f"{C_ALIAS}{d['alias']}{C_RESET}\033[2;90m{d['cat']}\033[0m"
                print(f"{C_ITEM}{d['item']:<{W_ITEM}}{C_RESET} | {info_col}{' '*(W_INFO-d['plain_len'])} | {C_DESC}{d['desc']}{C_RESET}")
            print("—" * total_bar_length)
            # --- TABLE DRAWING END ---

            help_hint = " | [Ctrl+R] Help" if title == "SEARCH ALL" else ""
            print(f"{C_HDR}[Arrows] Page {current_page_display}/{total_pages} | [S] Refine | [E] Exclude | [U] Undo{help_hint} | [ESC] Back{C_RESET}")
            
            k = readchar.readkey()

            # Helper for deep cleaning strings (removes spaces, dashes, etc)
            def deep_clean(t):
                return str(t).lower().replace(" ", "").replace("-", "")

            if k == "\x12" and title == "SEARCH ALL":
                bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cribsearchinstructions.bat")
                os.system(f'start "" "{bat_path}"') if os.path.exists(bat_path) else print("Help not found.")

            elif k == rc_key.BACKSPACE or k == rc_key.ESC: 
                break

            # --- UPDATED SEARCH LOGIC (S & E) ---
            elif k.lower() in ["s", "e"]:
                mode = "S" if k.lower() == "s" else "E"
                prompt = "\nFuzzy Refine: " if mode == "S" else "\nTerm to Exclude: "
                user_in = input(prompt).strip()
                
                if user_in:
                    self.results_stack.append(list(self.results))
                    is_or = '"' in user_in
                    
                    # Pre-clean search terms
                    if is_or:
                        terms = [deep_clean(t[0] if t[0] else t[1]) for t in re.findall(r'"([^"]*)"|(\S+)', user_in.lower())]
                    else:
                        terms = [deep_clean(user_in)]

                    new_results = []
                    for item in self.results:
                        # BUILD DATA STRING: Include ALL relevant fields
                        data_str = deep_clean(f"{item.get('itemNumber','')} {item.get('itemAliasNumber','')} {item.get('descr','')} {item.get('brand','')} {item.get('itemGroupDescr','')} {item.get('itemSubGroupDescr','')}")
                        
                        match = any(t in data_str for t in terms)
                        
                        if mode == "S" and match: new_results.append(item)
                        elif mode == "E" and not match: new_results.append(item)
                    
                    self.results = new_results
                    prefix = "OR: " if is_or else ""
                    self.history.append(f"{'INC' if mode == 'S' else 'NOT'}: {prefix}{user_in}")
                    self.page = 0

            elif k.lower() == "u" and self.results_stack:
                self.results = self.results_stack.pop()
                if self.history: self.history.pop()
                self.page = 0
            
            elif k in [rc_key.DOWN, rc_key.RIGHT]:
                if (self.page + 1) * self.page_size < len(self.results): self.page += 1
            elif k in [rc_key.UP, rc_key.LEFT]:
                if self.page > 0: self.page -= 1

if __name__ == "__main__":
    ToolSearcher("database.json").run()