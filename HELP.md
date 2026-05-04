# MAS-A5 ADE Multi-Line Tool Editor (MLTE) - User Guide

## Overview

The **Multi-Line Tool Editor (MLTE)** is a console-based application for managing CNC tool data across multiple production lines. It allows you to search, add, edit, and synchronize tool information in the tool crib database across Lines 1-5 and the 5-axis line.

---

## Getting Started

### Starting the Application

1. Open a terminal or command prompt
2. Navigate to the MLTE directory: `C:\Users\eweaver\Desktop\FTNXML\Python`
3. Run the application:
   ```
   python MLTE.py
   ```

**Programmer Mode** (advanced users only):
```
python MLTE.py --programmer
```

### Basic Navigation

- **UP/DOWN arrows**: Move through menu options
- **ENTER**: Select an option
- **BACKSPACE/ESC**: Go back to previous menu

---

## Main Menu Options

When you start MLTE, you'll see the main menu with these options:

### 1. **ADD a Tool**
Add a new tool to the crib. Walk through steps to:
- Select the tool category (Endmill, Drill, Tap, etc.)
- Enter tool details (diameter, type, holder, etc.)
- Specify which production lines to add it to
- Confirm before saving

### 2. **SEARCH for a Tool**
Find existing tools by:
- **Crib Item Search**: Search the Tool Crib database by item number
- **Keyword Search**: Search by tool type and characteristics
  - Endmills: Filter by subtype and diameter
  - Drills: Search by size and type
  - Taps: Find by standard or metric specifications
  - Other tools: Filter by relevant parameters

### 3. **EDIT a Tool**
Modify an existing tool:
- Search for the tool first
- Update any field (comment, holder, speed, coolant settings, etc.)
- Sync changes across lines as needed

### 4. **DELETE a Tool**
Remove a tool from the database:
- Search for the tool
- Confirm deletion
- Choose which lines to remove it from

### 5. **SYNC Multi-Line Tools**
Synchronize tool data across production lines:
- **Manual Sync**: Choose which tools to sync between lines
- **Auto Sync**: Automatically merge tool data following priority rules
- View sync status and conflicts

### 6. **CHECK for Conflicts**
Find tools with conflicting descriptions:
- Identifies tools (FTNs) that have different comments on different lines
- Helps maintain data consistency across lines

### 7. **SETTINGS**
Configure application behavior:
- Edit database credentials
- Manage line configurations
- Set sync priorities
- Configure search parameters

### 8. **EXIT**
Close the application safely

---

## Supported Tool Categories

The application supports the following tool types:

### Milling Tools
- **Square Endmills**: Flat-bottom end mills for general machining
- **Ball Endmills**: Ballnose/hemispherical end mills for contouring
- **Bullnose (Corner Radius)**: Mills with radius corners
- **Chamfer Mills**: For creating beveled edges
- **Keyseat/Woodruff Mills**: For slot and keyseat cutting

### Drilling Tools
- **Drills**: Standard jobber, stub, micro, and carbide drills
- **Spot/Center Drills**: For locating and spotting
- **Countersinks**: For creating countersink holes
- **Reamers**: For finishing holes to precise sizes

### Threading Tools
- **Taps**: For cutting internal threads
  - Available in standard and metric specifications
  - Multiple thread forms (plug, bottom, spiral)
- **Thread Mills**: For milling threads with precision control

### Special Tools
- **Lollipop/Undercut Tools**: For undercutting and spherical operations

---

## Key Features

### Intelligent Search System
The search feature uses an extensive synonym system to find tools quickly:
- **Word Synonyms**: Recognizes multiple terms (e.g., "end mill" = "endmill" = "em")
- **Part Synonyms**: Understands abbreviations (e.g., "sem" = "square endmill")
- **Smart Exclusion**: Prevents false matches (e.g., excludes "email" when searching for "endmill")
- **Auto-Filtering**: Eliminates conflicting tool types (e.g., won't return ball mills when searching for square endmills)

### Database Integration
- Connects to SQL Server databases on each production line
- Retrieves and stores tool data in the `FunctionalToolData` table
- Supports custom holder types and sizes per line
- Manages adaptive control and spindle load settings
- Tracks tool life and rotation restrictions

### Multi-Line Synchronization
- **Priority Order**: Tools are synced following a configured priority:
  - 5-axis (highest priority)
  - Line 4, Line 3, Line 5, Line 2, Line 1
- **Conflict Resolution**: Automatically selects the best data when differences exist
- **Read-Only Lines**: Some lines (like 5-axis) may be read-only to prevent overwrites
- **Selective Sync**: Choose specific tools to sync or sync all tools

### Tool Properties Managed
Each tool record includes:
- **Basic Info**: FTN (Functional Tool Number), Comment/Description
- **Physical Properties**: Diameter, Type, Length
- **Holder Info**: Type, Size, No-Rotation requirement
- **Machine Settings**: ATC Speed, Purge Time, Spindle Load
- **Cutting Parameters**: Adaptive Control value, Through-Spindle Coolant
- **Safety**: Tool Alarm Prohibit, B-axis Rotation Prohibit, One-Touch Prohibit
- **Removal**: TSC Removal Type and Frequency
- **Load Data**: Axial and Radial Maximum Cutting Load

---

## Common Workflows

### Adding a New Tool
1. Select **ADD a Tool** from main menu
2. Choose the tool category
3. Enter the tool details (prompted step-by-step)
4. Specify which production lines need this tool
5. Confirm and save

### Finding a Tool by Item Number
1. Select **SEARCH for a Tool**
2. Choose **Crib Item Search**
3. Enter the item number or part number
4. Review the results and select the tool
5. View all tool details and which lines have it

### Finding Tools by Type and Size
1. Select **SEARCH for a Tool**
2. Choose **Keyword Search**
3. Select the tool category (e.g., Endmills)
4. Specify any filters (e.g., Square endmill, 1/2" diameter)
5. Browse results and select to view details

### Updating a Tool on All Lines
1. Search for the tool (use either search method)
2. Select **EDIT** when viewing the tool
3. Update the desired field
4. Choose to sync the change across all lines
5. Confirm the update

### Resolving Tool Conflicts
1. Select **CHECK for Conflicts** from main menu
2. View list of FTNs with conflicting descriptions
3. Select a conflicting tool to review differences
4. Choose which description to keep
5. Sync the corrected version across lines

### Syncing Tools from One Line to Others
1. Select **SYNC Multi-Line Tools** from main menu
2. Choose which line to sync from
3. Select individual tools or sync all
4. Review sync summary
5. Confirm to apply changes

---

## Configuration

### config.json
Located in the main application directory, this file contains:

**Database Credentials**
- SQL Server connection details for each line
- Username and password (ensure file is protected)

**Line Configurations**
- IP addresses and database names for each production line
- Line priority order for conflict resolution

**Sync Settings**
- Read-only lines (lines that receive but don't override data)
- Priority order for multi-line sync
- Column mappings between tool data fields

**Tool Classifications**
- Sub-types for endmills (Square, Ball, Bullnose, etc.)
- Special tool sub-types
- Tap standards (metric and imperial)
- Holder types available

### Editing Settings
1. Select **SETTINGS** from main menu
2. Navigate through the settings menu using arrow keys
3. Make desired changes
4. Changes are saved automatically to config.json

---

## Advanced Features

### Programmer Mode
Run with `--programmer` flag for additional debugging and manual database operations. Not recommended for regular users.

### Breadcrumb Navigation
The yellow bar at the top of screens shows your navigation path:
- `MAIN > ADD > Endmills > 00000019` indicates you're adding an endmill with FTN 00000019
- Useful for tracking where you are in complex workflows

### Tool Crib Integration
- Search integrates with the Tool Crib database for comprehensive item lookup
- Retrieves supplier information when available
- Tracks tool inventory across the shop

---

## Tips & Tricks

1. **Quick Size Entry**: Use common formats for diameters
   - Fractions: `1/2`, `3/8`, `1/4`
   - Decimals: `.5`, `.375`, `.25`
   - Integers: `6`, `8`, `10`

2. **Tool Comments**: Keep descriptions concise and consistent
   - Use standardization to improve search accuracy
   - Add material restrictions or special notes here

3. **Sync Strategy**: Set up priority order based on
   - Which lines have the most up-to-date data
   - Production volume on each line
   - Which line has the most comprehensive tool library

4. **Batch Operations**: When adding multiple similar tools
   - Add one with full details
   - Copy settings for similar tools
   - Adjust parameters as needed

5. **Conflict Resolution**: Before syncing
   - Check which line has the most recent information
   - Review the tool's usage patterns on each line
   - Ensure the winning description is accurate

---

## Troubleshooting

### "Database Connection Failed"
- **Cause**: Network issue or incorrect credentials in config.json
- **Solution**: 
  - Check your network connection
  - Verify database credentials in Settings
  - Ensure line IP addresses are reachable
  - Contact IT if network access issues persist

### "Tool Not Found"
- **Cause**: Search term doesn't match stored description
- **Solution**:
  - Try alternative search terms (use synonyms)
  - Check spelling and capitalization
  - Search by item number if description search fails
  - Use keyword search to browse similar tools

### "Permission Denied" on Specific Line
- **Cause**: Line may be configured as read-only
- **Solution**:
  - Check Settings for read-only line configuration
  - Contact administrator to change permissions if needed
  - Add the tool to a writable line instead

### "Sync Conflicts"
- **Cause**: Same tool has different data on multiple lines
- **Solution**:
  - Use "CHECK for Conflicts" to identify issues
  - Choose the most accurate description
  - Sync the corrected version across all lines
  - Update line priority if a line consistently has better data

### "Search Returning Wrong Tools"
- **Cause**: Search terms too broad or matching unrelated tools
- **Solution**:
  - Be more specific in search criteria
  - Add additional filters (size, type, etc.)
  - Try searching by FTN directly if known

### Application Crashes
- **Solution**:
  - Ensure Python 3.8+ is installed
  - Install required packages: `pip install -r requirements.txt`
  - Check that config.json is properly formatted JSON
  - Run in Programmer Mode for additional error details

---

## Support & Resources

### Required Dependencies
- Python 3.8 or higher
- pyodbc (SQL Server connection)
- keyboard (input handling)
- readchar (terminal input)
- pyperclip (clipboard operations)

### Files Reference
- **MLTE.py** - Main application
- **CribSearch.py** - Search functionality with synonym engine
- **EditSettings.py** - Configuration editor
- **config.json** - Configuration file
- **settings.py** - Settings loader
- **sync_tool_crib.py** - Refresh Tool Crib Database
- **SyncLineTool.py** - Line-to-line sync logic
- **Standardize-Descriptions.py** - Line-to-line Standardization of Descriptions






