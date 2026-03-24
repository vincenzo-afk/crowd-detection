"""
Quick-launch script for Windows users.
Run: python launch.py --sim
"""
import sys
import os
import subprocess

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    args = ["python", "main.py"] + sys.argv[1:]
    subprocess.run(args)
