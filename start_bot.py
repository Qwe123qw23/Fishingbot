#!/usr/bin/env python3
import os
import sys
import subprocess
import time

# Layihə qovluğuna keçmək
project_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(project_dir)

# Virtual environment aktivləşdirmək və serveri başlatmaq
def start_server():
    try:
        print("🚀 Phishing Bot serveri başladılır...")
        
        # Virtual environment-i aktivləşdirmək
        venv_python = os.path.join(project_dir, 'venv', 'bin', 'python')
        main_script = os.path.join(project_dir, 'src', 'main.py')
        
        if not os.path.exists(venv_python):
            print("❌ Virtual environment tapılmadı!")
            return False
            
        if not os.path.exists(main_script):
            print("❌ main.py faylı tapılmadı!")
            return False
        
        # Serveri başlatmaq
        print("📡 Server başladılır...")
        subprocess.run([venv_python, main_script], check=True)
        
    except KeyboardInterrupt:
        print("\n⏹️ Server dayandırıldı.")
    except Exception as e:
        print(f"❌ Xəta: {e}")
        return False
    
    return True

if __name__ == "__main__":
    start_server()

