#!/usr/bin/env python3
"""
IFC to FalkorDB Graph Converter - Main CLI Application

Usage:
	python import_ifc_to_falkordb.py [options]
	
Options:
	--input-dir DIR     Input directory containing IFC files (default: ./input)
	--clear-db          Clear all existing data in graph before conversion
	--force-clear       Force database clearing without user confirmation (use with --clear-db)
	--log-level LEVEL   Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
	--no-log-file       Disable file logging
	--stats             Output statistics after conversion completion

Examples:
	# Basic conversion
	python import_ifc_to_falkordb.py
	
	# Clear database with confirmation and show statistics
	python import_ifc_to_falkordb.py --clear-db --stats
	
	# Force clear database without confirmation (batch mode)
	python import_ifc_to_falkordb.py --clear-db --force-clear --stats

Contact: Taewook Kang (laputa99999@gmail.com)
"""

import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

current_dir = Path(__file__).parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(src_dir))

from src.falkordb_database import FalkorDBDatabase
from src.falkordb_graph_converter import IFCToFalkorDBConverter
from src.utils import setup_logging, get_log_file_path


def parse_arguments():
	parser = argparse.ArgumentParser(
		description='Convert IFC files to FalkorDB graph database',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog=__doc__
	)
	parser.add_argument('--input-dir', type=str, default='input',
					  help='Input directory containing IFC files (default: ./input)')
	parser.add_argument('--clear-db', action='store_true',
					  help='Clear all existing data in graph before conversion')
	parser.add_argument('--force-clear', action='store_true',
					  help='Force database clearing without user confirmation (use with --clear-db)')
	parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
					  default='INFO', help='Log level (default: INFO)')
	parser.add_argument('--no-log-file', action='store_true',
					  help='Disable file logging')
	parser.add_argument('--stats', action='store_true',
					  help='Output statistics after conversion completion')
	
	return parser.parse_args()


def load_environment():
	"""Load environment variables from .env file"""
	env_path = Path(__file__).parent / '.env'
	if env_path.exists():
		load_dotenv(env_path)
	
	# Check required environment variables
	required_vars = ['FALKORDB_HOST', 'FALKORDB_PORT', 'FALKORDB_GRAPH']
	missing_vars = []
	
	for var in required_vars:
		if not os.getenv(var):
			missing_vars.append(var)
	
	if missing_vars:
		raise EnvironmentError(f"Required environment variables not set: {', '.join(missing_vars)}")
	
	return {
		'host': os.getenv('FALKORDB_HOST'),
		'port': int(os.getenv('FALKORDB_PORT')),
		'username': os.getenv('FALKORDB_USERNAME'),
		'password': os.getenv('FALKORDB_PASSWORD'),
		'graph_name': os.getenv('FALKORDB_GRAPH')
	}


def print_banner():
	banner = """
IFC to FalkorDB Graph Converter
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
		print(f"  Nodes: {db_stats.get('total_nodes', 0):,}")
		print(f"  Relationships: {db_stats.get('total_relationships', 0):,}")
		
		if 'element_types' in stats and stats['element_types']:
			print(f"\nElement Type Distribution (Top 5):")
			sorted_types = sorted(stats['element_types'].items(), key=lambda x: x[1], reverse=True)
			for i, (element_type, count) in enumerate(sorted_types[:5]):
				print(f"  {i+1}. {element_type}: {count:,}")
		
		if 'relationship_types' in stats and stats['relationship_types']:
			print(f"\nRelationship Type Distribution:")
			for rel_type, count in stats['relationship_types'].items():
				print(f"  {rel_type}: {count:,}")


def main():
	try:
		# Parse command line arguments
		args = parse_arguments()
		
		# Print banner
		print_banner()
		
		# Setup logging
		project_dir = Path(__file__).parent
		log_file = None if args.no_log_file else get_log_file_path(project_dir)
		logger = setup_logging(args.log_level, log_file)
		
		logger.info("IFC to FalkorDB converter starting")
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
			print("\nPlease create a .env file with the following variables:")
			print("FALKORDB_HOST=localhost")
			print("FALKORDB_PORT=6379")
			print("FALKORDB_GRAPH=bim")
			print("FALKORDB_USERNAME=  # optional")
			print("FALKORDB_PASSWORD=  # optional")
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
		
		# Connect to FalkorDB database
		print(f"\nConnecting to FalkorDB database at {env_config['host']}:{env_config['port']}...")
		db = FalkorDBDatabase(
			host=env_config['host'],
			port=env_config['port'],
			username=env_config['username'],
			password=env_config['password'],
			graph_name=env_config['graph_name']
		)
		
		if not db.connect():
			logger.error("FalkorDB database connection failed")
			print("Error: Cannot connect to FalkorDB database.")
			print("Please check if FalkorDB is running and the connection parameters are correct.")
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
				print("\nWARNING: This will delete ALL existing data in the graph!")
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
				print("Clearing database...")
				if db.clear_database():
					logger.info("Database cleared successfully")
					print("Database cleared successfully!")
				else:
					logger.error("Database clear failed")
					print("Warning: Database clear failed.")
		
		# Create converter and execute
		print("\nStarting IFC file conversion...")
		converter = IFCToFalkorDBConverter(db)
		
		# Execute conversion
		results = converter.convert_directory(input_dir)
		
		# Collect statistics (optional)
		stats = None
		if args.stats:
			print("\nCollecting statistics...")
			stats = converter.get_conversion_statistics()
		
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
