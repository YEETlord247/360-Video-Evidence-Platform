# 360 Video Player - Standalone Executable

## How to Use

1. **Double-click** the `360_Video_Player.exe` file
2. Wait for the application to start (you'll see a command prompt window)
3. Your web browser will automatically open to the application
4. If the browser doesn't open automatically, go to: http://localhost:8080

## Features

- Upload and view 360-degree videos
- Interactive timeline with pins
- Export videos with custom viewing angles
- Support for equirectangular and dual-fisheye formats

## Troubleshooting

- **Antivirus Warning**: Some antivirus software may flag the executable. This is a false positive. You can safely allow it.
- **Port Already in Use**: If you get an error about port 8080 being in use, close any other applications using that port.
- **Browser Doesn't Open**: Manually navigate to http://localhost:8080 in your web browser.

## System Requirements

- Windows 10 or later
- At least 4GB RAM
- Sufficient disk space for video processing

## File Structure

The executable creates these folders automatically:
- `uploads/` - Where uploaded videos are stored
- `static/` - Web application assets
- `templates/` - Web application templates

## Stopping the Application

Press `Ctrl+C` in the command prompt window to stop the application.
