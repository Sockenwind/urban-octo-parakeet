# CleanDrive - USB & External Drive Cleaner

A simple Python GUI tool for macOS to automatically remove `.DS_Store` and `._` (AppleDouble) files from external drives (USB keys, SD cards, network shares).

## Features
- **Auto-detection**: Automatically finds mounted external volumes in `/Volumes`.
- **Safety**: "Preview" mode (Dry Run) to see what will be deleted before it happens.
- **Cleaning**: Removes annoying metadata files that clutter non-Mac filesystems.

## Prerequisites
- macOS
- Python 3.x
- Tkinter (usually included with Python)

## Installation & Running from Source

1. Clone or download this repository.
2. Open a terminal and navigate to the folder.
3. Run the application:
   ```bash
   export PYTHONPATH=$PYTHONPATH:.
   python3 src/main.py
   ```

## Building Standalone App

To create a standalone `.app` bundle that you can put in your Applications folder:

1. Ensure you have `pip` installed.
2. Run the build script:
   ```bash
   chmod +x build_app.sh
   ./build_app.sh
   ```
3. The application will be created in the `dist/` folder. You can move `CleanDrive.app` to your Applications folder.

## Usage

1. **Launch the app.** It will list detected external drives.
2. **Select Drives.** By default, all found external drives are selected. Uncheck any you want to skip.
3. **Preview.** Click "Preview Scan (Dry Run)" to see a log of files that would be deleted. No files are touched.
4. **Clean.** Click "Clean Selected Drives" to permanently remove the files.

## License
MIT
