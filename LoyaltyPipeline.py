import numpy as np
import pandas as pd
import datetime
import os
import json
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set display options for pandas
pd.set_option('display.max_columns', None)

class ExcelDataReader:
    """Reads all sheets from an Excel file into a dictionary of DataFrames."""
    def __init__(self, file_path: str, header_row: int = 2):
        if not os.path.exists(file_path):
            logger.error(f"Excel file not found: {file_path}")
            raise FileNotFoundError(f"Excel file not found at: {file_path}")
        self.file_path = file_path
        self.header_row = header_row

    def read_sheets(self) -> dict[str, pd.DataFrame]:
        """Reads all sheets from the Excel file."""
        logger.info(f"Reading Excel file: {self.file_path}")
        try:
            all_sheets_dict = pd.read_excel(self.file_path, sheet_name=None, header=self.header_row)
            for sheet_name, df in all_sheets_dict.items():
                logger.info(f"Sheet '{sheet_name}' loaded with shape: {df.shape}")
            return all_sheets_dict
        except Exception as e:
            logger.error(f"Error reading Excel file '{self.file_path}': {e}")
            raise

class BaseDataFrameTransformer:
    """Abstract base class for DataFrame transformers."""
    def __init__(self, branch_mapping_df: pd.DataFrame, target_columns: list[str], column_mapping: dict[str, str]):
        self.branch_mapping_df = branch_mapping_df
        self.target_columns = target_columns
        self.column_mapping = column_mapping
        self.default_mapping = {}

    def _set_default_mapping(self, trans_header: pd.DataFrame):
        """Sets common default values for branch/brand info."""
        if 'Store No.' not in trans_header.columns:
            logger.warning("'Store No.' column not found in transaction header. Branch/brand mapping may be incomplete.")
            map_to_use = pd.DataFrame()
        else:
            trans_store_nos = trans_header['Store No.'].astype(int).unique()
            # Ensure erp_code is comparable type for lookup
            self.branch_mapping_df['erp_code_temp'] = self.branch_mapping_df['erp_code'].fillna(-1).astype(int)
            map_to_use = self.branch_mapping_df.loc[
                self.branch_mapping_df['erp_code_temp'].isin(trans_store_nos)
            ]
            del self.branch_mapping_df['erp_code_temp'] # Clean up temporary column


        if not map_to_use.empty:
            self.default_mapping = {
                'branch_id': map_to_use['branch_id'].iloc[0] if 'branch_id' in map_to_use.columns else None,
                'branch': map_to_use['branch'].iloc[0] if 'branch' in map_to_use.columns else None,
                'brand': map_to_use['brand'].iloc[0] if 'brand' in map_to_use.columns else None,
                'posted': False,
            }
            logger.info("Base default mapping initialized dynamically.")
        else:
            logger.warning("No matching branch found for transaction header. Using default None for branch/brand.")
            self.default_mapping = {
                'branch_id': None,
                'branch': None,
                'brand': None,
                'posted': False,
            }

    def _apply_column_mapping_and_defaults(self, source_df: pd.DataFrame, target_df: pd.DataFrame):
        """Applies column mapping and default values."""
        for target_col, source_col in self.column_mapping.items():
            if source_col in source_df.columns:
                target_df[target_col] = source_df[source_col]
            else:
                logger.warning(f"Source column '{source_col}' not found. '{target_col}' in target_df will be empty.")

        for default_col, default_value in self.default_mapping.items():
            if default_col in target_df.columns:
                if pd.notna(default_value):
                    # Apply default only if column is entirely null or has some nulls
                    if target_df[default_col].isnull().all() or target_df[default_col].isnull().any():
                        target_df[default_col] = target_df[default_col].fillna(default_value)
                else: # default_value is None or pd.NA
                    if target_df[default_col].isnull().any():
                        # Decide how to handle existing NaNs when the default is None
                        # Example: Fill with empty string for object columns
                        if target_df[default_col].dtype == 'object':
                            target_df[default_col] = target_df[default_col].fillna('')
                        # Example: Fill with 0 for numeric columns if that's desired
                        elif pd.api.types.is_numeric_dtype(target_df[default_col]):
                            target_df[default_col] = target_df[default_col].fillna(0)
                        # Otherwise, leave as NaN/None
                        logger.debug(f"Default value for '{default_col}' is None. Filling NaNs with specific types if applicable.")
            else:
                logger.warning(f"Default column '{default_col}' not found in target_df schema.")
        return target_df

    def transform(self, data_sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Transforms the given data sheets into a DataFrame."""
        raise NotImplementedError("Subclasses must implement the 'transform' method.")

class SlsDataFrameTransformer(BaseDataFrameTransformer):
    """Transforms data for the Sales Header (SLS) table."""
    def __init__(self, branch_mapping_df: pd.DataFrame, sls_columns: list[str], column_mapping: dict[str, str]):
        super().__init__(branch_mapping_df, sls_columns, column_mapping)

    def _set_default_mapping(self, trans_header: pd.DataFrame):
        super()._set_default_mapping(trans_header)
        self.default_mapping.update({
            'login_ref': 0, 'cash_draw': 1, 'sale_area': 1, 'acc_posted': False,
            'dollardisc': 0, 'hidden': False, 'tax_table': 1, 'cust_id': 0,
            'phone_id': 0, 'gratovrpct': -99.99, 'gratovramt': -10000000000,
            'cash_back': 0, 'start_stn': 0, 'settle_stn': 0, 'waiter0': 0,
            'tray_ref': 1, 'notaxamt': 0, 'address_id': 0, 'addr_mode': 0,
            'advconvert': 0, 'printed': True
        })
        logger.info("SLS-specific default mapping initialized.")

    def transform(self, data_sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Performs data merging and transformation for SLS."""
        try:
            trans_header = data_sheets.get('Transaction Header')
            trans_sales_entry = data_sheets.get('Trans. Sales Entry')
            trans_payment_entry = data_sheets.get('Trans. Payment Entry')
            trans_infocode_entry = data_sheets.get('Trans. Infocode Entry')

            if not all([isinstance(df, pd.DataFrame) for df in [trans_header, trans_sales_entry, trans_payment_entry, trans_infocode_entry]]):
                missing_sheets = [name for name, df in zip(['Transaction Header', 'Trans. Sales Entry', 'Trans. Payment Entry', 'Trans. Infocode Entry'], [trans_header, trans_sales_entry, trans_payment_entry, trans_infocode_entry]) if not isinstance(df, pd.DataFrame)]
                logger.error(f"Missing or invalid sheets for SLS transformation: {', '.join(missing_sheets)}")
                raise ValueError(f"Missing or invalid sheets for SLS transformation: {', '.join(missing_sheets)}")

            if 'Store No.' not in trans_header.columns:
                logger.error("'Store No.' column missing in 'Transaction Header'. Cannot determine branch.")
                raise ValueError("'Store No.' column not found in 'Transaction Header' sheet. Cannot determine branch.")

            self._set_default_mapping(trans_header)

            logger.info("SLS: Filtering transaction header...")
            # Ensure 'Transaction No.' is string for robust comparison
            trans_header['Transaction No.'] = trans_header['Transaction No.'].astype(str)
            trans_sales_entry['Transaction No.'] = trans_sales_entry['Transaction No.'].astype(str)
            trans_payment_entry['Transaction No.'] = trans_payment_entry['Transaction No.'].astype(str)
            trans_infocode_entry['Transaction No.'] = trans_infocode_entry['Transaction No.'].astype(str)

            sls_df = trans_header[
                (trans_header['Transaction No.'].isin(trans_sales_entry['Transaction No.'])) &
                (trans_header['Transaction Type'] == "Sales")
            ].copy()

            # Select only necessary columns to avoid overhead
            sls_df = sls_df[[
                'Transaction No.', 'Table No.', 'No. of Covers', 'VAT Amount',
                'Income/Exp. Amount', 'Sales Type', 'Discount Amount'
            ]].copy()

            logger.info("SLS: Processing sales entry data...")
            required_tse_cols = ['Transaction No.','Staff ID','Discount Module Name','Time','Date','Price']
            tse_sls_temp = trans_sales_entry[
                trans_sales_entry['Transaction No.'].isin(sls_df['Transaction No.'])
            ].copy()

            # Ensure required columns exist, fill with pd.NA if not, before selection
            for col in required_tse_cols:
                if col not in tse_sls_temp.columns:
                    logger.warning(f"Column '{col}' not found in 'Trans. Sales Entry' for SLS. Adding as pd.NA.")
                    tse_sls_temp[col] = pd.NA

            # Now select only the columns we need, ensuring they are present
            tse_sls_temp = tse_sls_temp[required_tse_cols].copy()
            
            # Convert Price to float
            tse_sls_temp['Price'] = pd.to_numeric(tse_sls_temp['Price'], errors='coerce').fillna(0)

            # Replicate the notebook's logic for tse_sls
            tse_sls_for_merge = tse_sls_temp.copy().drop('Price', axis=1).drop_duplicates(subset=['Transaction No.'])
            tse_sls_for_merge['Price'] = tse_sls_temp.groupby('Transaction No.')['Price'].transform('sum')

            logger.info("SLS: Processing payment entry data...")
            tpe_sls = trans_payment_entry[trans_payment_entry['Transaction No.'].isin(sls_df['Transaction No.'])].copy()
            if 'Tender Type' not in tpe_sls.columns:
                tpe_sls['Tender Type'] = ''
            else:
                tpe_sls['Tender Type'] = tpe_sls['Tender Type'].astype(str)
            tpe_sls = tpe_sls[['Transaction No.','Tender Type']].drop_duplicates(subset=['Transaction No.'])

            logger.info("SLS: Processing infocode entry data...")
            tie_sls = trans_infocode_entry[
                (trans_infocode_entry['Transaction No.'].isin(sls_df['Transaction No.'])) &
                (trans_infocode_entry['Infocode'] == "1MOMENT")
            ].copy()
            if 'Information' not in tie_sls.columns:
                tie_sls['Information'] = ''
            else:
                tie_sls['Information'] = tie_sls['Information'].astype(str)
            tie_sls = tie_sls[['Transaction No.','Information']]

            logger.info("SLS: Merging dataframes...")
            merged_df = pd.merge(sls_df, tse_sls_for_merge, on='Transaction No.', how='left')
            merged_df = pd.merge(merged_df, tpe_sls, on='Transaction No.', how='left')
            merged_df = pd.merge(merged_df, tie_sls, on='Transaction No.', how='left')

            # Initial flexible type conversion for robustness
            merged_df = merged_df.convert_dtypes()

            logger.info("SLS: Applying column mapping and defaults...")
            sls_table = pd.DataFrame(index=merged_df.index, columns=self.target_columns)
            sls_table = self._apply_column_mapping_and_defaults(merged_df, sls_table)

            if 'bill_no' in sls_table.columns:
                sls_table['bill_no'] = sls_table['bill_no'].astype(str)

            return sls_table
        except Exception as e:
            logger.error(f"Error during SLS transformation: {e}", exc_info=True)
            raise

class SdetDataFrameTransformer(BaseDataFrameTransformer):
    """Transforms data for the Sales Detail (SDET) table."""
    def __init__(self, branch_mapping_df: pd.DataFrame, sdet_columns: list[str], column_mapping: dict[str, str]):
        super().__init__(branch_mapping_df, sdet_columns, column_mapping)

    def _set_default_mapping(self, trans_header: pd.DataFrame):
        super()._set_default_mapping(trans_header)
        self.default_mapping.update({
            'posted': False, 'del_code': False, 'prc_adj': False, 'two4one': False,
            'prc_lvl': 0, 'prc_lvl0': 0, 'iscoupon': False, 'item_adj': 0,
            'pricemult': 1, 'invmult': 1, 'gd_no': 0, 'adj_no': 0,
            'refundflag': False, 'cou_rec': 0, 'coupitem': False, 'hash_stat': 0
        })
        logger.info("SDET-specific default mapping initialized.")

    def transform(self, data_sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Performs data selection and transformation for SDET."""
        try:
            trans_sales_entry = data_sheets.get('Trans. Sales Entry')
            trans_header = data_sheets.get('Transaction Header')

            if not isinstance(trans_sales_entry, pd.DataFrame) or not isinstance(trans_header, pd.DataFrame):
                missing_sheets = []
                if not isinstance(trans_sales_entry, pd.DataFrame): missing_sheets.append('Trans. Sales Entry')
                if not isinstance(trans_header, pd.DataFrame): missing_sheets.append('Transaction Header')
                logger.error(f"Missing or invalid sheets for SDET transformation: {', '.join(missing_sheets)}")
                raise ValueError(f"Missing or invalid sheets for SDET transformation: {', '.join(missing_sheets)}")

            if 'Store No.' not in trans_header.columns:
                logger.error("'Store No.' column missing in 'Transaction Header'. Cannot determine branch for SDET.")
                raise ValueError("'Store No.' column not found in 'Transaction Header' sheet. Cannot determine branch for SDET.")

            self._set_default_mapping(trans_header)

            logger.info("SDET: Filtering sales entry data...")
            # Ensure 'Transaction No.' is string for robust comparison
            trans_sales_entry['Transaction No.'] = trans_sales_entry['Transaction No.'].astype(str)
            trans_header['Transaction No.'] = trans_header['Transaction No.'].astype(str)

            trans_sales_entry_filtered = trans_sales_entry[
                trans_sales_entry['Transaction No.'].isin(trans_header['Transaction No.'])
            ].copy()

            required_cols = [
                'Transaction No.', 'Item No.', 'Quantity', 'Price', 'Net Price',
                'Cost Amount', 'Staff ID', 'Discount Module Name', 'VAT Amount',
                'Discount Amount', 'Time', 'Date'
            ]
            sdet_df = trans_sales_entry_filtered[[col for col in required_cols if col in trans_sales_entry_filtered.columns]].copy()

            # Add missing required columns with NaN and coerce to numeric where applicable
            for col in required_cols:
                if col not in sdet_df.columns:
                    sdet_df[col] = np.nan

            numeric_cols = ['Quantity', 'Price', 'Net Price', 'Cost Amount', 'VAT Amount', 'Discount Amount']
            for col in numeric_cols:
                sdet_df[col] = pd.to_numeric(sdet_df[col], errors='coerce')

            sdet_df['Quantity'] = sdet_df['Quantity'].abs()
            sdet_df['Cost Amount'] = sdet_df['Cost Amount'].abs()

            # Convert all columns to string *before* applying defaults to ensure consistency
            # Specific types will be set by DataTypeConverter later.
            for col in sdet_df.columns:
                 sdet_df[col] = sdet_df[col].astype(str)

            logger.info("SDET: Applying column mapping and defaults...")
            sdet_table = pd.DataFrame(index=sdet_df.index, columns=self.target_columns)
            sdet_table = self._apply_column_mapping_and_defaults(sdet_df, sdet_table)

            # Explicitly set 'brand' and 'branch' from default mapping if they are target columns
            if 'brand' in sdet_table.columns and 'brand' in self.default_mapping and pd.isna(sdet_table['brand']).all():
                 sdet_table['brand'] = self.default_mapping['brand']
            if 'branch' in sdet_table.columns and 'branch' in self.default_mapping and pd.isna(sdet_table['branch']).all():
                 sdet_table['branch'] = self.default_mapping['branch']

            return sdet_table
        except Exception as e:
            logger.error(f"Error during SDET transformation: {e}", exc_info=True)
            raise

class DataTypeConverter:
    """Converts DataFrame columns to specified SQL-like data types."""
    def __init__(self, sql_to_pandas_dtype_map: dict[str, str]):
        self.sql_to_pandas_dtype_map = sql_to_pandas_dtype_map

    def convert_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies data type conversions."""
        logger.info("Applying final data type conversions...")
        df_copy = df.copy()

        for col, target_dtype in self.sql_to_pandas_dtype_map.items():
            if col not in df_copy.columns:
                logger.warning(f"Column '{col}' specified in dtype map not found in DataFrame. Skipping conversion.")
                continue

            try:
                if target_dtype == 'datetime64[ns]':
                    df_copy[col] = pd.to_datetime(df_copy[col], errors='coerce')
                    if 'time' in col.lower():
                        df_copy[col] = df_copy[col].dt.strftime("%H:%M:%S").replace({pd.NA: ""})
                    else:
                        df_copy[col] = df_copy[col].dt.strftime("%Y-%m-%d").replace({pd.NA: ""})
                elif target_dtype == 'int64':
                    df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0).astype('int64')
                elif target_dtype == 'float64':
                    df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0.0).astype('float64')
                elif target_dtype == 'bool':
                    true_values = [True, 1, 'True', 'true', 'TRUE', 'Y', 'y', 'Yes', 'yes']
                    false_values = [False, 0, 'False', 'false', 'FALSE', 'N', 'n', 'No', 'no', '', 'None', np.nan] # Added np.nan
                    # Convert to string for consistent comparison, then map
                    df_copy[col] = df_copy[col].apply(lambda x: str(x) if pd.notna(x) else '').astype(str).apply(
                        lambda x: True if x in [str(v) for v in true_values] else (False if x in [str(v) for v in false_values] else pd.NA)
                    )
                    df_copy[col] = df_copy[col].fillna(False).astype('boolean')
                elif target_dtype == 'object':
                    df_copy[col] = df_copy[col].astype(str).fillna('') # Fill NaN with empty string for object type
            except Exception as e:
                logger.error(f"Error converting column '{col}' to '{target_dtype}': {e}", exc_info=True)
                # Optionally, re-raise or set to a default/object type if conversion fails critically
                df_copy[col] = df_copy[col].astype(str) # Fallback to string

        logger.info("Data type conversion completed.")
        return df_copy


class DataSaver:
    """Saves processed DataFrames to CSV files."""
    def __init__(self, output_dir: str = "."):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        if not os.path.isdir(self.output_dir):
            logger.error(f"Failed to create or access output directory: {self.output_dir}")
            raise IOError(f"Output directory not accessible: {self.output_dir}")

    def save(self, df: pd.DataFrame, filename_prefix: str) -> str:
        """Saves the DataFrame to a CSV file with a dynamic filename."""
        try:
            date_col = None
            if 'bill_date' in df.columns:
                date_col = 'bill_date'
            elif 'ord_date' in df.columns:
                date_col = 'ord_date'

            last_date_str = "UNKNOWN_DATE"
            if date_col:
                # Ensure the column is indeed datetime before taking max
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                max_date = df[date_col].max()
                if pd.notna(max_date):
                    last_date_str = max_date.strftime("%m%d%y")
                else:
                    logger.warning(f"Could not determine valid date from column '{date_col}' for filename.")
            else:
                logger.warning("Neither 'bill_date' nor 'ord_date' found for dynamic filename date.")

            brand = "UNKNOWN_BRAND"
            if 'brand' in df.columns and not df['brand'].isnull().all():
                # Take the first unique brand, convert to string, then uppercase
                unique_brands = df['brand'].dropna().astype(str).unique()
                if len(unique_brands) > 0:
                    brand = unique_brands[0].upper()
                else:
                    logger.warning("Brand column found but contains only nulls or empty strings.")
            else:
                logger.warning("Brand column not found or is entirely null. Using 'UNKNOWN_BRAND'.")

            branch = "UNKNOWN_BRANCH"
            if 'branch' in df.columns and not df['branch'].isnull().all():
                # Take the first unique branch, convert to string, then uppercase and replace spaces
                unique_branches = df['branch'].dropna().astype(str).unique()
                if len(unique_branches) > 0:
                    branch = unique_branches[0].upper().replace(" ", "_")
                else:
                    logger.warning("Branch column found but contains only nulls or empty strings.")
            else:
                logger.warning("Branch column not found or is entirely null. Using 'UNKNOWN_BRANCH'.")

            output_filename = os.path.join(self.output_dir, f"{filename_prefix}_{last_date_str}_{brand}_{branch}.csv")
            logger.info(f"Saving processed data to: {output_filename}")
            df.to_csv(output_filename, index=False)
            logger.info(f"CSV file '{output_filename}' generated successfully.")
            return output_filename
        except Exception as e:
            logger.error(f"Error saving data for prefix '{filename_prefix}': {e}", exc_info=True)
            raise

class PipelineRunner:
    """Orchestrates data processing pipelines (SLS and SDET)."""
    def __init__(self,
                 data_reader: ExcelDataReader,
                 sls_transformer: 'SlsDataFrameTransformer',
                 sdet_transformer: 'SdetDataFrameTransformer',
                 sls_type_converter: DataTypeConverter,
                 sdet_type_converter: DataTypeConverter,
                 data_saver: DataSaver):
        self.data_reader = data_reader
        self.sls_transformer = sls_transformer
        self.sdet_transformer = sdet_transformer
        self.sls_type_converter = sls_type_converter
        self.sdet_type_converter = sdet_type_converter
        self.data_saver = data_saver

    def run_sls_pipeline(self, all_sheets_dict: dict[str, pd.DataFrame]) -> str:
        """Executes the SLS data pipeline."""
        logger.info("--- SLS Data Pipeline Started ---")
        try:
            processed_df = self.sls_transformer.transform(all_sheets_dict)
            logger.debug(f"\nSLS DataFrame after transformation (first 5 rows):\n{processed_df.head().to_string()}")
            logger.debug(f"\nSLS DataFrame after transformation (info):\n{processed_df.info()}")

            final_df = self.sls_type_converter.convert_types(processed_df)
            logger.debug(f"\nSLS DataFrame after type conversion (first 5 rows):\n{final_df.head().to_string()}")
            logger.debug(f"\nSLS DataFrame after type conversion (info):\n{final_df.info()}")

            output_file_path = self.data_saver.save(final_df, filename_prefix="SLS")
            logger.info("--- SLS Data Pipeline Finished ---")
            return output_file_path
        except Exception as e:
            logger.error(f"SLS Data Pipeline failed: {e}", exc_info=True)
            raise

    def run_sdet_pipeline(self, all_sheets_dict: dict[str, pd.DataFrame]) -> str:
        """Executes the SDET data pipeline."""
        logger.info("--- SDET Data Pipeline Started ---")
        try:
            processed_df = self.sdet_transformer.transform(all_sheets_dict)
            logger.debug(f"\nSDET DataFrame after transformation (first 5 rows):\n{processed_df.head().to_string()}")
            logger.debug(f"\nSDET DataFrame after transformation (info):\n{processed_df.info()}")

            final_df = self.sdet_type_converter.convert_types(processed_df)
            logger.debug(f"\nSDET DataFrame after type conversion (first 5 rows):\n{final_df.head().to_string()}")
            logger.debug(f"\nSDET DataFrame after type conversion (info):\n{final_df.info()}")

            output_file_path = self.data_saver.save(final_df, filename_prefix="SDET")
            logger.info("--- SDET Data Pipeline Finished ---")
            return output_file_path
        except Exception as e:
            logger.error(f"SDET Data Pipeline failed: {e}", exc_info=True)
            raise

    def run_all_pipelines(self) -> dict[str, str]:
        """Runs all defined pipelines."""
        logger.info("--- Starting All Data Pipelines ---")
        try:
            all_sheets_dict = self.data_reader.read_sheets()

            sls_output = self.run_sls_pipeline(all_sheets_dict)
            sdet_output = self.run_sdet_pipeline(all_sheets_dict)

            logger.info("--- All Data Pipelines Finished ---")
            return {"sls_file": sls_output, "sdet_file": sdet_output}
        except Exception as e:
            logger.critical(f"Critical error during overall pipeline execution: {e}", exc_info=True)
            raise

    def _load_config(self, config_file_path: str = "config/config.json") -> Dict[str, Any]:
        """Loads configuration from a JSON file."""
        if not os.path.exists(config_file_path):
            logger.error(f"Configuration file not found: {config_file_path}")
            raise FileNotFoundError(f"Configuration file not found at: {config_file_path}")

        try:
            with open(config_file_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Configuration loaded from {config_file_path}")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from config file '{config_file_path}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading config file '{config_file_path}': {e}")
            raise

    def _load_branch_mapping(self, branch_mapping_file_path: str = "config/branch_mapping.xlsx") -> pd.DataFrame:
        """Loads the branch mapping DataFrame from an Excel file."""
        if not os.path.exists(branch_mapping_file_path):
            logger.error(f"Branch mapping file not found: {branch_mapping_file_path}")
            raise FileNotFoundError(f"Branch mapping file not found at: {branch_mapping_file_path}")

        try:
            df = pd.read_excel(branch_mapping_file_path)
            logger.info(f"Branch mapping loaded from {branch_mapping_file_path}")
            return df
        except Exception as e:
            logger.error(f"Error reading branch mapping file '{branch_mapping_file_path}': {e}")
            raise

    @classmethod
    def from_config(cls,
                    excel_file_path: str, # Added to allow dynamic Excel file input
                    config_file_path: str = "config/config.json",
                    branch_mapping_file_path: str = "config/branch_mapping.xlsx",
                    output_directory: str = "output",
                    excel_header_row: int = 2): # Added for dynamic header row
        """Factory method to create a PipelineRunner instance from configurations."""
        logger.info(f"Initializing PipelineRunner from config for Excel file: {excel_file_path}")
        # Initialize with placeholder data_reader, it will be properly set in .execute()
        runner_instance = cls(
            data_reader=ExcelDataReader(file_path=excel_file_path, header_row=excel_header_row),
            sls_transformer=None,
            sdet_transformer=None,
            sls_type_converter=None,
            sdet_type_converter=None,
            data_saver=DataSaver(output_dir=output_directory)
        )

        config = runner_instance._load_config(config_file_path)
        branch_mapping_df = runner_instance._load_branch_mapping(branch_mapping_file_path)

        sls_config = config.get("sls", {})
        sdet_config = config.get("sdet", {})

        sls_target_columns = sls_config.get("target_columns")
        sls_column_mapping = sls_config.get("column_mapping")
        sls_sql_to_pandas_dtype_map = sls_config.get("dtype_map")

        sdet_target_columns = sdet_config.get("target_columns")
        sdet_column_mapping = sdet_config.get("column_mapping")
        sdet_sql_to_pandas_dtype_map = sdet_config.get("dtype_map")

        if not all([sls_target_columns, sls_column_mapping, sls_sql_to_pandas_dtype_map,
                    sdet_target_columns, sdet_column_mapping, sdet_sql_to_pandas_dtype_map]):
            logger.critical("Missing essential configuration parameters for SLS or SDET pipelines in config.json")
            raise ValueError("Missing essential configuration parameters for SLS or SDET pipelines in config.json")

        runner_instance.sls_transformer = SlsDataFrameTransformer(
            branch_mapping_df=branch_mapping_df.copy(), # Pass a copy to transformers to avoid unintended modifications
            sls_columns=sls_target_columns,
            column_mapping=sls_column_mapping
        )
        runner_instance.sdet_transformer = SdetDataFrameTransformer(
            branch_mapping_df=branch_mapping_df.copy(), # Pass a copy
            sdet_columns=sdet_target_columns,
            column_mapping=sdet_column_mapping
        )
        runner_instance.sls_type_converter = DataTypeConverter(
            sql_to_pandas_dtype_map=sls_sql_to_pandas_dtype_map
        )
        runner_instance.sdet_type_converter = DataTypeConverter(
            sql_to_pandas_dtype_map=sdet_sql_to_pandas_dtype_map
        )
        logger.info("PipelineRunner components instantiated successfully.")
        return runner_instance

    def execute(self) -> Dict[str, str]:
        """Executes all data processing pipelines."""
        logger.info("Starting pipeline execution with loaded configurations.")
        try:
            # The data_reader is already initialized in from_config
            all_sheets_dict = self.data_reader.read_sheets()

            sls_output = self.run_sls_pipeline(all_sheets_dict)
            sdet_output = self.run_sdet_pipeline(all_sheets_dict)

            logger.info("All pipelines executed successfully.")
            return {"sls_file": sls_output, "sdet_file": sdet_output}

        except FileNotFoundError as e:
            logger.error(f"Execution Error: {e}")
            raise
        except ValueError as e:
            logger.error(f"Data Processing Error: {e}")
            raise
        except Exception as e:
            logger.critical(f"An unexpected error occurred during pipeline execution: {e}", exc_info=True)
            raise
