import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import pyodbc
import readchar
import sys
from collections import defaultdict

from MLTE import *
from settings import cfg

DB_CREDS = cfg.db_creds
LINE_CONFIGS = cfg.line_configs
READ_ONLY_LINES = cfg.read_only_lines
PRIORITY_ORDER = cfg.priority_order
MAPPING = cfg.mapping


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def header(title=""):
    clear()
    print(f"\033[1;34m--- {title.upper()} ---\033[0m")
    print("\033[90m" + "—" * 55 + "\033[0m")

def wait():
    print("\n\033[90mPress any key to continue...\033[0m")
    readchar.readkey()

def get_conflicting_ftns():
    master_map = defaultdict(set)
    # FIX: Iterate directly over the list
    for cfg_item in LINE_CONFIGS: 
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg_item['ip']},1433;DATABASE={cfg_item['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=1;")
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT [FTN], [FTNComment] FROM [dbo].[FunctionalToolData]")
                for row in cursor:
                    ftn = str(row[0]).strip()
                    comment = (row[1] or "").strip()
                    if comment: master_map[ftn].add(comment)
        except: pass
    return [ftn for ftn, comments in master_map.items() if len(comments) > 1]

def get_tool_data(tool_num):
    SCALE = 100000.0
    for name in PRIORITY_ORDER:
        # FIX: Find the config dict that matches the name in our priority list
        cfg_item = next((item for item in LINE_CONFIGS if item["name"] == name), None)
        if not cfg_item: continue
        
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg_item['ip']},1433;DATABASE={cfg_item['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=2;")
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM [dbo].[FunctionalToolData] WHERE [FTN] = ?", (int(tool_num),))
                ft_row = cursor.fetchone()
                if not ft_row: continue

                ft_cols = [col[0] for col in cursor.description]
                tool_data = dict(zip(ft_cols, ft_row))
                
                cursor.execute("SELECT * FROM [dbo].[FunctionalToolCutterData] WHERE [FTNID] = ?", (tool_data['FTNID'],))
                c_row = cursor.fetchone()
                
                if c_row:
                    c_cols = [col[0] for col in cursor.description]
                    c_dict = dict(zip(c_cols, c_row))
                    
                    # Exact Geometry Mapping & Scaling from your original script
                    tool_data['StdLength']   = c_dict.get('StandardLength', 0) / SCALE
                    tool_data['MinLength']   = c_dict.get('MinimumLength', 0) / SCALE
                    tool_data['MaxLength']   = c_dict.get('MaximumLength', 0) / SCALE
                    tool_data['StdDiameter'] = c_dict.get('StandardDiameter', 0) / SCALE
                    tool_data['MinDiameter'] = c_dict.get('MinimumDiameter', 0) / SCALE
                    tool_data['MaxDiameter'] = c_dict.get('MaximumDiameter', 0) / SCALE
                    
                    # Tool Life and Toggles
                    tool_data['Life']              = c_dict.get('ToolLife', 0)
                    tool_data['LifeWarning']       = c_dict.get('ToolLifeWarning', 0)
                    tool_data['TlType']            = c_dict.get('ToolLifeType', 0)
                    tool_data['SpindleSpeedLimit'] = c_dict.get('SpindleSpeedLimit', 0)
                    tool_data['CheckBTS']          = 1 if c_dict.get('CheckBTS') else 0
                    tool_data['OperatorCall']      = 1 if c_dict.get('OperatorCall') else 0
                    tool_data['FirstUseTool']      = 1 if c_dict.get('FirstUseTool') else 0
                    tool_data['ToolKind']          = c_dict.get('Kind', 0)
                else:
                    # Fallback for empty geometry
                    defaults = ['StdLength', 'MinLength', 'MaxLength', 'StdDiameter', 'MinDiameter', 
                                'MaxDiameter', 'Life', 'LifeWarning', 'TlType', 'SpindleSpeedLimit',
                                'CheckBTS', 'OperatorCall', 'FirstUseTool', 'ToolKind']
                    for k in defaults: tool_data[k] = 0

                return tool_data, name
        except: continue
    return None, None

def process():
    header("Network Scan")
    print("\033[90mChecking for description conflicts...\033[0m")
    exclude_list = get_conflicting_ftns()
    
    header("Tool Selection")
    target_tool = input("\033[1;97mEnter Tool Number: \033[0m").strip()
    
    if target_tool in exclude_list:
        header("Error")
        print(f"\033[91mConflict Detected: Tool {target_tool} has mismatched descriptions.\033[0m")
        print("\033[90mRun the Standardization Tool first.\033[0m")
        wait()
        return

    header("Data Sync")
    tool_data, source = get_tool_data(target_tool)
    if not tool_data:
        print(f"\033[91mNot Found: Tool {target_tool} does not exist on priority lines.\033[0m")
        wait()
        return

    print(f"Source: \033[1;34m{source}\033[0m")
    print(f"Comment: \033[38;5;51m\"{tool_data.get('FTNComment')}\"\033[0m")
    
    missing_from = []
    potential_targets = [line['name'] for line in LINE_CONFIGS 
                         if line['name'] != source and line['name'] not in READ_ONLY_LINES]

    print(f"\nChecking targets...")
    for name in potential_targets:
        # FIX: Look up the specific config for the name
        cfg_item = next((item for item in LINE_CONFIGS if item["name"] == name), None)
        try:
            conn_str = (f"DRIVER={{SQL Server}};SERVER={cfg_item['ip']},1433;DATABASE={cfg_item['db']};"
                        f"UID={DB_CREDS['uid']};PWD={DB_CREDS['pwd']};Connection Timeout=1;")
            with pyodbc.connect(conn_str) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM [dbo].[FunctionalToolData] WHERE [FTN] = ?", (int(target_tool),))
                if not cursor.fetchone():
                    print(f"  - {name}: \033[1;33mMISSING\033[0m")
                    missing_from.append(name)
                else:
                    print(f"  - {name}: \033[90mEXISTS\033[0m")
        except:
            print(f"  - {name}: \033[91mOFFLINE\033[0m")

    if not missing_from:
        print(f"\n\033[92mTool is already present on all writable targets.\033[0m")
        wait()
        return

    print(f"\n\033[1;97mSynchronize to {len(missing_from)} lines? (y/n)\033[0m")
    if readchar.readkey().lower() != 'y': return

    # XML Generation
    root = ET.Element("MASData")
    ft_group = ET.SubElement(root, "FunctionalTools")
    tool_el = ET.SubElement(ft_group, "FunctionalTool", {"action": "ADD", "number": str(target_tool).zfill(8)})

    # 1. Functional Data
    for sql_col, xml_tag in MAPPING.items():
        val = tool_data.get(sql_col, "0")
        if isinstance(val, bool): val = "1" if val else "0"
        ET.SubElement(tool_el, xml_tag).text = str(val if val is not None else "0")

    # 2. Cutter Data (Full dataset)
    cutter_el = ET.SubElement(tool_el, "Cutter", {"number": "1"})
    c_fields = ["Kind", "StdLength", "MinLength", "MaxLength", "StdDiameter", "MinDiameter", "MaxDiameter", 
                "Life", "LifeWarning", "TlType", "SpindleSpeedLimit", "CheckBTS", "OperatorCall", "FirstUseTool"]

    for field in c_fields:
        db_field = "ToolKind" if field == "Kind" else field
        val = tool_data.get(db_field, "0")
        ET.SubElement(cutter_el, field).text = str(val if val is not None else "0")

    xml_str = minidom.parseString(ET.tostring(root, 'utf-8')).toprettyxml(indent="  ")

    header("Deployment Result")
    for name in missing_from:
        # FIX: Retrieve the path from the correct dictionary in the list
        cfg_item = next((item for item in LINE_CONFIGS if item["name"] == name), None)
        if not cfg_item: continue
        
        path = cfg_item['path']
        try:
            with open(os.path.join(path, f"Sync_{target_tool}.xml"), "w") as f:
                f.write(xml_str)
            print(f"[\033[92mSUCCESS\033[0m] Deployment to {name}")
        except Exception as e:
            print(f"[\033[91mFAILED\033[0m] {name}: {e}")

    wait()

if __name__ == "__main__":
    try:
        process()
    except KeyboardInterrupt:
        sys.exit()