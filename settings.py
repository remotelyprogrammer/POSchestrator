"""
POS Data Processing Tool - Configuration Settings
Project Genesis - Phase 1

This file contains the configuration for all brands and their corresponding shops.
Add or remove shops here without modifying the core application logic.
"""

# POS Shops Configuration
# Structure: List of dictionaries with brand (mother folder) and their shops
POS_SHOPS = [
    {
        "brand": "Manam",
        "shops": ["Cebu", "Greenhills"]
    },
    # Add more brands and shops here as needed
    # Example:
    # {
    #     "brand": "AnotherBrand",
    #     "shops": ["Shop1", "Shop2", "Shop3"]
    # },
]

# Base directory configuration
BASE_POS_DATA_DIR = "POS DATA"

# Required subdirectories for each shop
REQUIRED_SUBDIRS = ["transtable", "sdet", "sls"]

# Output file names (for Phase 2 integration)
OUTPUT_FILES = {
    "sdet": "sdet.csv",
    "sls": "sls.csv"
}
