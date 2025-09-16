#!/usr/bin/env python3
"""
Dependency checker for Institute Management System
Run this to verify all dependencies are installed correctly
"""

import sys
import subprocess

def check_python_version():
    """Check if Python version is compatible"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Python 3.7+ is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_package(package_name, import_name=None):
    """Check if a package is installed and can be imported"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"✅ {package_name}")
        return True
    except ImportError:
        print(f"❌ {package_name} - Not installed")
        return False

def install_package(package):
    """Install a package using pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def main():
    print("🔍 Checking Institute Management System Dependencies...\n")
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Required packages
    packages = [
        ("Flask==2.3.3", "flask"),
        ("Flask-SQLAlchemy==3.1.1", "flask_sqlalchemy"), # Not in install-dependencies.bat
        ("Flask-CORS==4.0.0", "flask_cors"),
        ("PyJWT==2.8.0", "jwt"),
        ("bcrypt==4.1.2", "bcrypt"),
        ("python-dotenv==1.0.1", "dotenv"),
        ("python-dateutil==2.8.2", "dateutil") # Not in install-dependencies.bat
    ]
    
    print("\n📦 Checking packages:")
    missing_packages = []
    
    for package, import_name in packages:
        if not check_package(package.split("==")[0], import_name):
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ {len(missing_packages)} packages missing")
        print("\n🔧 To install missing packages, run:")
        for package in missing_packages:
            print(f"   pip install {package}")
        
        print("\n🚀 Or run the complete setup:")
        print("   pip install -r requirements.txt")
        
        # Ask if user wants to auto-install
        try:
            response = input("\n❓ Install missing packages now? (y/n): ").lower()
            if response == 'y':
                print("\n📥 Installing packages...")
                for package in missing_packages:
                    print(f"Installing {package}...")
                    if install_package(package):
                        print(f"✅ {package} installed")
                    else:
                        print(f"❌ Failed to install {package}")
        except KeyboardInterrupt:
            print("\n\n👋 Installation cancelled")
            sys.exit(1)
    else:
        print("\n✅ All dependencies are installed!")
        print("\n🚀 You can now run: python app.py")

if __name__ == "__main__":
    main()
