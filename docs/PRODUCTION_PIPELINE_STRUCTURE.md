# Production Data Pipeline Structure

## Overview
This is the cleaned, production-ready hybrid Rust/Python data pipeline that achieved 5.90x performance improvement.

## Core Components (KEEP)

### Python Components
- `hybrid_processor.py` - Main orchestrator (hybrid Rust/Python)
- `scorer.py` - Content scoring (Python-only, complex logic)
- `language_detector.py` - Language detection (lightweight)
- `stop_words.txt` - Stop words list
- `run_production_pipeline.py` - Production entry point

### Rust Components  
- `rust_core_processor/` - Complete Rust library
  - `src/lib.rs` - Python FFI interface
  - `src/extractor.rs` - Fast HTML parsing & extraction
  - `src/cleaner.rs` - Text cleaning & chunking
  - `src/types.rs` - Data structures
  - `Cargo.toml` - Dependencies

### Configuration
- `config.py` - Pipeline configuration
- `requirements.txt` - Python dependencies

## Legacy Components (REMOVE)
- `processor.py` - Replaced by hybrid_processor.py
- `extractor.py` - Replaced by Rust extractor
- `cleaner.py` - Replaced by Rust cleaner
- `enhanced_metadata_extractor.py` - Integrated into Rust
- All test/debug scripts
- Performance comparison scripts
- Verification scripts

## Performance
- **Speed**: 5.90x faster than original Python pipeline
- **Compatibility**: 91.3% field compatibility
- **Success Rate**: 100% vs 66.7% for Python-only
