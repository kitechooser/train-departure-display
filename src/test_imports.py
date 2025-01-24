"""Test script to verify imports are working"""
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.api import TflClient
from src.domain.models import TflStation, TflService
from src.domain.processors import TflProcessor

def test_imports():
    print("Testing imports...")
    print("TflClient imported successfully")
    print("TflStation imported successfully")
    print("TflService imported successfully")
    print("TflProcessor imported successfully")
    print("All imports working!")

if __name__ == "__main__":
    test_imports()
