import subprocess
import sys
import time

def install_dependencies():
    print("=" * 50)
    print("HYDRO-RISK DEPENDENCY INSTALLER")
    print("=" * 50)
    print("Bypassing Windows file locks and clearing cache...\n")
    
    try:
        # Using --no-cache-dir solves the WinError 32 lock issue
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "--no-cache-dir", "rasterio", "python-dotenv"
        ])
        print("\n[SUCCESS] Dependencies installed successfully!")
        print("You can now start the backend with: python api.py")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Installation failed. Please check your internet connection. Details: {e}")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")

if __name__ == "__main__":
    install_dependencies()
    time.sleep(5)
