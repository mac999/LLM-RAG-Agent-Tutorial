#!/usr/bin/env python3
"""
IFC to Neo4j Graph Converter - Main CLI Application

Usage:
    python import_ifc.py [options]
    
Options:
    --input-dir DIR     Input directory containing IFC files (default: ./input)
    --clear-db          Clear all existing data in elements database before conversion
    --force-clear       Force database clearing without user confirmation (use with --clear-db)
    --log-level LEVEL   Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    --no-log-file       Disable file logging
    --validate          Run validation after conversion
    --stats             Output statistics after conversion completion

Examples:
    # Basic conversion
    python import_ifc.py
    
    # Clear database with confirmation and show statistics
    python import_ifc.py --clear-db --stats
    
    # Force clear database without confirmation (batch mode)
    python import_ifc.py --clear-db --force-clear --stats
"""

import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import json

# 현재 디렉토리를 모듈 경로에 추가
current_dir = Path(__file__).parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(src_dir))

from src.neo4j_database import Neo4jDatabase
from src.graph_converter import IFCToGraphConverter
from src.utils import setup_logging, get_log_file_path


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Convert IFC files to Neo4j graph database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--input-dir', 
        type=str, 
        default='input',
        help='Input directory containing IFC files (default: ./input)'
    )
    
    parser.add_argument(
        '--clear-db', 
        action='store_true',
        help='Clear all existing data in the elements database before conversion (WARNING: This will delete all nodes and relationships!)'
    )
    
    parser.add_argument(
        '--force-clear', 
        action='store_true',
        help='Force database clearing without user confirmation (use with --clear-db)'
    )
    
    parser.add_argument(
        '--log-level', 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Log level (default: INFO)'
    )
    
    parser.add_argument(
        '--no-log-file', 
        action='store_true',
        help='Disable file logging'
    )
    
    parser.add_argument(
        '--validate', 
        action='store_true',
        help='Run validation after conversion'
    )
    
    parser.add_argument(
        '--stats', 
        action='store_true',
        help='Output statistics after conversion completion'
    )
    
    return parser.parse_args()


def load_environment():
    """Load environment variables"""
    # Load environment variables from .env file
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    # Check required environment variables
    required_vars = ['NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD', 'NEO4J_DATABASE']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise EnvironmentError(f"Required environment variables not set: {', '.join(missing_vars)}")
    
    return {
        'uri': os.getenv('NEO4J_URI'),
        'user': os.getenv('NEO4J_USER'),
        'password': os.getenv('NEO4J_PASSWORD'),
        'database': os.getenv('NEO4J_DATABASE')
    }


def print_banner():
    """Print application start banner"""
    banner = """
IFC to Neo4j Graph Converter
BIM Graph Data Importer v1.0.0
"""
    print(banner)


def print_summary(results: dict, stats: dict = None):
    """Print conversion result summary"""
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    print("\nConversion Result Summary")
    print(f"Total files: {total_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {total_count - success_count}")
    print(f"Success rate: {(success_count/total_count*100):.1f}%" if total_count > 0 else "0%")
    
    # List of failed files
    failed_files = [file_path for file_path, success in results.items() if not success]
    if failed_files:
        print("\nFailed files:")
        for file_path in failed_files:
            print(f"  {Path(file_path).name}")
    
    # Output statistics information
    if stats and 'database_stats' in stats:
        db_stats = stats['database_stats']
        print(f"\nDatabase Statistics:")
        print(f"  Nodes: {db_stats['total_nodes']:,}")
        print(f"  Relationships: {db_stats['total_relationships']:,}")
        
        if 'element_types' in stats and stats['element_types']:
            print(f"\nElement Type Distribution (Top 5):")
            sorted_types = sorted(stats['element_types'].items(), key=lambda x: x[1], reverse=True)
            for i, (element_type, count) in enumerate(sorted_types[:5]):
                print(f"  {i+1}. {element_type}: {count:,}")
        
        if 'relationship_types' in stats and stats['relationship_types']:
            print(f"\nRelationship Type Distribution:")
            for rel_type, count in stats['relationship_types'].items():
                print(f"  {rel_type}: {count:,}")


def validate_conversion(converter: IFCToGraphConverter, input_dir: Path):
    """Validate conversion results"""
    print("\nValidating conversion results...")
    
    # Run validation only for the first IFC file
    ifc_files = list(input_dir.glob("*.ifc"))
    if ifc_files:
        validation_result = converter.validate_conversion(ifc_files[0])
        
        if 'error' not in validation_result:
            print(f"Validation Results:")
            print(f"  Original elements: {validation_result['original_elements_count']:,}")
            print(f"  Original relationships: {validation_result['original_relationships_count']:,}")
            print(f"  DB nodes: {validation_result['db_nodes_count']:,}")
            print(f"  DB relationships: {validation_result['db_relationships_count']:,}")
            print(f"  Elements match: {'Yes' if validation_result['elements_match'] else 'No'}")
            print(f"  Relationships match: {'Yes' if validation_result['relationships_match'] else 'No'}")
        else:
            print(f"Validation failed: {validation_result['error']}")


def main():
    """Main function"""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Print banner
        print_banner()
        
        # Setup logging
        project_dir = Path(__file__).parent
        log_file = None if args.no_log_file else get_log_file_path(project_dir)
        logger = setup_logging(args.log_level, log_file)
        
        logger.info("IFC to Neo4j converter starting")
        logger.info(f"Log level: {args.log_level}")
        if log_file:
            logger.info(f"Log file: {log_file}")
        
        # Load environment variables
        try:
            env_config = load_environment()
            logger.info("Environment variables loaded successfully")
        except EnvironmentError as e:
            logger.error(f"Environment variable loading failed: {e}")
            print(f"Error: {e}")
            return 1
        
        # Check input directory
        input_dir = Path(args.input_dir)
        if not input_dir.exists():
            logger.error(f"Input directory does not exist: {input_dir}")
            print(f"Error: Input directory not found: {input_dir}")
            return 1
        
        logger.info(f"Input directory: {input_dir.absolute()}")
        
        # Check IFC files
        ifc_files = list(input_dir.glob("*.ifc"))
        if not ifc_files:
            logger.warning(f"No IFC files found: {input_dir}")
            print(f"Warning: No IFC files found: {input_dir}")
            return 0
        
        print(f"Found IFC files: {len(ifc_files)} files")
        for ifc_file in ifc_files:
            print(f"  {ifc_file.name}")
        
        # Connect to Neo4j database
        print("\nConnecting to Neo4j database...")
        db = Neo4jDatabase(
            uri=env_config['uri'],
            user=env_config['user'],
            password=env_config['password'],
            database=env_config['database']
        )
        
        if not db.connect():
            logger.error("Neo4j database connection failed")
            print("Error: Cannot connect to Neo4j database.")
            return 1
        
        print("Database connection successful!")
        
        # Initialize database (optional)
        if args.clear_db:
            should_clear = False
            
            if args.force_clear:
                # Force clear without confirmation
                should_clear = True
                logger.info("Force clearing database without user confirmation")
                print("\nForce clearing database (--force-clear option enabled)...")
            else:
                # Ask for user confirmation
                print("\nWARNING: This will delete ALL existing data in the elements database!")
                print("All nodes and relationships will be permanently removed.")
                
                while True:
                    response = input("Do you want to continue? (yes/no): ").lower().strip()
                    if response in ['yes', 'y']:
                        should_clear = True
                        break
                    elif response in ['no', 'n']:
                        print("Database initialization cancelled.")
                        logger.info("Database initialization cancelled by user")
                        print("Proceeding with conversion without clearing database...")
                        break
                    else:
                        print("Please enter 'yes' or 'no'")
            
            if should_clear:
                print("Initializing database...")
                if db.clear_database():
                    logger.info("Database initialization completed")
                    print("Database initialization completed!")
                else:
                    logger.error("Database initialization failed")
                    print("Warning: Database initialization failed.")
        
        # Create converter and execute
        print("\nStarting IFC file conversion...")
        converter = IFCToGraphConverter(db)
        
        # Execute conversion
        results = converter.convert_directory(input_dir)
        
        # Collect statistics (optional)
        stats = None
        if args.stats:
            print("\nCollecting statistics...")
            stats = converter.get_conversion_statistics()
        
        # Run validation (optional)
        if args.validate and results:
            validate_conversion(converter, input_dir)
        
        # Print result summary
        print_summary(results, stats)
        
        # Close database connection
        db.close()
        
        # Determine exit code
        success_count = sum(1 for success in results.values() if success)
        if success_count == len(results) and len(results) > 0:
            logger.info("All files converted successfully")
            print("\nAll files have been successfully converted!")
            return 0
        elif success_count > 0:
            logger.info(f"Some files converted successfully: {success_count}/{len(results)}")
            print(f"\nSome files were converted: {success_count}/{len(results)}")
            return 0
        else:
            logger.error("All file conversions failed")
            print("\nAll file conversions failed.")
            return 1
    
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user.")
        return 130
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())