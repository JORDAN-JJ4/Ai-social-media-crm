import uvicorn
import webbrowser
import time
import threading

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    print("Starting Autonomous AI Social Media Growth Platform...")
    print("Serving on http://localhost:8000")
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
