#!/usr/bin/env python3
"""
Setup script for Azure Terraform MCP Server.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"➤ {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def main():
    """Main setup function."""
    print("🚀 Setting up Azure Terraform MCP Server...")
    
    # Check Python version
    if sys.version_info < (3, 11):
        print("❌ Python 3.11 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python version: {sys.version}")
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Install the package in development mode
    if not run_command("pip install -e .", "Installing package in development mode"):
        print("❌ Failed to install package")
        sys.exit(1)
    
    # Check if optional dependencies are available
    print("\n📦 Checking optional dependencies...")
    
    try:
        import bs4
        print("✅ BeautifulSoup4 is available")
    except ImportError:
        print("⚠️  BeautifulSoup4 not available - HTML parsing will be limited")
        print("   Install with: pip install beautifulsoup4")
    
    # Validate the installation
    print("\n🔍 Validating installation...")
    
    try:
        from src.core.config import Config
        from src.core.server import create_server
        print("✅ Core modules imported successfully")
        
        # Test configuration
        config = Config.from_env()
        print(f"✅ Configuration loaded: {config.server.host}:{config.server.port}")
        
        # Test server creation
        server = create_server(config)
        print("✅ Server created successfully")
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(1)
    
    print("\n🎉 Setup completed successfully!")
    print("\n📚 Quick start:")
    print("   1. Set environment variables (optional):")
    print("      export ARM_SUBSCRIPTION_ID=your-subscription-id")
    print("      export ARM_TENANT_ID=your-tenant-id")
    print("   2. Run the server:")
    print("      python -m tf_mcp_server")
    print("   3. Or use the new main script:")
    print("      python main_new.py")
    
    print("\n📖 For more information, see README.md")


if __name__ == "__main__":
    main()
