import json
import os
import sys

class Settings:
    def __init__(self, config_name="config.json"):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(base_dir, config_name)
        self.data = self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_path):
            print(f"Error: {self.config_path} not found.")
            sys.exit(1)
        with open(self.config_path, 'r') as f:
            return json.load(f)

    def save_config(self):
        with open(self.config_path, 'w') as f:
            json.dump(self.data, f, indent=4)

    @property
    def shop_floor_password(self): 
        return self.data.get("shop_floor", {}).get("password", "")

    @property
    def db_creds(self):
        # Access the new nested dictionary
        db_data = self.data.get("database_creds", {})
        
        # Return the dictionary in the exact format MLTE.py expects
        return {
            'uid': db_data.get("uid", ""),
            'pwd': db_data.get("pwd", "")
        }

    @property
    def line_configs(self): return self.data["line_configs"]

    @property
    def endmill_sub_types(self): return self.data["endmill_sub_types"]

    @property
    def special_sub_types(self): return self.data["special_sub_types"]

    @property
    def tap_standard(self): return self.data["tap_standard"]

    @property
    def tap_metric(self): return self.data["tap_metric"]

    @property
    def search_ranges(self):
        # Convert list of lists back to list of tuples for range compatibility if needed
        return {k: [tuple(r) for r in v] for k, v in self.data["search_ranges"].items()}

    @property
    def keyword_search_ranges(self):
        ranges = self.search_ranges
        ranges["Item Number"] = [(0, 99999999)]
        return ranges

    @property
    def holder_list(self): return self.data["holder_list"]

    @property
    def tool_kinds(self): return self.data["tool_kinds"]

    @property
    def tool_types(self): return self.data["tool_types"]

    @property
    def life_types(self): return self.data["life_types"]

    @property
    def read_only_lines(self): 
        return self.data.get("sync_settings", {}).get("read_only_lines", [])

    @property
    def priority_order(self): 
        return self.data.get("sync_settings", {}).get("priority_order", [])

    @property
    def mapping(self): 
        return self.data.get("sync_settings", {}).get("column_mapping", {})
    
    @property
    def msc_creds(self):
        return {
            "user": self.data["msc_vending"]["user"],
            "pass": self.data["msc_vending"]["pass"]
        }

    @property
    def msc_urls(self):
        return self.data["msc_vending"]["urls"]

    # Setter methods for runtime editing
    def set_admin_password(self, new_pw):
        self.data["creds"]["admin_password"] = new_pw
        self.save_config()

    def update_line_ip(self, line_name, new_ip):
        for line in self.data["line_configs"]:
            if line["name"] == line_name:
                line["ip"] = new_ip
                break
        self.save_config()

# Initialize global settings instance
cfg = Settings()