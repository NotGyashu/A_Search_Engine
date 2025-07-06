#!/usr/bin/env python3
"""Show the organized project structure"""

import os
from pathlib import Path

def show_structure():
    print("🏗️  ORGANIZED PROJECT STRUCTURE")
    print("=" * 50)
    
    root = Path(".")
    
    # Show main directories
    print("📁 mini_search_engine/")
    
    # Show crawler
    if (root / "crawler").exists():
        print("├── 🕷️  crawler/                    # C++ web crawler")
        print("│   ├── src/                      # Source code")
        print("│   ├── build/                    # Compiled binaries")
        print("│   └── scripts/                  # Build scripts")
    
    # Show AI search structure
    print("├── 🧠 ai_search/                   # AI search engine")
    print("│   ├── backend/                    # Python backend")
    
    # Check backend files
    backend_dir = root / "ai_search" / "backend"
    if backend_dir.exists():
        # Check main files
        if (backend_dir / "demo.py").exists():
            print("│   │   ├── demo.py                # Project showcase")
        if (backend_dir / "README.md").exists():
            print("│   │   ├── README.md              # Documentation")
        
        # Check search directory
        search_dir = backend_dir / "search"
        if search_dir.exists():
            print("│   │   ├── search/                # Core search engine")
            if (search_dir / "ai_search_engine.py").exists():
                print("│   │   │   └── ai_search_engine.py")
        
        # Check scripts directory
        scripts_dir = backend_dir / "scripts"
        if scripts_dir.exists():
            print("│   │   ├── scripts/               # Utility scripts")
            scripts = list(scripts_dir.glob("*.py"))
            for script in sorted(scripts):
                print(f"│   │   │   ├── {script.name}")
        
        # Check venv
        if (backend_dir / "venv").exists():
            print("│   │   └── venv/                  # Python environment")
    
    # Show data pipeline
    data_pipeline_dir = root / "ai_search" / "data_pipeline"
    if data_pipeline_dir.exists():
        print("│   └── data_pipeline/              # Data processing")
        pipeline_files = list(data_pipeline_dir.glob("*.py"))
        for file in sorted(pipeline_files):
            print(f"│       ├── {file.name}")
    
    # Show data directory
    if (root / "data").exists():
        print("├── 📊 data/                        # Data storage")
        print("│   ├── raw/                       # Crawler output")
        print("│   └── processed/                 # Clean data + AI index")
    
    # Show docs
    if (root / "docs").exists():
        print("└── 📚 docs/                        # Documentation")
        docs = list((root / "docs").glob("*.md"))
        for doc in sorted(docs):
            print(f"    └── {doc.name}")
    
    print("\n🎯 MAIN ENTRY POINTS:")
    print("=" * 30)
    
    # Check which files exist and show how to run them
    if (backend_dir / "demo.py").exists():
        print("📊 Project Demo:")
        print("   cd ai_search/backend && python demo.py")
    
    if (search_dir / "ai_search_engine.py").exists():
        print("\n🔍 AI Search Engine:")
        print("   cd ai_search/backend && python search/ai_search_engine.py")
    
    if (backend_dir / "scripts" / "check_data.py").exists():
        print("\n📈 Data Statistics:")
        print("   cd ai_search/backend && python scripts/check_data.py")
    
    print("\n✅ PROJECT PROPERLY ORGANIZED!")

if __name__ == "__main__":
    show_structure()
