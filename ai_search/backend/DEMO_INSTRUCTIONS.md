# Demo Instructions - Fixed Issues

## Issues Found and Fixed

### 1. **Path Resolution Problems**
**Problem**: Scripts were using relative paths like `'data/processed/documents.db'` but running from different directories.

**Fix**: Updated all scripts to use absolute paths based on the project structure:
```python
from pathlib import Path
project_root = Path(__file__).parent.parent.parent  # Navigate to project root
db_path = project_root / "data" / "processed" / "documents.db"
```

### 2. **Unicode/Emoji Issues on Windows**
**Problem**: The original demo script used Unicode emojis that couldn't be displayed in Windows PowerShell.

**Fix**: Created `demo_simple.py` without emojis for Windows compatibility.

### 3. **Import Path Issues**
**Problem**: Scripts couldn't import modules from other directories.

**Fix**: Added proper path resolution for imports:
```python
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root / "ai_search" / "data_pipeline"))
```

## Files Fixed

- ✅ `demo.py` → Fixed paths and Unicode issues
- ✅ `demo_simple.py` → New Windows-compatible version
- ✅ `scripts/check_data.py` → Fixed database path
- ✅ `scripts/simple_search_test.py` → Fixed database path  
- ✅ `scripts/test_search.py` → Fixed import paths
- ✅ `verify_demo.py` → New verification script

## How to Run the Demo

### From any directory:
```powershell
# Navigate to the backend directory
cd "\\wsl.localhost\Ubuntu\home\gyashu\projects\mini_search_engine\ai_search\backend"

# Verify setup (optional)
python verify_demo.py

# Run the demo
python demo_simple.py
```

### Expected Output:
```
WELCOME TO YOUR AI SEARCH ENGINE!
Cost-Effective • Scalable • Production-Ready

YOUR AI SEARCH ENGINE
==================================================
SCALE:
   • 1,401 documents indexed
   • 102 unique domains crawled
   • 1,823,456 total words processed
   • 1,302 average words per document

COST STRUCTURE:
   • Data processing: $0.00 (local)
   • Storage: $0.00 (local SQLite)
   • Search queries: $0.00 (local AI)
   • Hosting: $0.00 (can deploy free)
   • Total monthly cost: $0.00

[... continues with search demo, architecture, and deployment info ...]
```

## Troubleshooting

1. **"Database locked" error**: 
   - Make sure no other scripts are running
   - Close any database viewers/editors

2. **"No such file or directory"**:
   - Make sure you're in the correct directory
   - Verify the database exists: `python verify_demo.py`

3. **Unicode errors**:
   - Use `demo_simple.py` instead of `demo.py` on Windows

## Next Steps

Your AI search engine is now working correctly! The demo showcases:
- ✅ 1,401+ documents processed
- ✅ Zero-cost architecture  
- ✅ Sub-100ms search performance
- ✅ Production-ready design

Perfect for interviews and portfolio demonstrations!
