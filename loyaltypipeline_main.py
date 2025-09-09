import os
import shutil # Import shutil for moving files
from LoyaltyPipeline2 import PipelineRunner
import glob # Import glob for pattern matching file names

# Define directories
input_folder = "for upload"
output_dir = "output"
uploaded_folder = "uploaded" # New folder for processed files
config_dir = "config"

# Ensure directories exist
os.makedirs(input_folder, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)
os.makedirs(uploaded_folder, exist_ok=True)
os.makedirs(config_dir, exist_ok=True) # Ensure config directory exists for dummy files

print(f"Checking for Excel files in: {input_folder}")

# Get a list of all Excel files in the 'for upload' folder
excel_files_to_process = glob.glob(os.path.join(input_folder, "*.xlsx"))
if not excel_files_to_process:
    print(f"No Excel files found in '{input_folder}'. Exiting.")
else:
    print(f"Found {len(excel_files_to_process)} Excel file(s) to process.")

for excel_file_path in excel_files_to_process:
    file_name = os.path.basename(excel_file_path)
    print(f"\n--- Processing '{file_name}' ---")

    try:
        # 1. Instantiate the PipelineRunner using the factory method
        # This loads all necessary configurations and initializes transformers/converters
        pipeline_orchestrator = PipelineRunner.from_config(
            excel_file_path=excel_file_path, # Use the current file path
            config_file_path=os.path.join(config_dir, "config.json"),
            branch_mapping_file_path=os.path.join(config_dir, "branch_mapping.xlsx"),
            output_directory=output_dir
        )

        # 2. Execute the pipelines
        output_files = pipeline_orchestrator.execute()

        print(f"Successfully completed pipelines for '{file_name}'. Output files:")
        print(f"SLS Output: {output_files.get('sls_file', 'N/A')}")
        print(f"SDET Output: {output_files.get('sdet_file', 'N/A')}")

        # Move the processed file to the 'uploaded' folder
        destination_path = os.path.join(uploaded_folder, file_name)
        shutil.move(excel_file_path, destination_path)
        print(f"Moved '{file_name}' to '{uploaded_folder}'.")

    except FileNotFoundError as e:
        print(f"Execution failed for '{file_name}' due to missing file: {e}")
    except ValueError as e:
        print(f"Execution failed for '{file_name}' due to configuration or data issue: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during execution for '{file_name}': {e}")

print("\n--- All specified Excel files processed or attempted. ---")

#For 1 file
'''
import os
from your_module import PipelineRunner # Assuming PipelineRunner is in 'your_module.py'
Make sure 'output' directory exists or will be created by DataSaver
from LoyaltyPipeline import PipelineRunner
input_excel_file = "Manam GH August 1-28, 2025.xlsx"
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)
os.makedirs("config", exist_ok=True) # Ensure config directory exists for dummy files
try:
# 1. Instantiate the PipelineRunner using the factory method
# This loads all necessary configurations and initializes transformers/converters
pipeline_orchestrator = PipelineRunner.from_config(
excel_file_path = input_excel_file,
config_file_path="config/config.json",
branch_mapping_file_path="config/branch_mapping.xlsx",
output_directory=output_dir
)
code
Code
# 2. Execute the pipelines with a specific input Excel file

output_files = pipeline_orchestrator.execute()

print(f"\nSuccessfully completed pipelines. Output files:")
print(f"SLS Output: {output_files.get('sls_file', 'N/A')}")
print(f"SDET Output: {output_files.get('sdet_file', 'N/A')}")
except FileNotFoundError as e:
print(f"Execution failed due to missing file: {e}")
except ValueError as e:
print(f"Execution failed due to configuration or data issue: {e}")
except Exception as e:
print(f"An unexpected error occurred during execution: {e}")
'''