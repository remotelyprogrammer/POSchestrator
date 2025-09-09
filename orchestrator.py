"""
POS Data Processing Orchestrator
Project Genesis - Phase 1

This module contains the POSDataOrchestrator class that handles the business logic
for processing POS data files according to the brand/shop configuration.
"""

import os
import glob
import logging
from typing import List, Dict, Optional, Tuple
from LoyaltyPipeline2 import PipelineRunner
from settings import POS_SHOPS, BASE_POS_DATA_DIR, REQUIRED_SUBDIRS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class POSDataOrchestrator:
    """
    Orchestrates the processing of POS data files for multiple brands and shops.
    Handles directory navigation, file discovery, and pipeline execution.
    """
    
    def __init__(self, base_data_dir: str = BASE_POS_DATA_DIR, 
                 config_dir: str = "config"):
        """
        Initialize the orchestrator.
        
        Args:
            base_data_dir: Base directory containing POS data (default: "POS DATA")
            config_dir: Directory containing configuration files (default: "config")
        """
        self.base_data_dir = base_data_dir
        self.config_dir = config_dir
        self.config_file_path = os.path.join(config_dir, "config.json")
        self.branch_mapping_file_path = os.path.join(config_dir, "branch_mapping.xlsx")
        
        # Validate base directory exists
        if not os.path.exists(self.base_data_dir):
            raise FileNotFoundError(f"Base POS data directory not found: {self.base_data_dir}")
        
        # Validate config files exist
        self._validate_config_files()
    
    def _validate_config_files(self) -> None:
        """Validate that required configuration files exist."""
        if not os.path.exists(self.config_file_path):
            raise FileNotFoundError(f"Config file not found: {self.config_file_path}")
        
        if not os.path.exists(self.branch_mapping_file_path):
            raise FileNotFoundError(f"Branch mapping file not found: {self.branch_mapping_file_path}")
    
    def _get_brand_path(self, brand: str) -> str:
        """Get the full path to a brand directory."""
        return os.path.join(self.base_data_dir, brand)
    
    def _get_shop_path(self, brand: str, shop: str) -> str:
        """Get the full path to a shop directory."""
        return os.path.join(self._get_brand_path(brand), shop)
    
    def _ensure_shop_directories(self, brand: str, shop: str) -> None:
        """Ensure all required subdirectories exist for a shop."""
        shop_path = self._get_shop_path(brand, shop)
        
        for subdir in REQUIRED_SUBDIRS:
            dir_path = os.path.join(shop_path, subdir)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"Created directory: {dir_path}")
    
    def _find_monthly_transtable_file(self, brand: str, shop: str, month: str, year: str) -> Optional[str]:
        """
        Find the Excel file for the given brand/shop/month/year in the transtable directory.
        Accepts both full month name (e.g., 'September') and two-digit month (e.g., '09').
        Returns the first match or None if not found.
        """
        import re
        from calendar import month_name
        transtable_path = os.path.join(self._get_shop_path(brand, shop), "transtable")
        if not os.path.exists(transtable_path):
            logger.warning(f"Transtable directory not found: {transtable_path}")
            return None
        # Normalize month
        month_str = str(month).strip()
        year_str = str(year).strip()
        # Accept both 'September' and '09'
        try:
            if month_str.isdigit():
                month_num = int(month_str)
                month_full = month_name[month_num]
                month_variants = [f"{month_num:02d}", month_full]
            else:
                # Try to get month number from name
                month_full = month_str.capitalize()
                month_num = [i for i, m in enumerate(month_name) if m.lower() == month_full.lower()]
                if month_num:
                    month_num = month_num[0]
                    month_variants = [f"{month_num:02d}", month_full]
                else:
                    month_variants = [month_full]
        except Exception:
            month_variants = [month_str]
        # Build regex pattern for file name
        # Example: Manam Cebu September 2025.xlsx or Manam Cebu 09 2025.xlsx
        safe_brand = re.escape(brand)
        safe_shop = re.escape(shop)
        safe_year = re.escape(year_str)
        candidates = []
        for m in month_variants:
            pattern = re.compile(rf"^{safe_brand}\s+{safe_shop}\s+{m}\s+{safe_year}\.xlsx$", re.IGNORECASE)
            for fname in os.listdir(transtable_path):
                if pattern.match(fname):
                    candidates.append(os.path.join(transtable_path, fname))
        if candidates:
            return candidates[0]
        logger.warning(f"No monthly file found for {brand} - {shop} [{month_str} {year_str}] in {transtable_path}")
        return None
    
    def _get_output_directory(self, brand: str, shop: str) -> str:
        """
        Get the output directory for processed files (parent of sdet/sls folders).
        
        Args:
            brand: Brand name
            shop: Shop name
            
        Returns:
            Full path to the shop directory (parent of sdet/sls)
        """
        return self._get_shop_path(brand, shop)
    
    def _process_shop_file(self, brand: str, shop: str, excel_file_path: str, pipeline_types: List[str] = None, month: str = None, year: str = None) -> Dict[str, str]:
        """
        Process a single Excel file for a shop using the LoyaltyPipeline.
        
        Args:
            brand: Brand name
            shop: Shop name
            excel_file_path: Full path to the Excel file to process
            pipeline_types: List of pipeline types to run ('sls', 'sdet'). If None, runs both.
            
        Returns:
            Dictionary containing output file paths
        """
        file_name = os.path.basename(excel_file_path)
        logger.info(f"Processing '{file_name}' for {brand} - {shop}")
        # Default to both pipelines if not specified
        if pipeline_types is None:
            pipeline_types = ['sls', 'sdet']
        # Validate pipeline types
        valid_types = ['sls', 'sdet']
        pipeline_types = [pt.lower() for pt in pipeline_types]
        for pt in pipeline_types:
            if pt not in valid_types:
                raise ValueError(f"Invalid pipeline type '{pt}'. Must be one of: {valid_types}")
        logger.info(f"Running pipelines: {', '.join(pipeline_types).upper()}")
        try:
            output_directory = self._get_output_directory(brand, shop)
            pipeline_orchestrator = PipelineRunner.from_config(
                excel_file_path=excel_file_path,
                config_file_path=self.config_file_path,
                branch_mapping_file_path=self.branch_mapping_file_path,
                output_directory=output_directory
            )
            all_sheets_dict = pipeline_orchestrator.data_reader.read_sheets()
            output_files = {}
            # Output file naming convention: SDET_MMYY_Brand_Shop.csv, SLS_MMYY_Brand_Shop.csv
            from datetime import datetime
            # Determine MM and YY
            if month and year:
                try:
                    if month.isdigit():
                        mm = f"{int(month):02d}"
                    else:
                        dt = datetime.strptime(month[:3], "%b")
                        mm = f"{dt.month:02d}"
                except Exception:
                    mm = month[:2]
                yy = year[-2:]
            else:
                now = datetime.now()
                mm = now.strftime('%m')
                yy = now.strftime('%y')
            brand_safe = brand.replace(' ', '_').upper()
            shop_safe = shop.replace(' ', '_').upper()
            if 'sls' in pipeline_types:
                sls_output = pipeline_orchestrator.run_sls_pipeline(all_sheets_dict)
                # Rename/move output file to new convention
                sls_new_name = f"SLS_{mm}{yy}_{brand_safe}_{shop_safe}.csv"
                sls_new_path = os.path.join(output_directory, sls_new_name)
                if sls_output != sls_new_path:
                    try:
                        os.replace(sls_output, sls_new_path)
                        logger.info(f"Renamed SLS output to: {sls_new_path}")
                    except Exception as e:
                        logger.warning(f"Could not rename SLS output: {e}")
                output_files['sls_file'] = sls_new_path
            if 'sdet' in pipeline_types:
                sdet_output = pipeline_orchestrator.run_sdet_pipeline(all_sheets_dict)
                sdet_new_name = f"SDET_{mm}{yy}_{brand_safe}_{shop_safe}.csv"
                sdet_new_path = os.path.join(output_directory, sdet_new_name)
                if sdet_output != sdet_new_path:
                    try:
                        os.replace(sdet_output, sdet_new_path)
                        logger.info(f"Renamed SDET output to: {sdet_new_path}")
                    except Exception as e:
                        logger.warning(f"Could not rename SDET output: {e}")
                output_files['sdet_file'] = sdet_new_path
            logger.info(f"✅ Successfully processed '{file_name}' for {brand} - {shop}")
            if 'sls_file' in output_files:
                logger.info(f"   SLS Output: {output_files['sls_file']}")
            if 'sdet_file' in output_files:
                logger.info(f"   SDET Output: {output_files['sdet_file']}")
            return output_files
        except Exception as e:
            logger.error(f"❌ Failed to process '{file_name}' for {brand} - {shop}: {e}")
            raise
    
    def process_shop(self, brand: str, shop: str, pipeline_types: List[str] = None, month: str = None, year: str = None) -> List[Dict[str, str]]:
        """
        Process the monthly Excel file for a specific brand and shop.
        Args:
            brand: Brand name
            shop: Shop name
            pipeline_types: List of pipeline types to run ('sls', 'sdet'). If None, runs both.
            month: Month to process (e.g., 'September' or '09')
            year: Year to process (e.g., '2025')
        Returns:
            List of dictionaries containing output file paths for the processed file (empty if not found)
        """
        logger.info(f"\n=== Processing {brand} - {shop} ({month} {year}) ===")
        # Validate brand exists in configuration
        brand_config = next((b for b in POS_SHOPS if b["brand"] == brand), None)
        if not brand_config:
            raise ValueError(f"Brand '{brand}' not found in configuration")
        # Validate shop exists in brand configuration
        if shop not in brand_config["shops"]:
            raise ValueError(f"Shop '{shop}' not found in brand '{brand}' configuration")
        # Ensure shop directories exist
        self._ensure_shop_directories(brand, shop)
        # Find the monthly Excel file to process
        excel_file = self._find_monthly_transtable_file(brand, shop, month, year)
        if not excel_file:
            logger.warning(f"No Excel file found for {brand} - {shop} [{month} {year}] in transtable directory.")
            return []
        logger.info(f"Found monthly Excel file to process for {brand} - {shop}: {os.path.basename(excel_file)}")
        results = []
        try:
            output_files = self._process_shop_file(brand, shop, excel_file, pipeline_types, month=month, year=year)
            results.append(output_files)
        except Exception as e:
            logger.error(f"Error processing file {excel_file}: {e}")
        return results
    
    def process_brand(self, brand: str, pipeline_types: List[str] = None, month: str = None, year: str = None) -> Dict[str, List[Dict[str, str]]]:
        """
        Process all shops for a specific brand for a given month/year.
        Args:
            brand: Brand name
            pipeline_types: List of pipeline types to run ('sls', 'sdet'). If None, runs both.
            month: Month to process
            year: Year to process
        Returns:
            Dictionary mapping shop names to their processing results
        """
        logger.info(f"\n🏢 Processing Brand: {brand} ({month} {year})")
        brand_config = next((b for b in POS_SHOPS if b["brand"] == brand), None)
        if not brand_config:
            raise ValueError(f"Brand '{brand}' not found in configuration")
        results = {}
        for shop in brand_config["shops"]:
            try:
                shop_results = self.process_shop(brand, shop, pipeline_types, month=month, year=year)
                results[shop] = shop_results
            except Exception as e:
                logger.error(f"Error processing shop {shop}: {e}")
                results[shop] = []
                continue
        return results
    
    def process_all(self, pipeline_types: List[str] = None, month: str = None, year: str = None) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
        """
        Process all brands and shops for a given month/year.
        Args:
            pipeline_types: List of pipeline types to run ('sls', 'sdet'). If None, runs both.
            month: Month to process
            year: Year to process
        Returns:
            Dictionary mapping brand names to shop results
        """
        logger.info(f"\n🚀 Starting Full Processing Run - All Brands and Shops ({month} {year})")
        results = {}
        for brand_config in POS_SHOPS:
            brand = brand_config["brand"]
            try:
                brand_results = self.process_brand(brand, pipeline_types, month=month, year=year)
                results[brand] = brand_results
            except Exception as e:
                logger.error(f"Error processing brand {brand}: {e}")
                results[brand] = {}
                continue
        return results
    
    def get_available_brands(self) -> List[str]:
        """Get list of available brands from configuration."""
        return [brand_config["brand"] for brand_config in POS_SHOPS]
    
    def get_available_shops(self, brand: str) -> List[str]:
        """
        Get list of available shops for a brand.
        
        Args:
            brand: Brand name
            
        Returns:
            List of shop names for the brand
        """
        brand_config = next((b for b in POS_SHOPS if b["brand"] == brand), None)
        if not brand_config:
            return []
        
        return brand_config["shops"]
    
    def validate_brand_shop(self, brand: str, shop: str) -> Tuple[bool, str]:
        """
        Validate if a brand and shop combination is valid.
        
        Args:
            brand: Brand name
            shop: Shop name
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if brand not in self.get_available_brands():
            return False, f"Brand '{brand}' not found. Available brands: {', '.join(self.get_available_brands())}"
        
        if shop not in self.get_available_shops(brand):
            return False, f"Shop '{shop}' not found in brand '{brand}'. Available shops: {', '.join(self.get_available_shops(brand))}"
        
        return True, ""
