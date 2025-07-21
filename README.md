# ZKTeco Attendance Uploader

A cross-platform desktop app to fetch, view, and upload attendance records from ZKTeco devices, with a modern web UI and easy exit functionality.

---

## Project Directory Structure

```
zk-sync/
├── app.py                # Main Flask application
├── README.md             # Project documentation
├── requirements.txt      # Python dependencies
├── templates/
│   └── index.html        # Frontend HTML (TailwindCSS + Toastify)
├── venv/                 # Python virtual environment (not tracked in git)
├── zk_utils.py           # ZKTeco device utility functions
└── ...                   # Other files
```

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd zk-sync
```

### 2. Create and Activate a Virtual Environment

#### **Windows**

```bash
python -m venv venv
venv\Scripts\activate
```

#### **Mac/Linux**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Running the App (Development)

```bash
python app.py
```

- The app will open in your default browser at [http://localhost:5000](http://localhost:5000)
- Use the web interface to connect to your ZKTeco device, fetch attendance, and upload records.
- To exit, click the red **Exit Application** button in the UI.

---

## Building Standalone Executables

### **Windows Build**

1. **Install PyInstaller**
   ```bash
   pip install pyinstaller
   ```
2. **Build the .exe**
   ```bash
   pyinstaller --onefile --windowed --add-data "templates;templates" app.py
   ```
   - The built executable will be in the `dist/` folder as `app.exe`.
   - Double-click `app.exe` to run. The app will open in your browser, and no terminal window will appear.

### **Mac Build**

1. **Build on a Mac (cannot cross-compile from Windows)**
2. **Install PyInstaller**
   ```bash
   pip install pyinstaller
   ```
3. **Build the .app bundle**
   ```bash
   pyinstaller --onefile --windowed --add-data "templates:templates" app.py
   ```
   - The built app will be in the `dist/` folder as `app.app`.
   - Double-click `app.app` to run. The app will open in your browser, and no terminal window will appear.

#### **Optional: Create a DMG for Distribution**

```bash
brew install create-dmg
create-dmg --volname "ZKTeco Attendance Uploader" --window-pos 200 120 --window-size 600 300 --icon-size 100 --icon "app.app" 175 120 --hide-extension "app.app" --app-drop-link 425 120 "ZKTeco-Attendance-Uploader.dmg" "dist/"
```

---

## Notes

- **You must build on each target OS** (Windows for .exe, Mac for .app).
- The `--add-data` flag uses `;` on Windows and `:` on Mac/Linux.
- The app will open in your default browser and can be exited using the **Exit Application** button.
- If you see any issues with missing dependencies, ensure your virtual environment is activated and all requirements are installed.

---

## Usage

1. **Connect to Device:** Enter the device IP and click Connect.
2. **Select Date Range:** Choose start and end dates.
3. **Fetch & Send:** Click to fetch attendance and upload to your backend.
4. **View Records:** Attendance records are shown in a table.
5. **Exit:** Click the red Exit Application button to close the app and server.

---
