#!/usr/bin/env python3
"""
Simple test script - Basic functionality check
"""

import sys
from pathlib import Path

# Add module path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_imports():
    """Module import test"""
    print("Module import test...")
    
    try:
        from src.ifc_parser import IFCParser
        print("IFCParser import successful")
    except ImportError as e:
        print(f"IFCParser import failed: {e}")
        return False
    
    try:
        from src.neo4j_database import Neo4jDatabase
        print("Neo4jDatabase import successful")
    except ImportError as e:
        print(f"Neo4jDatabase import failed: {e}")
        return False
    
    try:
        from src.graph_converter import IFCToGraphConverter
        print("IFCToGraphConverter import successful")
    except ImportError as e:
        print(f"IFCToGraphConverter import failed: {e}")
        return False
    
    try:
        from src.utils import setup_logging
        print("utils import successful")
    except ImportError as e:
        print(f"utils import failed: {e}")
        return False
    
    return True

def test_file_structure():
    """File structure test"""
    print("\nFile structure test...")
    
    required_files = [
        'requirements.txt',
        '.env',
        'src/ifc_parser.py',
        'src/neo4j_database.py',
        'src/graph_converter.py',
        'src/utils.py',
        'import_ifc.py',
        'input/Duplex_A_20110907.ifc'
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"OK {file_path}")
        else:
            print(f"MISSING {file_path} - file does not exist")
            all_exist = False
    
    return all_exist

def test_env_file():
    """Environment configuration file test"""
    print("\nEnvironment configuration test...")
    
    env_file = Path('.env')
    if not env_file.exists():
        print("MISSING .env file does not exist")
        return False
    
    try:
        from dotenv import load_dotenv
        import os
        
        load_dotenv(env_file)
        
        required_vars = ['NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD', 'NEO4J_DATABASE']
        all_set = True
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                print(f"OK {var} = {value}")
            else:
                print(f"MISSING {var} - not configured")
                all_set = False
        
        return all_set
        
    except ImportError:
        print("MISSING python-dotenv package is not installed")
        return False

def main():
    """Main test function"""
    print("BIM Graph RAG Project Basic Test")
    print("Basic functionality verification")
    
    # Execute tests
    tests = [
        ("File Structure", test_file_structure),
        ("Module Import", test_imports),
        ("Environment Config", test_env_file),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"ERROR {test_name} test error: {e}")
            results.append((test_name, False))
    
    # Results summary
    print("\nTest Results Summary")
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall result: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\nAll basic tests passed!")
        print("Now check the main application with 'python import_ifc.py --help' command.")
    else:
        print("\nSome tests failed. Please check the errors above.")
    
    return 0 if passed == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())