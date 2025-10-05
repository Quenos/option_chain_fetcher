# Folder Structure

## Overview
The project organizes data files in dedicated directories to keep the repository clean and separate code from data.

## Directory Layout

```
spx_option_chain_fetcher/
├── database/                      # SQLite database files (gitignored)
│   └── option_chain_data.db      # Main option chain database
│
├── json_exports/                  # Exported JSON files (gitignored)
│   ├── spx_options_2025-10-06_*.json
│   ├── spx_options_2025-10-07_*.json
│   └── ...
│
├── *.log                          # Log files (gitignored)
│   ├── option_chain_fetcher.log
│   └── ...
│
├── option_chain_fetcher.py        # Main data collection script
├── export_to_json.py              # JSON export script
├── query_option_data.py           # Database query helper
├── market_data.py                 # Market data interface
├── session.py                     # TastyTrade session management
│
├── OPTION_CHAIN_USAGE.md          # Usage guide
├── JSON_EXPORT_GUIDE.md           # Export documentation
├── CHANGES.md                     # Change log
│
├── requirements.txt               # Python dependencies
├── .env                           # API credentials (gitignored)
├── config.ini                     # Configuration (gitignored)
└── .gitignore                     # Git ignore rules
```

## Automatically Created Directories

The following directories are automatically created when needed:

### `database/`
- **Created by:** `option_chain_fetcher.py`
- **Purpose:** Stores SQLite database files
- **Default file:** `option_chain_data.db`
- **Git status:** Ignored (not committed)

### `json_exports/`
- **Created by:** `export_to_json.py`
- **Purpose:** Stores exported JSON files
- **Files:** One JSON file per expiration date
- **Git status:** Ignored (not committed)

## Ignored Files (.gitignore)

The following are excluded from version control:

```gitignore
# Database files
database/
*.db
*.db-journal

# JSON exports
json_exports/

# Log files
*.log
*.log.*

# Configuration
config.ini
.env
.secrets
```

## Default Paths

All scripts use these default paths (can be overridden with CLI arguments):

### option_chain_fetcher.py
```bash
--db_path database/option_chain_data.db
```

### export_to_json.py
```bash
--db_path database/option_chain_data.db
--output_dir json_exports
```

### query_option_data.py
```bash
--db_path database/option_chain_data.db
```

## Custom Paths

You can specify custom paths for any script:

```bash
# Use custom database location
python option_chain_fetcher.py \
    --max_dte 7 \
    --min_strike 5800 \
    --max_strike 6000 \
    --db_path /path/to/my/data.db

# Export to custom directory
python export_to_json.py \
    --db_path /path/to/my/data.db \
    --output_dir /path/to/exports
```

## Benefits

1. **Clean repository:** Data files don't clutter the codebase
2. **Version control:** Only code and documentation are committed
3. **Easy cleanup:** Delete entire folders to start fresh
4. **Organized:** Clear separation between code and data
5. **Portable:** Move/backup data directories independently

## Migration

If you have existing database files from previous versions:

```bash
# Create database directory
mkdir -p database

# Move existing database
mv option_chain_data.db database/

# Scripts will now find it automatically
python export_to_json.py
```
