#!/usr/bin/env python3
"""Setup verification script for Clawbot"""
import os
import sys
from pathlib import Path


def check_dependencies():
    """Check if all required dependencies are installed"""
    print("Checking dependencies...")
    required_packages = [
        'fastapi',
        'uvicorn',
        'google-auth',
        'google-auth-oauthlib',
        'google-api-python-client',
        'pydantic',
        'python-dotenv'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✓ {package}")
        except ImportError:
            print(f"  ✗ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("Install them with: pip install -r requirements.txt")
        return False
    
    print("\n✓ All dependencies installed")
    return True


def check_env_file():
    """Check if .env file exists and has required variables"""
    print("\nChecking environment configuration...")
    env_file = Path('.env')
    
    if not env_file.exists():
        print("  ✗ .env file not found")
        print("  Create it by copying .env.example: cp .env.example .env")
        return False
    
    print("  ✓ .env file exists")
    
    # Check for required variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'GOOGLE_REDIRECT_URI'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.startswith('your_'):
            print(f"  ✗ {var} not set or using placeholder")
            missing_vars.append(var)
        else:
            print(f"  ✓ {var} is set")
    
    if missing_vars:
        print(f"\n❌ Missing or invalid environment variables: {', '.join(missing_vars)}")
        print("  Update .env file with your Google OAuth credentials")
        return False
    
    print("\n✓ Environment configuration looks good")
    return True


def check_directory_structure():
    """Check if directory structure is correct"""
    print("\nChecking directory structure...")
    
    required_dirs = [
        'clawbot',
        'clawbot/auth',
        'clawbot/integrations',
        'clawbot/routing'
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"  ✓ {dir_path}/")
        else:
            print(f"  ✗ {dir_path}/ - MISSING")
            all_exist = False
    
    if not all_exist:
        print("\n❌ Directory structure incomplete")
        return False
    
    print("\n✓ Directory structure is correct")
    return True


def check_token_cache():
    """Check token cache directory"""
    print("\nChecking token cache setup...")
    
    cache_type = os.getenv('TOKEN_CACHE_TYPE', 'file')
    print(f"  Token cache type: {cache_type}")
    
    if cache_type == 'file':
        cache_path = Path(os.getenv('TOKEN_CACHE_PATH', './.token_cache'))
        cache_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ Token cache directory: {cache_path}")
    elif cache_type == 'redis':
        try:
            import redis
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            r.ping()
            print(f"  ✓ Redis connection successful ({redis_host}:{redis_port})")
        except Exception as e:
            print(f"  ✗ Redis connection failed: {e}")
            return False
    
    print("\n✓ Token cache setup is correct")
    return True


def main():
    """Run all checks"""
    print("=" * 60)
    print("Clawbot Setup Verification")
    print("=" * 60)
    
    checks = [
        check_dependencies,
        check_directory_structure,
        check_env_file,
        check_token_cache
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Error during check: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ All checks passed! Clawbot is ready to use.")
        print("\nNext steps:")
        print("1. Complete OAuth flow: GET /auth/authorize?user_id=YOUR_USER_ID")
        print("2. Visit the authorization URL and grant permissions")
        print("3. Handle callback: GET /auth/callback?code=CODE&user_id=YOUR_USER_ID")
        print("4. Start using the API!")
        print("\nRun the API with: uvicorn clawbot_api:app --reload")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
