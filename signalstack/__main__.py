"""Start the local UI and independent scheduler together."""
import subprocess
import sys
from signalstack.db import ROOT

def main():
    scheduler=subprocess.Popen([sys.executable,'-m','signalstack.scheduler'],cwd=ROOT)
    ui=None
    try:
        ui=subprocess.Popen([sys.executable,'-m','streamlit','run','app.py','--server.address','127.0.0.1','--server.headless','true'],cwd=ROOT)
        print('Signal Stack: http://127.0.0.1:8501 — Ctrl+C stops both services.',flush=True)
        ui.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for process in (ui,scheduler):
            if process and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill()

if __name__=='__main__': main()
