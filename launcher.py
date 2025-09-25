#!/usr/bin/env python3
"""
Launcher script for 360 Video Player
Opens the web application and automatically opens the browser
"""

import webbrowser
import time
import threading
import sys
import os

def open_browser():
    """Open browser after a short delay"""
    time.sleep(2)  # Wait for Flask to start
    webbrowser.open('http://localhost:8080')

def main():
    # Start browser opening in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Import and run the Flask app
    from web_app import app
    print("Starting 360 Video Player...")
    print("Opening browser automatically...")
    print("If browser doesn't open, go to: http://localhost:8080")
    print("Press Ctrl+C to stop the application")
    app.run(debug=False, host='0.0.0.0', port=8080)

if __name__ == '__main__':
    main()
