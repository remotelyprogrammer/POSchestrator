# POS Data Processing Tool - Usage Guide

## 📋 Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Usage Examples](#usage-examples)
- [Pipeline Types](#pipeline-types)
- [Advanced Usage](#advanced-usage)
- [Troubleshooting](#troubleshooting)
- [File Structure](#file-structure)

---

## 📌 Overview

The **POS Data Processing Tool** is a command-line application designed to process Point-of-Sale (POS) data from Excel files and generate cleaned CSV reports. It supports two types of output files:
- **SLS** (Sales) - Transaction header data for sales analysis
- **SDET** (Sales Detail) - Detailed sales entry data for item-level analysis

### Key Features
- Process all brands/shops or target specific ones
- Generate either SLS, SDET, or both file types
- Process multiple shops simultaneously
- Comprehensive validation and error handling
- Detailed logging and progress tracking

---

## 🚀 Quick Start

### Basic Usage
```bash
# Process all brands and shops (generates both SLS and SDET files)
python3 main.py

# View available options
python3 main.py --help
```

### Most Common Commands
```bash
# List available brands
python3 main.py --list-brands

# List shops for a specific brand
python3 main.py --list-shops --brand Manam

# Process specific brand
python3 main.py --brand Manam

# Process specific shop
python3 main.py --brand Manam --shop Cebu
```

---

## 📖 Command Reference

### Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--brand BRAND` | Process files for a specific brand only | `--brand Manam` |
| `--shop SHOP` | Process files for specific shop(s) | `--shop Cebu` |
| `--pipeline TYPE` | Specify which pipeline to run (`sls` or `sdet`) | `--pipeline sls` |
| `--list-brands` | List all available brands and exit | N/A |
| `--list-shops` | List shops for a brand (requires `--brand`) | `--list-shops --brand Manam` |
| `--verbose, -v` | Enable verbose logging | `--verbose` |
| `--help, -h` | Show help message | N/A |

### Pipeline Types
- `sls` - Generate Sales (SLS) files only
- `sdet` - Generate Sales Detail (SDET) files only
- Both (default) - Generate both SLS and SDET files

---

## 💡 Usage Examples

### 1. Discovery Commands
```bash
# See what brands are available
python3 main.py --list-brands
# Output: Available Brands: • Manam (2 shops: Cebu, Greenhills)

# See what shops are available for a brand
python3 main.py --list-shops --brand Manam
# Output: Available Shops for 'Manam': • Cebu • Greenhills
```

### 2. Full Processing
```bash
# Process everything (all brands, all shops, both SLS and SDET)
python3 main.py

# Process everything but only generate SLS files
python3 main.py --pipeline sls

# Process everything but only generate SDET files
python3 main.py --pipeline sdet
```

### 3. Brand-Level Processing
```bash
# Process all shops for Manam brand (both SLS and SDET)
python3 main.py --brand Manam

# Process all Manam shops, only SLS files
python3 main.py --brand Manam --pipeline sls

# Process all Manam shops, only SDET files
python3 main.py --brand Manam --pipeline sdet
```

### 4. Single Shop Processing
```bash
# Process only Manam Cebu shop (both SLS and SDET)
python3 main.py --brand Manam --shop Cebu

# Process only Manam Cebu shop, only SLS files
python3 main.py --brand Manam --shop Cebu --pipeline sls

# Process only Manam Cebu shop, only SDET files
python3 main.py --brand Manam --shop Cebu --pipeline sdet
```

### 5. Multiple Shop Processing
```bash
# Process Cebu and Greenhills shops (both SLS and SDET)
python3 main.py --brand Manam --shop Cebu --shop Greenhills

# Process multiple shops, only SLS files
python3 main.py --brand Manam --shop Cebu --shop Greenhills --pipeline sls

# Process multiple shops, only SDET files
python3 main.py --brand Manam --shop Cebu --shop Greenhills --pipeline sdet
```

### 6. Pipeline Combinations
```bash
# Generate both SLS and SDET (same as default)
python3 main.py --pipeline sls --pipeline sdet

# You can specify pipelines in any order
python3 main.py --pipeline sdet --pipeline sls
```

### 7. Verbose Output
```bash
# Enable detailed logging for troubleshooting
python3 main.py --brand Manam --shop Cebu --verbose
```

---

## 🔧 Pipeline Types

### SLS (Sales) Pipeline
- **Purpose**: Generate transaction-level sales data
- **Source**: Transaction Header, Payment Entry, Sales Entry, Infocode Entry sheets
- **Output**: `SLS_MMDDYY_BRAND_BRANCH_SHOP.csv`
- **Use Case**: Sales analysis, revenue tracking, customer behavior

### SDET (Sales Detail) Pipeline  
- **Purpose**: Generate item-level sales detail data
- **Source**: Transaction Sales Entry sheet
- **Output**: `SDET_MMDDYY_BRAND_BRANCH_SHOP.csv`
- **Use Case**: Inventory analysis, product performance, detailed item tracking

### Output File Naming Convention
Files are automatically named using the format:
```
{PIPELINE}_{DATE}_{BRAND}_{BRAND}_{SHOP}.csv
```
- `PIPELINE`: SLS or SDET
- `DATE`: MMDDYY from the source Excel filename
- `BRAND`: Brand name in uppercase
- `SHOP`: Shop name in uppercase

**Examples:**
- `SLS_081725_MANAM_MANAM_GREENHILLS.csv`
- `SDET_070925_MANAM_MANAM_SM_CEBU.csv`

---

## 🎯 Advanced Usage

### Batch Processing Scripts
You can create shell scripts for routine processing:

```bash
#!/bin/bash
# weekly_processing.sh

echo "Starting weekly POS data processing..."

# Process all shops for SLS only
python3 main.py --brand Manam --pipeline sls

# Process specific shops for SDET only
python3 main.py --brand Manam --shop Cebu --shop Greenhills --pipeline sdet

echo "Weekly processing completed!"
```

### Combining with Other Tools
```bash
# Process and immediately check output directory
python3 main.py --brand Manam && ls -la "POS DATA/Manam/"

# Process with timestamp logging
python3 main.py --brand Manam 2>&1 | tee "processing_$(date +%Y%m%d_%H%M%S).log"
```

---

## 🛠️ Troubleshooting

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Brand 'X' not found` | Invalid brand name | Run `--list-brands` to see available brands |
| `Shop 'X' not found for brand 'Y'` | Invalid shop name | Run `--list-shops --brand Y` to see available shops |
| `--shop requires --brand` | Shop specified without brand | Always use `--brand` when using `--shop` |
| `--list-shops requires --brand` | List shops without specifying brand | Use `--list-shops --brand BRANDNAME` |
| `No Excel files found` | No transtable files in directory | Check if Excel files exist in the expected directory structure |

### Debugging Steps

1. **Check Available Options**:
   ```bash
   python3 main.py --list-brands
   python3 main.py --list-shops --brand YourBrand
   ```

2. **Enable Verbose Logging**:
   ```bash
   python3 main.py --verbose --brand YourBrand --shop YourShop
   ```

3. **Test Single Shop First**:
   ```bash
   # Start with a single shop to isolate issues
   python3 main.py --brand Manam --shop Cebu --pipeline sls
   ```

4. **Check File Permissions**:
   ```bash
   # Ensure you can read input files and write to output directories
   ls -la "POS DATA/"
   ```

### Log Levels
- **INFO**: Normal processing information
- **WARNING**: Non-critical issues (missing optional data)
- **ERROR**: Critical errors that stop processing
- **DEBUG**: Detailed technical information (use `--verbose`)

---

## 📁 File Structure

### Expected Directory Structure
```
POSchestrator/
├── main.py                    # Main application
├── orchestrator.py           # Business logic
├── LoyaltyPipeline.py        # Processing engine (existing)
├── settings.py               # Configuration
├── config/
│   ├── config.json          # Column mappings
│   └── branch_mapping.xlsx  # Store mappings
└── POS DATA/
    └── {Brand}/
        └── {Shop}/
            ├── transtable/      # Input Excel files go here
            │   └── *.xlsx
            ├── sls/            # Optional: SLS files copied here
            ├── sdet/           # Optional: SDET files copied here
            ├── SLS_*.csv       # Generated SLS files
            └── SDET_*.csv      # Generated SDET files
```

### Input Requirements
- Excel files must be placed in `POS DATA/{Brand}/{Shop}/transtable/`
- Files must contain the required sheets:
  - For SLS: Transaction Header, Trans. Sales Entry, Trans. Payment Entry, Trans. Infocode Entry
  - For SDET: Trans. Sales Entry
- Files should follow naming convention: `{Brand} {Shop} {DateRange}.xlsx`

### Output Locations
Generated CSV files are placed in the respective brand/shop directories:
- `POS DATA/{Brand}/{Shop}/SLS_*.csv`
- `POS DATA/{Brand}/{Shop}/SDET_*.csv`

---

## 📞 Support

### Before Seeking Help
1. Check this documentation
2. Run with `--verbose` to get detailed error information
3. Verify file structure and permissions
4. Test with a single shop first

### Information to Provide When Reporting Issues
- Exact command used
- Complete error message
- Output from `--list-brands` and `--list-shops`
- File structure of affected directories

---

## 📊 Summary

The POS Data Processing Tool provides flexible options for processing POS data:

- **Discovery**: Use `--list-brands` and `--list-shops` to explore available data
- **Scope**: Process everything, specific brands, or individual shops
- **Output**: Choose SLS, SDET, or both pipeline types
- **Scale**: Process single or multiple shops simultaneously
- **Debugging**: Use `--verbose` for detailed logging

Start with discovery commands, then gradually narrow your scope to the specific data you need to process.
