import sys
import os
import subprocess
import time

def main():
    print("🚀 Starting both Flask applications...")
    
    # Paths to subdirectories
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pysql_dir = os.path.join(base_dir, 'pysql_manager')
    employee_dir = os.path.join(base_dir, 'employee_manager')
    
    # Using sys.executable to run with the active Python interpreter (venv)
    python_bin = sys.executable
    
    processes = []
    try:
        # Start PySQLManager
        print("  -> Starting PySQLManager on http://localhost:5000...")
        pysql_proc = subprocess.Popen(
            [python_bin, 'app.py'],
            cwd=pysql_dir
        )
        processes.append(pysql_proc)
        
        # Start Employee Manager
        print("  -> Starting Employee Manager on http://localhost:5002...")
        employee_proc = subprocess.Popen(
            [python_bin, 'employee_app.py'],
            cwd=employee_dir
        )
        processes.append(employee_proc)
        
        print("\n⚡ Both servers are running. Press Ctrl+C to stop them.\n")
        
        # Wait for processes
        while True:
            time.sleep(1)
            # Check if any process terminated early
            for p in processes:
                if p.poll() is not None:
                    print(f"⚠️ Process {p.args} exited with code {p.returncode}")
                    raise SystemExit
                    
    except KeyboardInterrupt:
        print("\n🛑 Stopping all servers...")
    finally:
        for p in processes:
            if p.poll() is None:
                print(f"  -> Terminating process: {p.args}")
                p.terminate()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    print(f"  -> Killing unresponsive process: {p.args}")
                    p.kill()
        print("✅ Servers shut down cleanly.")

if __name__ == '__main__':
    main()
