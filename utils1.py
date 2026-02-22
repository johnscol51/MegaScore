# utils1.py
import os

def appDir():
    """Return directory of this script (cross-platform safe)."""
    return os.path.dirname(os.path.abspath(__file__))

