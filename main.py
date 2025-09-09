#!/usr/bin/env python3
"""
POS Data Processing Tool - Main Application
Project Genesis - Phase 1

Terminal-based Python application that processes Point-of-Sale (POS) data.
Navigates POS Data directory structure, processes raw transtable files for multiple shops,
and generates cleaned sdet.csv and sls.csv reports using the LoyaltyPipeline.

Usage:
    python main.py                              # Process all brands and shops
    python main.py --brand BrandName            # Process all shops for a specific brand  
    python main.py --brand BrandName --shop ShopName   # Process specific brand and shop
"""

import argparse
import sys
import logging
from orchestrator import POSDataOrchestrator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description='POS Data Processing Tool - Process transtable files and generate sdet/sls reports',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    Process all brands and shops (both SLS and SDET)
  %(prog)s --brand Manam                     Process all shops for Manam brand
  %(prog)s --brand Manam --shop Cebu         Process only Manam Cebu shop
  %(prog)s --brand Manam --shop Cebu --shop Greenhills  Process Manam Cebu and Greenhills shops
  %(prog)s --pipeline sls                    Generate only SLS files for all brands/shops
  %(prog)s --pipeline sdet                   Generate only SDET files for all brands/shops
  %(prog)s --pipeline sls --pipeline sdet    Generate both SLS and SDET files (same as default)
  %(prog)s --brand Manam --pipeline sls      Generate only SLS files for Manam brand
  %(prog)s --brand Manam --shop Cebu --pipeline sdet  Generate only SDET files for Manam Cebu
  %(prog)s --month September --year 2025     Process files for a specific month and year (default: current)
  %(prog)s --list-brands                     Show available brands
  %(prog)s --list-shops --brand Manam        Show available shops for Manam brand
        """
    )
    parser.add_argument(
        '--month',
        type=str,
        help='Specify the month to process (e.g., September or 09). Defaults to current month.'
    )
    parser.add_argument(
        '--year',
        type=str,
        help='Specify the year to process (e.g., 2025). Defaults to current year.'
    )
    
    parser.add_argument(
        '--brand',
        type=str,
        help='Process files for a specific brand only'
    )
    
    parser.add_argument(
        '--shop',
        type=str,
        action='append',
        help='Process files for specific shop(s) (requires --brand). Can be used multiple times to specify multiple shops.'
    )
    
    parser.add_argument(
        '--pipeline',
        choices=['sls', 'sdet'],
        action='append',
        help='Specify which pipeline(s) to run. Can be used multiple times. Default: both sls and sdet'
    )
    
    parser.add_argument(
        '--list-brands',
        action='store_true',
        help='List all available brands and exit'
    )
    
    parser.add_argument(
        '--list-shops',
        action='store_true',
        help='List all available shops for a brand (requires --brand) and exit'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser


def validate_arguments(args, orchestrator: POSDataOrchestrator) -> bool:
    """
    Validate command line arguments.
    
    Args:
        args: Parsed command line arguments
        orchestrator: POSDataOrchestrator instance
        
    Returns:
        True if arguments are valid, False otherwise
    """
    # If shop is specified, brand must also be specified
    if args.shop and not args.brand:
        logger.error("Error: --shop requires --brand to be specified")
        return False
    
    # If list-shops is specified, brand must also be specified
    if args.list_shops and not args.brand:
        logger.error("Error: --list-shops requires --brand to be specified")
        return False
    
    # If brand and shops are specified, validate they exist
    if args.brand and args.shop:
        for shop in args.shop:
            is_valid, error_message = orchestrator.validate_brand_shop(args.brand, shop)
            if not is_valid:
                logger.error(f"Error: {error_message}")
                return False
    
    # If only brand is specified, validate it exists
    elif args.brand:
        available_brands = orchestrator.get_available_brands()
        if args.brand not in available_brands:
            logger.error(f"Error: Brand '{args.brand}' not found. Available brands: {', '.join(available_brands)}")
            return False
    
    return True


def handle_list_commands(args, orchestrator: POSDataOrchestrator) -> bool:
    """
    Handle list commands (--list-brands, --list-shops).
    
    Args:
        args: Parsed command line arguments
        orchestrator: POSDataOrchestrator instance
        
    Returns:
        True if a list command was executed, False otherwise
    """
    if args.list_brands:
        brands = orchestrator.get_available_brands()
        print("\n📋 Available Brands:")
        for brand in brands:
            shops = orchestrator.get_available_shops(brand)
            print(f"  • {brand} ({len(shops)} shops: {', '.join(shops)})")
        print()
        return True
    
    if args.list_shops:
        shops = orchestrator.get_available_shops(args.brand)
        print(f"\n📋 Available Shops for '{args.brand}':")
        for shop in shops:
            print(f"  • {shop}")
        print()
        return True
    
    return False


def print_processing_summary(results, pipeline_types: list = None) -> None:
    """Print a summary of processing results."""
    total_files = 0
    total_shops = 0
    total_brands = 0
    
    if isinstance(results, dict):
        if any(isinstance(v, dict) for v in results.values()):
            # Full run or brand run - results[brand][shop] = [files]
            for brand, shops in results.items():
                if isinstance(shops, dict):
                    total_brands += 1
                    for shop, files in shops.items():
                        total_shops += 1
                        total_files += len(files)
        else:
            # Single shop run - results[shop] = [files]  
            total_shops = len(results)
            total_files = sum(len(files) for files in results.values())
    elif isinstance(results, list):
        # Single shop, single result
        total_files = len(results)
        total_shops = 1
    
    pipeline_str = ', '.join(pipeline_types).upper() if pipeline_types else 'SLS, SDET'
    
    print(f"\n📊 Processing Summary:")
    if total_brands > 0:
        print(f"  • Brands processed: {total_brands}")
    print(f"  • Shops processed: {total_shops}")
    print(f"  • Files processed: {total_files}")
    print(f"  • Pipeline types: {pipeline_str}")


def main():
    """Main application entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Initialize orchestrator
        logger.info("🚀 Initializing POS Data Processing Tool")
        orchestrator = POSDataOrchestrator()

        # Validate arguments
        if not validate_arguments(args, orchestrator):
            sys.exit(1)

        # Handle list commands
        if handle_list_commands(args, orchestrator):
            sys.exit(0)

        # Determine pipeline types
        pipeline_types = args.pipeline if args.pipeline else ['sls', 'sdet']
        pipeline_str = ', '.join(pipeline_types).upper()

        # Month/year selection
        from datetime import datetime
        now = datetime.now()
        month = args.month if args.month else now.strftime('%B')
        year = args.year if args.year else str(now.year)

        # Determine processing mode and execute
        results = None

        if args.brand and args.shop:
            # Targeted run - specific brand and shop(s)
            if len(args.shop) == 1:
                logger.info(f"🎯 Mode: Targeted Processing - {args.brand} → {args.shop[0]} ({pipeline_str}) [{month} {year}]")
                results = orchestrator.process_shop(args.brand, args.shop[0], pipeline_types, month=month, year=year)
            else:
                shops_str = ', '.join(args.shop)
                logger.info(f"🎯 Mode: Multi-Shop Processing - {args.brand} → {shops_str} ({pipeline_str}) [{month} {year}]")
                results = {}
                for shop in args.shop:
                    logger.info(f"\n=== Processing {args.brand} - {shop} ({month} {year}) ===")
                    shop_results = orchestrator.process_shop(args.brand, shop, pipeline_types, month=month, year=year)
                    results[shop] = shop_results

        elif args.brand:
            # Brand run - all shops for specific brand
            logger.info(f"🏢 Mode: Brand Processing - {args.brand} ({pipeline_str}) [{month} {year}]")
            results = orchestrator.process_brand(args.brand, pipeline_types, month=month, year=year)

        else:
            # Full run - all brands and shops
            logger.info(f"🌐 Mode: Full Processing - All Brands and Shops ({pipeline_str}) [{month} {year}]")
            results = orchestrator.process_all(pipeline_types, month=month, year=year)

        # Print summary
        print_processing_summary(results, pipeline_types)

        logger.info("✅ POS Data Processing completed successfully!")

    except FileNotFoundError as e:
        logger.error(f"❌ File not found: {e}")
        sys.exit(1)

    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("⏹️  Processing interrupted by user")
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
