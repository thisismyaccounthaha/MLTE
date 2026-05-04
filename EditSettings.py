import os
import sys
import json
import readchar
from settings import cfg

class SettingsEditor:
    def __init__(self):
        self.history = ["SETTINGS"]
        self.config = cfg.data  # Working directly on the loaded JSON data

    def clear(self, title=""):
        os.system('cls' if os.name == 'nt' else 'clear')
        if self.history:
            print(f"\033[1;33m{' > '.join(self.history)}\033[0m")
            print("\033[1;33m" + "—" * 55 + "\033[0m")
        else:
            print("\033[1;34m--- CONFIGURATION MANAGER ---\033[0m\n")
        
        if title:
            print(f"\033[1;36m[ {title.upper()} ]\033[0m\n")

    def safe_pop(self):
        """Safely remove the last breadcrumb without crashing if the list is empty."""
        if len(self.history) > 1:
            return self.history.pop()
        return None

    def get_menu_choice(self, options, title):
        keys = list(options.keys())
        idx = 0
        num_options = len(keys)
        self.clear(title)
        sys.stdout.write("\033[?25l") 
        try:
            while True:
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
                if key == readchar.key.UP:
                    idx = (idx - 1) % num_options
                elif key == readchar.key.DOWN:
                    idx = (idx + 1) % num_options
                elif key == readchar.key.ENTER:
                    choice_label = keys[idx]
                    if choice_label not in ["BACK", "SAVE & EXIT", "DISCARD & EXIT"]:
                        self.history.append(choice_label[:15])
                    return options[choice_label]
                elif key == readchar.key.BACKSPACE or key == readchar.key.ESC:
                    return "BACK_REQ"
                
                sys.stdout.write(f"\033[{num_options}F")
        finally:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    def prompt(self, title, label, current_val="", show_reference=False):
        self.clear(title)
        
        # If adding a new line, show existing lines as a template
        if show_reference:
            print("\033[1;30mREFERENCE TEMPLATE (Existing Lines):\033[0m")
            print(f"\033[90m{'Name':<10} | {'IP Address':<15} | {'Path'}\033[0m")
            for l in self.config["line_configs"][:3]: # Show first 3 as examples
                print(f"\033[90m{l['name']:<10} | {l['ip']:<15} | {l['path']}\033[0m")
            print("\033[1;33m" + "—" * 55 + "\033[0m\n")

        if current_val:
            print(f"\033[90mCurrent: {current_val}\033[0m")
        
        val = input(f"\033[1;97m{label}: \033[0m").strip()
        
        # Path cleanup logic
        if val.startswith('\\\\'):
            val = val.replace('\\\\\\\\', '\\\\')
            
        return val if val else current_val

    
    def edit_shop_floor(self):
        while True:
            # Access the dedicated shop_floor section
            sf = self.config.setdefault("shop_floor", {"password": ""})
            opts = {
                f"Password: {sf['password']}": "password",
                "BACK": "BACK"
            }
            choice = self.get_menu_choice(opts, "Shop Floor Settings")
            if choice == "BACK" or choice == "BACK_REQ":
                self.history.pop()
                break
            
            sf[choice] = self.prompt("Update Password", "New Shop Floor Password", sf[choice])
            self.history.pop()

    def edit_db_creds(self):
        while True:
            # Access the dedicated database_creds section
            db = self.config.setdefault("database_creds", {"uid": "", "pwd": ""})
            opts = {
                f"DB User: {db['uid']}": "uid",
                f"DB Pass: {db['pwd']}": "pwd",
                "BACK": "BACK"
            }
            choice = self.get_menu_choice(opts, "Database Credentials")
            if choice == "BACK" or choice == "BACK_REQ":
                self.history.pop()
                break
            
            db[choice] = self.prompt("Update DB Creds", f"New {choice.upper()}", db[choice])
            self.history.pop()

    

    def edit_lines(self):
        idx = 0
        sys.stdout.write("\033[?25l") # Hide cursor
        
        # Clear once at the start to draw the header and breadcrumbs
        self.clear("Machine Line Configurations")
        
        try:
            while True:
                lines = self.config.setdefault("line_configs", [])
                opts_labels = [f"{line['name']} ({line['ip']})" for line in lines]
                opts_labels.append("[+] ADD NEW LINE")
                opts_labels.append("BACK")
                
                total_rows = len(opts_labels)

                # Move cursor to the row just below the "Machine Line Configurations" header
                # This prevents redrawing the whole screen. Adjust the number '4' if 
                # your header/breadcrumbs take up more/less lines.
                sys.stdout.write("\033[4;1H") 
                
                print("\033[90m(Arrows: Navigate | DEL/'D': Delete Line | Enter: Edit Details)\033[0m")
                # Clear to end of line to keep the instructions clean
                sys.stdout.write("\033[K\n") 

                for i, label in enumerate(opts_labels):
                    # \033[K clears the line before printing to prevent "ghost text"
                    sys.stdout.write("\033[K") 
                    if i == idx:
                        print(f"  \033[1;97;42m > {label} \033[0m")
                    else:
                        print(f"    {label}")

                key = readchar.readkey()

                # --- Navigation ---
                if key == readchar.key.UP:
                    idx = (idx - 1) % total_rows
                elif key == readchar.key.DOWN:
                    idx = (idx + 1) % total_rows
                
                # --- DELETE ---
                elif key in [readchar.key.DELETE, 'd', 'D']:
                    if idx < len(lines):
                        target_name = lines[idx]['name']
                        confirm = self.prompt("Confirm Delete", f"Delete {target_name}? (y/n)", "")
                        if confirm.lower() == 'y':
                            lines.pop(idx)
                            if idx >= len(lines) and idx > 0:
                                idx -= 1
                        # After a prompt, we MUST clear to restore the menu layout
                        self.clear("Machine Line Configurations")
                        self.history.pop()

                # --- ENTER ---
                elif key == readchar.key.ENTER:
                    selection = opts_labels[idx]
                    if selection == "BACK":
                        self.safe_pop()
                        return
                    
                    if selection == "[+] ADD NEW LINE":
                        # 1. Ask for Name
                        name = self.prompt("Add Line", "Line Name", show_reference=True)
                        self.safe_pop() # Pop "Add Line" from history immediately after input
                        
                        # 2. Ask for IP
                        ip = self.prompt("Add Line", "IP Address", show_reference=True)
                        self.safe_pop()
                        
                        # 3. Ask for Path
                        path = self.prompt("Add Line", "Network Path", show_reference=True)
                        self.safe_pop()
                        
                        new_line = {
                            "name": name,
                            "ip": ip,
                            "db": "Makino",  # Hardcoded: No prompt, always Makino
                            "path": path
                        }
                        
                        # Only append if user didn't cancel/leave Name and IP blank
                        if name and ip:
                            lines.append(new_line)
                        
                        self.clear("Machine Line Configurations")
                        
                    else:
                        self.manage_line_details(lines[idx])
                        self.clear("Machine Line Configurations")
                elif key in [readchar.key.BACKSPACE, readchar.key.ESC]:
                    self.history.pop()
                    return
        finally:
            sys.stdout.write("\033[?25h") # Show cursor

    def manage_line_details(self, line_dict):
        """Sub-menu to edit individual fields of a line (IP, Name, etc)"""
        while True:
            opts = {
                f"Name: {line_dict['name']}": "name",
                f"IP:   {line_dict['ip']}": "ip",
                f"DB:   {line_dict['db']}": "db",
                f"Path: {line_dict['path']}": "path",
                "BACK": "BACK"
            }
            choice = self.get_menu_choice(opts, f"Edit {line_dict['name']}")
            
            # If the user chose BACK or ESC
            if choice in ["BACK", "BACK_REQ"]:
                # ONLY pop if there is actually something to pop
                if len(self.history) > 1:
                    self.history.pop()
                return
            
            # Update value logic
            line_dict[choice] = self.prompt("Edit Line", f"New {choice}", line_dict[choice])
            
            # After prompt returns, self.prompt usually handles its own history pop, 
            # but check if your prompt() function is also popping!
            if len(self.history) > 1:
                self.history.pop()

    def edit_msc(self):
        while True:
            # Safely get the msc_vending section
            msc = self.config.setdefault("msc_vending", {
                "user": "", "pass": "", 
                "urls": {"login": "", "portal": "", "data": ""}
            })
            
            opts = {
                f"User: {msc['user']}": "user",
                f"Pass: {msc['pass']}": "pass",
                "EDIT URLS": "URLS",
                "BACK": "BACK"
            }
            
            choice = self.get_menu_choice(opts, "MSC Vending Settings")
            if choice == "BACK" or choice == "BACK_REQ":
                self.history.pop()
                break
            
            if choice == "URLS":
                self.edit_msc_urls(msc["urls"])
                self.history.pop()
            else:
                msc[choice] = self.prompt("Update MSC Creds", f"New MSC {choice}", msc[choice])
                self.history.pop()

    def edit_msc_urls(self, urls):
        while True:
            opts = {
                f"Login:  {urls['login'][:30]}...": "login",
                f"Portal: {urls['portal'][:30]}...": "portal",
                f"Data:   {urls['data'][:30]}...": "data",
                "BACK": "BACK"
            }
            choice = self.get_menu_choice(opts, "MSC URL Configuration")
            if choice == "BACK" or choice == "BACK_REQ":
                break
            
            urls[choice] = self.prompt("Update URL", f"New {choice} URL", urls[choice])

    def save_to_disk(self):
        with open(cfg.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)
        print(f"\n\033[1;92m✔ Settings Saved. Restarting MLTE...\033[0m")
        import time
        time.sleep(1) # Brief pause so the user sees the success message
        return "RESTART"
    def edit_ranges(self):
        while True:
            ranges = self.config.setdefault("search_ranges", {})
            opts = {f"{k}": k for k in ranges.keys()}
            opts["BACK"] = "BACK"

            choice = self.get_menu_choice(opts, "Tool Search Ranges")
            
            # Use this check to prevent popping an empty list
            if choice in ["BACK", "BACK_REQ"]:
                if len(self.history) > 1: # Keep at least the root breadcrumb
                    self.history.pop()
                return 

            # If it's not BACK, it's a tool type (Endmills, Drills, etc.)
            self.manage_specific_range(choice, ranges[choice])

    def manage_specific_range(self, tool_label, range_list):
        idx = 0
        sys.stdout.write("\033[?25l") # Hide cursor
        
        # Clear once at the start to establish header/breadcrumbs
        self.clear(f"Manage {tool_label}")
        
        try:
            while True:
                num_options = len(range_list)
                opts_labels = [f"Range {i+1}: {r[0]} - {r[1]}" for i, r in enumerate(range_list)]
                opts_labels.append("[+] ADD NEW RANGE")
                opts_labels.append("BACK")
                
                total_rows = len(opts_labels)

                # Jump cursor to the 4th line (below the header/breadcrumbs)
                sys.stdout.write("\033[4;1H") 
                
                print("\033[90m(Arrows: Navigate | DEL/'D': Delete | Enter: Edit)\033[0m")
                sys.stdout.write("\033[K\n") # Clear line to end

                # Draw the menu
                for i, label in enumerate(opts_labels):
                    sys.stdout.write("\033[K") # Prevent "ghost" characters
                    if i == idx:
                        print(f"  \033[1;97;42m > {label} \033[0m")
                    else:
                        print(f"    {label}")

                key = readchar.readkey()

                # --- Navigation ---
                if key == readchar.key.UP:
                    idx = (idx - 1) % total_rows
                elif key == readchar.key.DOWN:
                    idx = (idx + 1) % total_rows
                
                # --- DELETE ---
                elif key in [readchar.key.DELETE, 'd', 'D']:
                    if idx < len(range_list):
                        range_list.pop(idx)
                        if idx >= len(range_list) and idx > 0:
                            idx -= 1
                        self.clear(f"Manage {tool_label}")
                
                # --- ENTER ---
                elif key == readchar.key.ENTER:
                    selection = opts_labels[idx]
                    
                    if selection == "BACK":
                        self.safe_pop() # Use safe_pop here
                        return
                    
                    if selection == "[+] ADD NEW RANGE":
                        low = self.prompt(f"Add {tool_label}", "Start Number")
                        high = self.prompt(f"Add {tool_label}", "End Number")
                        if low.isdigit() and high.isdigit():
                            range_list.append([int(low), int(high)])
                        
                        # Fix: Safely clean up the history used by the two prompts
                        self.safe_pop() 
                        self.safe_pop()
                        self.clear(f"Manage {tool_label}")
                    else:
                        # Edit Existing
                        low = self.prompt("Edit Range", "New Start", str(range_list[idx][0]))
                        high = self.prompt("Edit Range", "New End", str(range_list[idx][1]))
                        if low.isdigit() and high.isdigit():
                            range_list[idx] = [int(low), int(high)]
                        
                        # Fix: Safely clean up the history used by the two prompts
                        self.safe_pop()
                        self.safe_pop()
                        self.clear(f"Manage {tool_label}")

                elif key in [readchar.key.BACKSPACE, readchar.key.ESC]:
                    self.safe_pop()
                    return
        finally:
            sys.stdout.write("\033[?25h")

    def run(self):
        while True:
            main_opts = {
                "SHOP FLOOR PASSWORD": self.edit_shop_floor,
                "DATABASE CREDENTIALS": self.edit_db_creds,
                "MSC VENDING SETTINGS": self.edit_msc,
                "SEARCH RANGES": self.edit_ranges,      # <--- ADD THIS LINE
                "MACHINE LINES": self.edit_lines,
                "SAVE & EXIT": self.save_to_disk,
                "DISCARD & EXIT": lambda: "DISCARD"
            }
            
            action = self.get_menu_choice(main_opts, "Settings Menu")
            
            # 1. Handle the "Back" request from the menu
            if action == "BACK_REQ":
                return "DISCARD"
            
            # 2. Handle if the action is a function (like edit_ranges)
            if callable(action):
                result = action()
                
                # If the function we just ran wants a restart, pass it up
                if result == "RESTART":
                    return "RESTART"
                
                # If it was a discard signal
                if result == "DISCARD":
                    return "DISCARD"
            
            # 3. Handle a direct string return (like the Discard lambda)
            elif action == "DISCARD":
                return "DISCARD"

if __name__ == "__main__":
    app = SettingsEditor()
    app.run()