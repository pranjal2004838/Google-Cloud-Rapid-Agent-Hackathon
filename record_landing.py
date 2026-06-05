import os
import sys
import time
import subprocess
import webbrowser
import threading

# Helper to automatically install dependencies if missing
def install_dependencies():
    required = ["mss", "opencv-python", "numpy", "pyautogui"]
    missing = []
    for pkg in required:
        try:
            if pkg == "opencv-python":
                import cv2
            else:
                __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"Missing required packages: {missing}. Installing them now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print("All packages installed successfully!")

install_dependencies()

import cv2
import numpy as np
import pyautogui
import mss

def start_server():
    print("Starting FastAPI server...")
    # Start uvicorn in the workspace directory (which contains cliniqai)
    # We run it as a subprocess
    cwd = os.path.dirname(os.path.abspath(__file__))
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "cliniqai.agent.server:app", "--port", "8000", "--host", "127.0.0.1"],
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return server_process

def record_screen(duration_seconds=30, fps=20, output_name="cliniqai_landing_scroll.mp4"):
    print("Preparing screen recording...")
    # Get primary monitor details
    with mss.mss() as sct:
        monitor = sct.monitors[1] # 1 is primary monitor
        width = monitor["width"]
        height = monitor["height"]
        monitor_area = {
            "top": monitor["top"],
            "left": monitor["left"],
            "width": width,
            "height": height
        }
        
    print(f"Screen resolution: {width}x{height}")
    
    # Define the codec and create VideoWriter object
    # On Windows, 'mp4v' or 'XVID' work well for .mp4 or .avi
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_name, fourcc, fps, (width, height))
    
    # Wait for the browser to open and load
    print("Opening browser in 3 seconds... Click on the browser window to focus it if needed.")
    time.sleep(3)
    webbrowser.open("http://127.0.0.1:8000/")
    
    # Wait for page load
    print("Waiting 6 seconds for page to load and settle...")
    time.sleep(6)
    
    # Position mouse in the center of the screen and click to focus browser
    print("Focusing browser window...")
    pyautogui.moveTo(width // 2, height // 2)
    pyautogui.click()
    time.sleep(1)
    
    print(f"Recording started. Will record for {duration_seconds} seconds...")
    
    start_time = time.time()
    frame_delay = 1.0 / fps
    total_frames = duration_seconds * fps
    
    # Scroll delay: scroll a bit every few frames to simulate smooth scrolling
    scroll_amount = -2  # Negative is scroll down
    
    with mss.mss() as sct:
        for i in range(total_frames):
            frame_start = time.time()
            
            # Capture screen
            img = sct.grab(monitor_area)
            # Convert to numpy array
            frame = np.array(img)
            # mss returns BGRA, convert to BGR for VideoWriter
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            # Write frame to video file
            out.write(frame)
            
            # Slowly scroll down
            # Scroll every frame for maximum smoothness
            pyautogui.scroll(scroll_amount)
            
            # Control frame rate
            elapsed = time.time() - frame_start
            sleep_time = frame_delay - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
                
            if i % fps == 0:
                print(f"Recorded {i // fps} / {duration_seconds} seconds...")
                
    # Release everything
    out.release()
    print("Recording finished. Video saved as:", output_name)

if __name__ == "__main__":
    server_proc = None
    try:
        # Start local FastAPI server
        server_proc = start_server()
        # Wait a bit for server to spin up
        time.sleep(3)
        
        # Start recording and scrolling
        record_screen(duration_seconds=30, fps=20, output_name="cliniqai_landing_scroll.mp4")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if server_proc:
            print("Stopping FastAPI server...")
            server_proc.terminate()
            server_proc.wait()
            print("FastAPI server stopped.")
