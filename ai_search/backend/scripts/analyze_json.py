#!/usr/bin/env python3
"""Quick script to analyze crawler JSON structure"""

import json
import sys
from pathlib import Path

def analyze_json_file(file_path):
    print(f"Analyzing: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Type: {type(data)}")
        
        if isinstance(data, list):
            print(f"List with {len(data)} items")
            if data:
                print(f"First item type: {type(data[0])}")
                if isinstance(data[0], dict):
                    print(f"First item keys: {list(data[0].keys())}")
                    # Print a sample of the first item
                    sample = {k: str(v)[:100] + "..." if len(str(v)) > 100 else v 
                             for k, v in data[0].items()}
                    print(f"First item sample: {sample}")
        
        elif isinstance(data, dict):
            print(f"Dict with keys: {list(data.keys())}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Analyze the first JSON file
    json_files = list(Path("../../../Data/Raw").glob("*.json"))
    if json_files:
        analyze_json_file(json_files[0])
    else:
        print("No JSON files found!")
