# Windows Executable Build Instructions

## For Your Coworker's Windows PC

### Option 1: Build on Windows (Recommended)

1. **Copy your project to a Windows computer** (or use a Windows virtual machine)
2. **Open Command Prompt** as Administrator
3. **Navigate to your project folder**
4. **Run the build script:**
   ```
   build_windows.bat
   ```
5. **Find the executable** in the `dist\` folder: `360_Video_Player.exe`

### Option 2: Use Cross-Compilation (Advanced)

If you want to build the Windows .exe from your Mac:

1. **Install Wine** (for running Windows tools on Mac)
2. **Install Python for Windows** via Wine
3. **Use the same PyInstaller command** but with Wine

### What the Executable Does

When your coworker double-clicks the `360_Video_Player.exe`:

1. **Opens a command prompt window** (this is normal)
2. **Starts the Flask web server** on localhost:8080
3. **Automatically opens their web browser** to http://localhost:8080
4. **Shows the exact same interface** as your current web app
5. **No Python installation required** on their computer

### File Size

The executable will be approximately **100-200MB** because it includes:
- Python runtime
- All dependencies (OpenCV, Flask, NumPy, etc.)
- Your web application code
- Templates and static files

### Distribution

Simply send the `.exe` file to your coworker. They can:
- Double-click to run
- No installation required
- No Python needed
- Works on any Windows 10/11 computer

### Troubleshooting

- **Antivirus Warning**: Some antivirus software may flag the executable. This is normal for PyInstaller apps. You can safely allow it.
- **Port 8080 in Use**: If they get an error, they can manually go to http://localhost:8080 in their browser
- **First Run Slow**: The first run takes longer as it extracts the bundled files

### Current Status

✅ **Launcher script created** - Opens browser automatically  
✅ **Build script created** - Ready for Windows compilation  
✅ **All dependencies included** - No external requirements  
✅ **Same interface** - Exact replica of your current web app  

**Next Step**: Build on a Windows machine using `build_windows.bat` 