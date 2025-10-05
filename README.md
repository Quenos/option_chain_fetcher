# SPX Option Chain Fetcher

A powerful tool to fetch SPX option chain data including Greeks (delta, gamma, theta, vega, rho), bid/ask quotes, and underlying prices. Data is stored in SQLite and can be exported to JSON for analysis.

## 📋 Table of Contents

- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
  - [Step 1: Install Python](#step-1-install-python)
  - [Step 2: Download the Code](#step-2-download-the-code)
  - [Step 3: Install Dependencies](#step-3-install-dependencies)
  - [Step 4: Setup Tastytrade API Access](#step-4-setup-tastytrade-api-access)
- [Quick Start](#-quick-start)
- [Documentation](#-documentation)
- [License](#-license)

---

## ✨ Features

- **Comprehensive Data Collection**: Fetches options data for SPX (monthly/quarterly) and SPXW (weekly) automatically
- **Full Greeks**: Delta, gamma, theta, vega, and rho for all options
- **Market Quotes**: Real-time bid/ask prices and calculated mid prices
- **Underlying Price Tracking**: Records SPX price at the time of each data fetch
- **SQLite Database**: Organized storage with indexing for fast queries
- **JSON Export**: Export data to well-structured JSON files for analysis
- **Flexible Filtering**: Filter by expiration date, strike range, and delta range
- **Command-Line Interface**: Easy to use and automate

---

## 📦 Prerequisites

- A Tastytrade account (with API access enabled)
- Internet connection
- Computer running macOS or Windows

---

## 🚀 Installation

### Step 1: Install Python

Python is the programming language this tool is written in. You need to install it first.

#### **For macOS Users:**

1. **Open Terminal**
   - Press `Command (⌘) + Space` to open Spotlight
   - Type `Terminal` and press Enter

2. **Check if Python is already installed**
   ```bash
   python3 --version
   ```
   - If you see something like `Python 3.11.x` or higher, you already have Python! Skip to Step 2.
   - If not, continue below.

3. **Install Python using Homebrew** (recommended method)
   
   First, install Homebrew if you don't have it:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   
   Then install Python:
   ```bash
   brew install python
   ```

4. **Verify installation**
   ```bash
   python3 --version
   ```
   You should see `Python 3.11.x` or higher.

**Alternative for macOS**: Download the installer from [python.org](https://www.python.org/downloads/macos/) and run it.

---

#### **For Windows Users:**

1. **Download Python**
   - Go to [python.org](https://www.python.org/downloads/windows/)
   - Click on the latest **Python 3.x** version (e.g., Python 3.12.x)
   - Download the "Windows installer (64-bit)"

2. **Run the Installer**
   - Double-click the downloaded file
   - ⚠️ **IMPORTANT**: Check the box that says **"Add Python to PATH"** at the bottom
   - Click **"Install Now"**
   - Wait for installation to complete
   - Click **"Close"**

3. **Verify Installation**
   - Press `Windows Key + R`
   - Type `cmd` and press Enter
   - In the command prompt, type:
   ```bash
   python --version
   ```
   You should see `Python 3.11.x` or higher.

---

### Step 2: Download the Code

#### **Option A: Download ZIP File (Easiest - No GitHub Account Required)**

1. Go to [https://github.com/Quenos/option_chain_fetcher](https://github.com/Quenos/option_chain_fetcher)
   - **No login required** - the repository is public
2. Click the green **"Code"** button (near the top right)
3. Click **"Download ZIP"**
4. Extract the ZIP file to a folder on your computer
   - **macOS**: Double-click the ZIP file
   - **Windows**: Right-click the ZIP file → "Extract All"
5. Remember where you extracted it (e.g., `Documents/option_chain_fetcher`)

#### **Option B: Clone with Git (Advanced)**

If you have Git installed:

```bash
git clone https://github.com/Quenos/option_chain_fetcher.git
cd option_chain_fetcher
```

---

### Step 3: Install Dependencies

Dependencies are additional Python packages this tool needs to work.

#### **For macOS:**

1. **Open Terminal**
2. **Navigate to the project folder**
   ```bash
   cd /path/to/option_chain_fetcher
   ```
   Replace `/path/to/` with the actual path where you extracted the files.
   
   Example:
   ```bash
   cd ~/Documents/option_chain_fetcher
   ```

3. **Install required packages**
   ```bash
   pip3 install -r requirements.txt
   ```
   This will take a minute or two. Wait for it to complete.

#### **For Windows:**

1. **Open Command Prompt**
   - Press `Windows Key + R`
   - Type `cmd` and press Enter

2. **Navigate to the project folder**
   ```bash
   cd C:\path\to\option_chain_fetcher
   ```
   Replace `C:\path\to\` with the actual path where you extracted the files.
   
   Example:
   ```bash
   cd C:\Users\YourName\Documents\option_chain_fetcher
   ```

3. **Install required packages**
   ```bash
   pip install -r requirements.txt
   ```
   This will take a minute or two. Wait for it to complete.

---

### Step 4: Setup Tastytrade API Access

To fetch option data, you need to set up API access with your Tastytrade account.

**📚 Follow the detailed tutorial**: [OAUTH_SETUP_TUTORIAL.md](OAUTH_SETUP_TUTORIAL.md)

**Quick Overview:**

1. **Log in to Tastytrade** → [https://trade.tastytrade.com/](https://trade.tastytrade.com/)
2. **Navigate to**: Manage → My Profile → API
3. **Enable API Access** (if not already enabled)
4. **Create a new OAuth Grant**:
   - **Redirect URI**: `http://localhost:8000` (exactly)
   - **Permission**: Select **"Read"** only (⚠️ do NOT select "Trade")
5. **Copy your Client ID and Client Secret** (save them immediately!)
6. **Run the setup script**:
   
   **macOS:**
   ```bash
   python3 get_refresh_token.py
   ```
   
   **Windows:**
   ```bash
   python get_refresh_token.py
   ```

7. **Follow the prompts** to complete authentication

The script will create a `.secrets` file with your credentials. Keep this file safe and never share it!

For detailed step-by-step instructions with screenshots, see [OAUTH_SETUP_TUTORIAL.md](OAUTH_SETUP_TUTORIAL.md).

---

## 🎯 Quick Start

### Fetch Option Data

**macOS:**
```bash
python3 option_chain_fetcher.py --max_dte 7 --min_strike 5800 --max_strike 6000
```

**Windows:**
```bash
python option_chain_fetcher.py --max_dte 7 --min_strike 5800 --max_strike 6000
```

This fetches options expiring in the next 7 days with strikes between 5800 and 6000.

### Export to JSON

**macOS:**
```bash
python3 export_to_json.py
```

**Windows:**
```bash
python export_to_json.py
```

This exports the latest data to JSON files in the `json_exports/` folder.

### Clear Database

**macOS:**
```bash
python3 option_chain_fetcher.py --clear_db
```

**Windows:**
```bash
python option_chain_fetcher.py --clear_db
```

---

## 📚 Documentation

For detailed documentation, see:

- **[OPTION_CHAIN_USAGE.md](OPTION_CHAIN_USAGE.md)** - Complete usage guide for the data fetcher
- **[JSON_EXPORT_GUIDE.md](JSON_EXPORT_GUIDE.md)** - How to export and work with JSON files
- **[OAUTH_SETUP_TUTORIAL.md](OAUTH_SETUP_TUTORIAL.md)** - Step-by-step API setup guide
- **[SPX_HANDLING_NOTES.md](SPX_HANDLING_NOTES.md)** - Understanding SPX vs SPXW
- **[CHANGES.md](CHANGES.md)** - Project changelog and technical details

### Key Features Explained

#### Database Structure

The tool creates a SQLite database with two tables:

1. **option_chain_data**: All option data with Greeks and quotes
2. **underlying_prices**: SPX price at the time of each fetch

#### SPX/SPXW Handling

When you specify `--symbol SPX` or `--symbol SPXW`, the tool automatically fetches **both**:
- **SPX**: Monthly/quarterly expirations
- **SPXW**: Weekly expirations

This gives you complete market coverage in a single run!

#### Export Options

Filter your exports by:
- Expiration date range
- Strike price range
- Delta range
- Specific expiration date

Example:
```bash
# macOS
python3 export_to_json.py --start_date 2025-10-06 --end_date 2025-10-10 --min_delta 0.25 --max_delta 0.45

# Windows
python export_to_json.py --start_date 2025-10-06 --end_date 2025-10-10 --min_delta 0.25 --max_delta 0.45
```

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ⚠️ Disclaimer

This tool is for educational and research purposes only. It provides market data but does not execute trades. Always verify data independently before making trading decisions.

---

## 🆘 Support

If you encounter issues:

1. Check the [OAUTH_SETUP_TUTORIAL.md](OAUTH_SETUP_TUTORIAL.md) troubleshooting section
2. Review the log file: `option_chain_fetcher.log`
3. Open an issue on GitHub with:
   - Your operating system (macOS/Windows)
   - Python version (`python --version` or `python3 --version`)
   - Error messages from the log file

---

## 🎉 You're All Set!

Once you've completed the installation steps above, you're ready to start fetching SPX option data!

**First run command:**

**macOS:**
```bash
cd ~/Documents/option_chain_fetcher
python3 option_chain_fetcher.py --max_dte 7 --min_strike 5800 --max_strike 6000
```

**Windows:**
```bash
cd C:\Users\YourName\Documents\option_chain_fetcher
python option_chain_fetcher.py --max_dte 7 --min_strike 5800 --max_strike 6000
```

Happy trading! 📈
