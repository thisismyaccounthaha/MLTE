import json
import os
import re
import sys
from turtle import title
import readchar
import shutil
from readchar import key as rc_key

C_HDR, C_ITEM, C_DESC, C_ALIAS, C_RESET = "\033[1;36m", "\033[1;33m", "\033[1;37m", "\033[1;32m", "\033[0m"
C_DEBUG = "\033[1;31m" # Red for debug visibility

# -------------------------------
# EXTENSIVE SYNONYM SYSTEM
# -------------------------------
ALIAS_GROUPS = [
    {
        "name": "Square Endmill",
        "word_syns": {"endmill", "end mill", "mill", "em", "e.m."},
        "part_syns": {"sem", "eml", "sqr end", "square end", "flat end", "e.m."},
        "alias_exclude": {"item", "system", "them", "email", "dykem"},
        "hard_exclude": {"ball", "tpi", "chmfr", "bn", "radius", "rad", "c.r.", "cr", "corner", "bullnose", "chamfer", "chf", "tap", "lollipop"}
    },
    {
        "name": "Ball Mill",
        "word_syns": {"ballmill", "ball mill", "ballnose", "ball", "ballendmill"},
        "part_syns": set(),
        "alias_exclude": set(),
        "hard_exclude": {"square", "flat", "tpi", "sqr", "corner radius", "c.r.", "corner rounding", "reamer", "bearing", "bearings", "bur", "moved"}
    },
    {
        "name": "Bull Mill",
        "word_syns": {"corner radius", "cr", "c.r.", "bullnose", "bull nose", "radius end", "bullmill"},
        "part_syns": {"rad em", "bn"},
        "alias_exclude": {"screw", "craft", "crane", "creek"},
        "hard_exclude": {"ball", "square", "flat", "pilot", "corner rounding", "tpi", "undercutting"}
    },
    {
        "name": "Drills",
        "word_syns": {"drill", "drilling", "jobber", "stub drill", "micro drill", "carbide drill", "130d", "118d", "135d", "para drill", "cool thru drill", "guhr", "screw mach drl"},
        "part_syns": {"drl"},
        "alias_exclude": set(),
        "hard_exclude": {"tap", "threadmill", "tm", "reams", "reamer", "spot", "drill mill", "chf", "chamf", "chamfer", "countersink", "csink", "ctrsnk"}
    },
    {
        "name": "Taps",
        "word_syns": {"tap", "tapping", "thread tap", "spiral tap", "plug tap", "btm tap", "form tap", "roll form", "sti tap", "sp pt", "sp flt", "exotap"},
        "part_syns": set(),
        "alias_exclude": {"tape", "taper", "tapered"},
        "hard_exclude": {"drill", "thread mill", "tm", "debur"}
    },
    {
        "name": "Thread Mills",
        "word_syns": {"threadmill", "thread mill", "tm", "t.m.", "pitch mill", "thrd mill", "thrd. mill", "th. mill", "th mill", "thrd tool", "thread tool", "threadmill"},
        "part_syns": set(),
        "alias_exclude": {"atm", "platform", "html", "stme", "time"},
        "hard_exclude": {"drill", "tap"}
    },
    {
        "name": "Chamfer Mills",
        "word_syns": {"chamfer", "cmf", "chamf", "chmf", "chamfer mill", "chf", "back chamfer", "drill mill,"},
        "part_syns": set(),
        "alias_exclude": {"chef"},
        "hard_exclude": {"square", "flat", "ball", "drill", "debur", "tap"}
    },
    {
        "name": "Countersinks",
        "word_syns": {"countersink", "csink", "ctrsnk", "counter sink", "c'sink", "sf hss c'sink", "6fl hss c'sink", "uniflute"},
        "part_syns": set(),
        "alias_exclude": {"sink"},
        "hard_exclude": {"drill", "endmill"}
    },
    {
        "name": "Spot / Center Drills",
        "word_syns": {"spot drill", "spotting drill", "center drill", "spotdrill", "spot", "cb nc", "spotting"},
        "part_syns": set(),
        "alias_exclude": {"transport", "hotspot"},
        "hard_exclude": {"jobber", "long length", "tap"}
    },
    {
        "name": "Lollipop / Undercut",
        "word_syns": {"undercut", "lollipop", "270 deg", "double angle", "spherical mill"},
        "part_syns": set(),
        "alias_exclude": set(),
        "hard_exclude": {"square", "drill"}
    },
    {
        "name": "Reamers",
        "word_syns": {"reams", "reamer", "chucking reamer", "hss reamer", "carbide reamer"},
        "part_syns": {"rmr"},
        "alias_exclude": {"armor", "warm"},
        "hard_exclude": {"drill", "tap"}
    },
    {
        "name": "Keyseat / Woodruff",
        "word_syns": {"woodruff", "keyseat", "key seat", "slot mill", "t-slot", "woody", "key"},
        "part_syns": set(),
        "alias_exclude": set(),
        "hard_exclude": {"endmill", "drill"}
    },
    {
        "name": "SEARCH ALL",
        "word_syns": set(),
        "part_syns": set(),
        "alias_exclude": set(),
        "hard_exclude": set()
    }
]

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
            text = text.lower().strip()
            
            # Handle Metric (mm) conversion
            if "mm" in text or (text.endswith("m") and not text.endswith("em")):
                clean_val = text.replace("mm", "").replace("m", "").strip()
                # Convert mm to inches: mm / 25.4
                return round(float(clean_val) / 25.4, 4)
            
            # Handle Fractions
            if "/" in text:
                n, d = text.split("/")
                return round(float(n)/float(d), 4)
            
            # Handle Standard Decimals
            return round(float(text), 4)
        except: 
            return None

    def extract_size(self, text):
        # Updated Regex to catch patterns like "10mm", "6.5mm", or "1/4"
        # Now includes optional 'mm' at the end of the digit group
        match = re.search(r'(\d+/\d+|\d*\.\d+|\d+)\s*(mm|m)?', text.lower())
        if match:
            # Reconstruct the string (e.g., "10" + "mm") to pass to parse_size
            full_val = match.group(1) + (match.group(2) if match.group(2) else "")
            return self.parse_size(full_val)
        return None

    def filtered_search(self, cat_name, diam_val, keywords, source_set=None, dynamic_regex=None):
        dataset = source_set if source_set is not None else self.data
        cat_name_std = str(cat_name).upper() 
        group_meta = next((g for g in ALIAS_GROUPS if g["name"].upper() == cat_name_std), None)
        
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
                
                # Check 1: Direct match (e.g., 0.5 == 0.5)
                if item_size_inch == diam_val:
                    pass # Match found
                
                # Check 2: Metric fallback 
                # If user typed '5.5', check if the tool is 5.5mm (0.2165")
                elif round(diam_val / 25.4, 4) == item_size_inch:
                    pass # Match found (User typed MM value without suffix)
                
                else:
                    continue # No matchue
            
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
            categories = {g["name"]: g["name"] for g in ALIAS_GROUPS}
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