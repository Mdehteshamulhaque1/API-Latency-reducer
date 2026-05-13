#!/usr/bin/env python3
"""
MySQL setup helper - creates database and user if needed.
Run with: python setup_mysql.py
"""
import subprocess
import sys

def run_command(cmd, description):
    """Run shell command and show output."""
    print(f"\n📝 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Success: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def setup_mysql():
    """Setup MySQL database for the project."""
    print("🔧 MySQL Setup Helper")
    print("=" * 50)
    
    print("\n1️⃣  Checking MySQL connectivity...")
    
    # Test basic connection
    if not run_command(
        'powershell -Command "mysql -u root -e \\"SELECT 1\\"" 2>&1',
        "Testing MySQL connection as root"
    ):
        print("\n⚠️  MySQL root connection failed. Options:")
        print("   a) If you don't have MySQL root access, provide new credentials below")
        print("   b) If MySQL is not running, start it first")
        
        # Alternative: try different credentials
        username = input("\n   Enter MySQL username (default: root): ").strip() or "root"
        password = input("   Enter MySQL password (default: password): ").strip() or "password"
        
        print(f"\n2️⃣  Attempting connection with {username}...")
        if not run_command(
            f'powershell -Command "mysql -u {username} -p{password} -e \\"SELECT 1\\"" 2>&1',
            f"Testing connection as {username}"
        ):
            print("\n❌ Could not connect to MySQL with provided credentials.")
            print("   Please verify MySQL is running and credentials are correct.")
            return False
        
        # Update .env file
        print("\n3️⃣  Updating .env with new credentials...")
        with open(".env", "r") as f:
            content = f.read()
        
        old_url = f"mysql+aiomysql://root:password@localhost:3306/api_optimizer"
        new_url = f"mysql+aiomysql://{username}:{password}@localhost:3306/api_optimizer"
        content = content.replace(old_url, new_url)
        
        with open(".env", "w") as f:
            f.write(content)
        
        print(f"✅ Updated .env with {username}:{password}")
    
    print("\n4️⃣  Creating database...")
    if not run_command(
        'powershell -Command "mysql -u root -e \\"CREATE DATABASE IF NOT EXISTS api_optimizer;\\"" 2>&1',
        "Creating api_optimizer database"
    ):
        # Try with alt credentials
        username = input("Enter MySQL username: ").strip() or "root"
        password = input("Enter MySQL password: ").strip() or "password"
        run_command(
            f'powershell -Command "mysql -u {username} -p{password} -e \\"CREATE DATABASE IF NOT EXISTS api_optimizer;\\"" 2>&1',
            f"Creating database as {username}"
        )
    
    print("\n✅ MySQL setup complete!")
    print("\nNext step: Run 'python migrate_db.py' to create tables")
    return True

if __name__ == "__main__":
    setup_mysql()
