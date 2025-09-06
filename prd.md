Product Requirements Document (PRD)
1. Introduction
1.1 Project Name
POS Data Processing Tool (Project "Genesis")

1.2 Purpose
This document outlines the requirements for a terminal-based Python application that processes Point-of-Sale (POS) data. The tool will navigate a pre-defined directory structure, process raw transtable files for multiple shops, and generate cleaned sdet.csv and sls.csv reports. The actual data cleaning logic is handled by an existing script, LoyaltyPipeline.py, which our new application will orchestrate.

1.3 Scope
This document details Phase 1 of the project. The primary goal is to build the application's framework. This involves creating a main script (main.py) that can process either all shops or a specific shop, using the PipelineRunner class from LoyaltyPipeline.py to handle the data transformation. We will also set up the necessary configuration files (settings.py, config.json, and branch_mapping.xlsx) required by the pipeline.

2. User Stories
As a developer, I want to use a central configuration file (settings.py) so I can easily add or remove shops without modifying the core application logic.

As a user, I want to run a single command from the terminal to process all shops listed in the settings.

As a user, I want to run a single command from the terminal to process a specific shop within a brand.

As a developer, I need to integrate with the existing LoyaltyPipeline.py script to use its sdet_cleaner and sls_cleaner methods.

As a user, I want the processed files (sdet.csv, sls.csv) to be placed in their respective sdet and sls folders for each shop.

3. Functional Requirements
3.1 settings.py Configuration
The application MUST read a list of brands and their corresponding shops from a settings.py file.

The structure of the configuration file will be a Python list of dictionaries, for example:

Python

POS_SHOPS = [
    {"brand": "BrandA", "shops": ["Shop101", "Shop102"]},
    {"brand": "BrandB", "shops": ["Shop201", "Shop202"]},
]
3.2 File and Folder Structure
The application MUST assume the following directory structure:
POS Data/ <Brand> / <Shop> / transtable/
POS Data/ <Brand> / <Shop> / sdet/
POS Data/ <Brand> / <Shop> / sls/

The script MUST create the sdet and sls directories if they do not exist.

The main.py script MUST locate the relevant raw data file (e.g., .xlsx or .xls) within the transtable folder for each shop.

The application will require a new config directory containing two files:

config.json: Contains column mappings and data type configurations for the pipeline.

branch_mapping.xlsx: Maps Store No. to brand and branch.

3.3 Main Application (main.py)
The application MUST be run from the terminal using python main.py or by providing specific arguments for brand and shop.

main.py MUST use the argparse library to handle command-line arguments.

The application MUST support two modes of operation:

Full Run: If no arguments are provided, it will iterate through every brand and shop listed in settings.py.

Targeted Run: If --brand and --shop arguments are provided, it will process only the specified shop.

For each shop being processed, main.py MUST:

Construct the path to the transtable file.

Construct the path for the output sdet and sls folders.

Instantiate the LoyaltyPipeline.PipelineRunner class using the from_config() factory method, passing the paths to the transtable file and output folders.

Call the run_sdet_pipeline() and run_sls_pipeline() methods on the instantiated PipelineRunner object to execute the data processing.

The application MUST print status messages to the terminal to inform the user which shop is being processed and a final message upon completion.

4. Technical Requirements
Language: Python updated

Dependencies: pandas, numpy, and openpyxl (or xlrd) are required by LoyaltyPipeline.py. Our main application will also require argparse.

Execution Environment: The application is designed to be run from a command-line interface.

5. Non-Functional Requirements
Maintainability: The codebase should be clean, well-commented, and logically structured for future enhancements. Separating file system logic (main.py) from data processing logic (LoyaltyPipeline.py) is key.

Scalability: The design with settings.py makes it simple to scale by adding more brands and shops to the configuration list.

Error Handling: (Future Phase) Basic error handling will be implemented to manage cases where specified brands/shops are not found or a transtable file is missing.