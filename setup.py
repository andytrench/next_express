import os
import subprocess
import sys
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and handle errors"""
    try:
        subprocess.run(cmd, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"Error running command {' '.join(cmd)}: {e}")
        sys.exit(1)

def setup_environment():
    print("Setting up development environment...")
    
    # Create Python virtual environment if it doesn't exist
    if not os.path.exists('.venv'):
        print("Creating Python virtual environment...")
        run_command([sys.executable, '-m', 'venv', '.venv'])
    
    # Determine pip path based on OS
    pip_path = str(Path('.venv/Scripts/pip' if os.name == 'nt' else '.venv/bin/pip'))
    
    # Upgrade pip
    print("Upgrading pip...")
    run_command([pip_path, 'install', '--upgrade', 'pip'])
    
    # Install Python dependencies
    print("Installing Python dependencies...")
    run_command([pip_path, 'install', '-r', 'requirements.txt'])
    
    # Check if Node.js is installed
    try:
        subprocess.run(['node', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Node.js not found. Please install Node.js (version 20+) from https://nodejs.org/")
        sys.exit(1)
    
    # Check if npm is installed
    try:
        subprocess.run(['npm', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("npm not found. Please install Node.js which includes npm")
        sys.exit(1)
    
    # Install global Node.js dependencies
    print("Installing global Node.js dependencies...")
    global_deps = [
        'next@latest',
        'create-next-app@latest',
        'typescript@latest',
        'shadcn-ui@latest'
    ]
    run_command(['npm', 'install', '-g'] + global_deps)
    
    print("\nVerifying installations...")
    try:
        # Verify Python environment
        run_command([pip_path, 'list'])
        
        # Verify Node.js installations
        run_command(['node', '--version'])
        run_command(['npm', '--version'])
        run_command(['npm', 'list', '-g', '--depth=0'])
        
        print("\nEnvironment setup complete! 🚀")
        print("\nTo activate the virtual environment:")
        if os.name == 'nt':
            print("    .venv\\Scripts\\activate")
        else:
            print("    source .venv/bin/activate")
        
        print("\nTo start Next Express:")
        print("    python next_express.py")
        
    except Exception as e:
        print(f"Error during verification: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        setup_environment()
    except KeyboardInterrupt:
        print("\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Setup failed: {e}")
        sys.exit(1)