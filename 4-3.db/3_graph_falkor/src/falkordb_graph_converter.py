"""
IFC to FalkorDB graph conversion logic implementation

Contact: Taewook Kang (laputa99999@gmail.com)
"""
import logging
from typing import Dict, List, Any
from pathlib import Path
from .ifc_parser import IFCParser
from .falkordb_database import FalkorDBDatabase


class IFCToFalkorDBConverter:
	"""Main class for converting IFC data to FalkorDB graph"""
	
	def __init__(self, db: FalkorDBDatabase):
		"""
		Initialize converter
		
		Args:
			db: FalkorDB database instance
		"""
		self.logger = logging.getLogger(__name__)
		self.parser = IFCParser()
		self.db = db
		
	def convert_file(self, ifc_file_path: Path) -> bool:
		"""
		Convert single IFC file to FalkorDB graph
		
		Args:
			ifc_file_path: IFC file path
			
		Returns:
			Conversion success status
		"""
		try:
			self.logger.info(f"Starting IFC file conversion: {ifc_file_path}")
			
			# 1. Create file metadata node first
			file_id = self.db.create_file_node(ifc_file_path)
			if not file_id:
				self.logger.error(f"File metadata creation failed: {ifc_file_path}")
				return False
			
			# 2. Parse IFC file
			ifc_file = self.parser.parse_file(ifc_file_path)
			if not ifc_file:
				self.logger.error(f"IFC file parsing failed: {ifc_file_path}")
				return False
			
			# 3. Extract and convert elements
			elements = self.parser.extract_elements(ifc_file)
			if not elements:
				self.logger.warning(f"No elements extracted: {ifc_file_path}")
				return False
			
			# 4. Convert elements to nodes with file reference
			element_success_count = 0
			for element in elements:
				if self.db.create_element_node(element, file_id):
					element_success_count += 1
					
			self.logger.info(f"Element nodes creation completed: {element_success_count}/{len(elements)}")
			
			# 5. Extract and convert relationships
			relationships = self.parser.extract_relationships(ifc_file)
			if relationships:
				relationship_success_count = 0
				for relationship in relationships:
					if self.db.create_relationship(relationship):
						relationship_success_count += 1
						
				self.logger.info(f"Relationships creation completed: {relationship_success_count}/{len(relationships)}")
			else:
				self.logger.info("No relationships extracted.")
			
			self.logger.info(f"IFC file conversion completed: {ifc_file_path}")
			return True
			
		except Exception as e:
			self.logger.error(f"Error during IFC file conversion: {ifc_file_path}, error: {e}")
			return False
	
	def convert_directory(self, input_directory: Path, file_pattern: str = "*.ifc") -> Dict[str, bool]:
		"""
		Convert all IFC files in directory
		
		Args:
			input_directory: Input directory path
			file_pattern: File pattern (default: "*.ifc")
			
		Returns:
			Dictionary of conversion results by file
		"""
		results = {}
		
		try:
			# Search for IFC files
			ifc_files = list(input_directory.glob(file_pattern))
			
			if not ifc_files:
				self.logger.warning(f"No IFC files found: {input_directory}")
				return results
			
			self.logger.info(f"Found {len(ifc_files)} IFC files")
			
			# Convert each file
			for ifc_file in ifc_files:
				self.logger.info(f"Processing file: {ifc_file.name}")
				success = self.convert_file(ifc_file)
				results[str(ifc_file)] = success
				
				if success:
					self.logger.info(f"File conversion successful: {ifc_file.name}")
				else:
					self.logger.error(f"File conversion failed: {ifc_file.name}")
			
			return results
			
		except Exception as e:
			self.logger.error(f"Error during directory conversion: {e}")
			return results
	
	def get_conversion_statistics(self) -> Dict[str, Any]:
		"""
		Get conversion statistics
		
		Returns:
			Statistics dictionary
		"""
		try:
			stats = self.db.get_statistics()
			
			return {
				'database_stats': stats,
				'element_types': stats.get('element_types', {}),
				'relationship_types': stats.get('relationship_types', {})
			}
		except Exception as e:
			self.logger.error(f"Statistics collection failed: {e}")
			return {}
