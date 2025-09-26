
# CSV Compare & Modify Flask App

This app lets you upload, compare, deduplicate, split, and modify CSV files with a modern web interface.

## Quick Start on a New Laptop

### 1. Prerequisites
 - Install Python 3.8 or newer from [python.org](https://www.python.org/downloads/)
 - On Windows, during installation, check the box "Add Python to PATH" on the first installer screen.
    - If you missed this step, you can add Python to PATH manually:
       1. Open the Start menu and search for "Environment Variables".
       2. Click "Edit the system environment variables".
       3. In the System Properties window, click "Environment Variables...".
       4. Under "System variables", find and select "Path", then click "Edit".
       5. Click "New" and add the path to your Python installation (e.g., `C:\Users\YourName\AppData\Local\Programs\Python\Python3x`).
       6. Also add the `Scripts` folder (e.g., `C:\Users\YourName\AppData\Local\Programs\Python\Python3x\Scripts`).
       7. Click OK to save and close all dialogs.
       8. Restart your terminal or computer for changes to take effect.
    - Disable App Execution Aliases for Python (Windows 10/11):
       1. Open Windows Settings.
       2. Go to "Apps" > "App execution aliases".
       3. Find `python.exe` and `python3.exe` in the list.
       4. Turn OFF the toggles for both.
       5. This ensures the `python` command uses your installed Python, not the Microsoft Store alias.

### 2. Clone or Copy the Project
- You can download or clone the project folder to your laptop.
- Recommended: Use GitHub Desktop for easy cloning:
   1. Download and install GitHub Desktop from https://desktop.github.com/
   2. Open GitHub Desktop and sign in to your GitHub account.
   3. Click "File" > "Clone repository..."
   4. Enter the repository URL or select it from your list.
   5. Choose a local path (e.g., `C:\Custom Software\csv_compare_flask`) and click "Clone".
   6. The project will be downloaded to your laptop and ready for use.
- Alternatively, you can use the command line:
   `git clone https://github.com/yourusername/your-repo-name.git`

   - If prompted for your GitHub username and password (or personal access token), enter them to complete the clone process.

### 3. Install Dependencies
- Open a terminal (Windows: PowerShell, macOS/Linux: Terminal)
- Navigate to the project folder:
   - Windows: `cd "C:\Custom Software\csv_compare_flask"`
   - macOS/Linux: `cd ~/path/to/csv_compare_flask`
- Run the setup script:
   - Windows: `setup.bat`
   - macOS/Linux: `bash setup.sh`
- This will install all required Python packages (Flask, pandas, openpyxl, etc.)

### 4. Run the App
- In the terminal, run:
   - Windows: `flask run`
   - macOS/Linux: `flask run`
- By default, the app will be available at [http://127.0.0.1:5000](http://127.0.0.1:5000)

### 5. Using the App
- Open your browser and go to [http://127.0.0.1:5000](http://127.0.0.1:5000)
- Use the sidebar/menu to:
   - Upload CSV files
   - Compare and deduplicate data
   - Split CSVs
   - Modify columns (keep, delete, change values, format dates, concatenate, etc.)
   - Download results

### 6. Notes
- Temporary CSV files are cleaned up automatically.
- All dependencies are managed via `requirements.txt`.
- For advanced features, see the web UI or ask for help.

## Troubleshooting
- If you see errors about missing Python, ensure Python 3 is installed and added to PATH.
- If you see missing package errors, rerun the setup script.
- For port conflicts, change the port with `flask run --port 5001` (or any free port).

## Contact & Support
- For questions or issues, contact your project administrator or developer.
