# 🔍 Quality Inspection Guide

This guide shows you how to use the new quality inspection features to ensure high-quality data in your search engine pipeline.

## 📋 Overview

The quality inspection functionality writes processed documents to files **before indexing** so you can:
- ✅ Inspect data quality manually
- 📊 Get detailed quality metrics 
- 🔍 See sample processed documents
- 📈 Monitor processing performance
- 🎯 Identify issues before they reach your search index

## 🚀 Quick Start

### 1. Basic Quality Inspection with Test Data

```bash
# Test with sample data
cd /home/gyashu/projects/A_Search_Engine/ai_search/data_pipeline
python3 test_quality_inspection.py
```

### 2. Process Real Batch Files with Quality Inspection

```bash
# Process a few batch files with quality inspection
python3 enhanced_pipeline_runner.py \
  --batch-dir ../../RawHTMLdata \
  --pattern "batch_20250728_125404_*.json" \
  --quality-dir quality_output \
  --min-quality 1.0
```

### 3. Process All Batch Files

```bash
# Process all batch files (be careful - this might take a while!)
python3 enhanced_pipeline_runner.py \
  --batch-dir ../../RawHTMLdata \
  --pattern "batch_*.json" \
  --quality-dir all_batches_quality \
  --min-quality 0.8
```

## 📁 Output Files

For each batch processed, you get **3 files**:

### 1. 📄 Main Data File (`processed_data_*.json`)
- Complete processed documents and chunks
- Processing metadata and stats
- Quality summary metrics
- **Use for**: Detailed analysis, debugging, data auditing

### 2. 📊 Quality Report (`quality_report_*.txt`)
- Human-readable quality summary
- Performance metrics
- Domain breakdown
- Quality scores and statistics
- **Use for**: Quick quality assessment, monitoring trends

### 3. 🔍 Sample Documents (`sample_documents_*.txt`)
- First 3 processed documents with details
- Shows chunks, quality scores, extracted content
- **Use for**: Manual inspection, spot-checking quality

## ⚙️ Configuration Options

### Quality Threshold
```bash
--min-quality 1.5  # Only index chunks with quality >= 1.5
```

### Output Directory
```bash
--quality-dir my_quality_reports  # Custom output directory
```

### Disable Quality Inspection
```bash
--no-quality-inspection  # Skip writing quality files (faster)
```

### File Pattern Matching
```bash
--pattern "batch_20250728_*.json"  # Only specific batches
--pattern "*.json"                 # All JSON files
```

## 📊 Understanding Quality Metrics

### Document Quality
- **Avg Title Length**: Should be 20-100 chars for good titles
- **Unique Domains**: Shows diversity of your content sources  
- **Content Types**: article, blog, documentation, qa, etc.
- **Keywords per Doc**: 5-15 is typically good
- **Docs with Categories**: Should be close to 100%

### Chunk Quality  
- **Avg Chunk Length**: 800-2000 chars is optimal for search
- **Word Count**: 100-300 words per chunk is good
- **Quality Score**: Higher is better (1.0+ is good, 2.0+ is excellent)
- **Domain Score**: Authority score based on domain reputation
- **Chunks per Document**: 1-3 chunks per doc is typical

### Performance Metrics
- **Success Rate**: Should be 80%+ (some failures are normal)
- **Processing Speed**: 10+ docs/second is good performance
- **Quality Filter Rate**: % of processed docs that pass quality filter

## 🎯 Quality Inspection Workflow

### Step 1: Process a Small Batch First
```bash
# Test with just one batch file
python3 enhanced_pipeline_runner.py \
  --batch-dir ../../RawHTMLdata \
  --pattern "batch_20250728_125404_0.json" \
  --quality-dir test_quality
```

### Step 2: Review Quality Report
```bash
# Check the quality report
cat test_quality/quality_report_*.txt
```

### Step 3: Inspect Sample Documents  
```bash
# Look at sample processed documents
cat test_quality/sample_documents_*.txt
```

### Step 4: Adjust Settings if Needed
- Increase `--min-quality` if too much low-quality content
- Decrease `--min-quality` if too few documents pass
- Check domain scores and content categories

### Step 5: Process More Batches
```bash
# Process more batches with refined settings
python3 enhanced_pipeline_runner.py \
  --batch-dir ../../RawHTMLdata \
  --pattern "batch_20250728_*.json" \
  --quality-dir production_quality \
  --min-quality 1.2
```

## 🔧 Integration with Existing Code

### Using in Your Own Scripts

```python
from processor import DocumentProcessor

# Initialize processor
processor = DocumentProcessor()

# Process documents with quality inspection
result = processor.process_batch(
    documents,
    write_output=True,           # Enable quality files
    output_dir="my_quality",     # Custom directory
    batch_name="my_batch"        # Custom batch name
)

# Or write quality files manually
processor.write_processed_documents(
    result["documents"],
    result["chunks"],
    output_dir="manual_inspection",
    batch_name="manual_check"
)
```

## 📈 Monitoring Quality Over Time

1. **Track Quality Trends**: Compare quality reports across batches
2. **Monitor Success Rates**: Watch for drops in processing success
3. **Check Domain Diversity**: Ensure good variety in content sources
4. **Review Sample Content**: Regularly inspect actual processed text
5. **Adjust Quality Thresholds**: Based on search performance feedback

## 🚨 Common Issues & Solutions

### Low Quality Scores
- **Problem**: Most chunks have quality < 1.0
- **Solution**: Check content extraction, review source quality

### High Failure Rate  
- **Problem**: Success rate < 70%
- **Solution**: Check HTML parsing, update extraction logic

### Poor Text Quality
- **Problem**: Extracted text looks garbled or incomplete
- **Solution**: Review sample documents, adjust cleaning parameters

### Too Few Chunks
- **Problem**: Most documents produce only 1 chunk
- **Solution**: Check chunking parameters, content length requirements

## 🎉 Benefits

✅ **Data Quality Assurance**: Catch issues before they reach search index  
✅ **Performance Monitoring**: Track processing speed and success rates  
✅ **Content Analysis**: Understand what content you're actually indexing  
✅ **Debugging Support**: Detailed logs and sample data for troubleshooting  
✅ **Quality Optimization**: Tune parameters based on actual output quality  

## 🔗 Related Files

- `processor.py` - Main processing logic with quality inspection
- `enhanced_pipeline_runner.py` - Full pipeline with quality features
- `test_quality_inspection.py` - Test script for quality functionality
- `indexer.py` - OpenSearch indexing with bulk optimization
