"""
IFC to Neo4j graph conversion logic implementation

Contact: Taewook Kang (laputa99999@gmail.com)
"""
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from .ifc_parser import IFCParser
from .neo4j_database import Neo4jDatabase

class IFCToGraphConverter:
	"""Main class for converting IFC data to Neo4j graph"""
	
	def __init__(self, neo4j_db: Neo4jDatabase):
		"""
		Initialize converter
		
		Args:
			neo4j_db: Neo4j database instance
		"""
		self.logger = logging.getLogger(__name__)
		self.parser = IFCParser()
		self.db = neo4j_db
		
	def convert_file(self, ifc_file_path: Path) -> bool:
		"""
		Convert single IFC file to Neo4j graph
		
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
			
			# 4. Convert elements to Neo4j nodes with file reference
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
			
			self.logger.info(f"Found {len(ifc_files)} IFC files in total.")
			
			# Process each file sequentially
			for ifc_file in ifc_files:
				try:
					result = self.convert_file(ifc_file)
					results[str(ifc_file)] = result
					
					if result:
						self.logger.info(f"Conversion successful: {ifc_file.name}")
					else:
						self.logger.error(f"Conversion failed: {ifc_file.name}")
						
				except Exception as e:
					self.logger.error(f"Error processing file: {ifc_file.name}, error: {e}")
					results[str(ifc_file)] = False
					continue
			
			# Conversion result summary
			success_count = sum(1 for success in results.values() if success)
			total_count = len(results)
			
			self.logger.info(f"Conversion completed - successful: {success_count}/{total_count}")
			
			return results
			
		except Exception as e:
			self.logger.error(f"Error during directory conversion: {input_directory}, error: {e}")
			return results
	
	def get_conversion_statistics(self) -> Dict[str, Any]:
		"""
		Return conversion result statistics
		
		Returns:
			Statistics information dictionary
		"""
		try:
			stats = self.db.get_stats()
			
			# Calculate additional statistics
			detailed_stats = {
				'database_stats': stats,
				'element_types': self._get_element_type_distribution(),
				'relationship_types': self._get_relationship_type_distribution()
			}
			
			return detailed_stats
			
		except Exception as e:
			self.logger.error(f"Statistics collection failed: {e}")
			return {}
	
	def _get_element_type_distribution(self) -> Dict[str, int]:
		"""
		Query element type distribution
		
		Returns:
			Dictionary of element count by type
		"""
		try:
			with self.db.driver.session(database=self.db.database) as session:
				result = session.run("""
				MATCH (n:Element)
				RETURN n.ifcClass as elementType, count(n) as count
				ORDER BY count DESC
				""")
				
				distribution = {}
				for record in result:
					distribution[record['elementType']] = record['count']
				
				return distribution
				
		except Exception as e:
			self.logger.error(f"Element type distribution query failed: {e}")
			return {}
	
	def _get_relationship_type_distribution(self) -> Dict[str, int]:
		"""
		Query relationship type distribution
		
		Returns:
			Dictionary of relationship count by type
		"""
		try:
			with self.db.driver.session(database=self.db.database) as session:
				result = session.run("""
				MATCH ()-[r]->()
				RETURN type(r) as relationshipType, count(r) as count
				ORDER BY count DESC
				""")
				
				distribution = {}
				for record in result:
					distribution[record['relationshipType']] = record['count']
				
				return distribution
				
		except Exception as e:
			self.logger.error(f"Relationship type distribution query failed: {e}")
			return {}
	
	def validate_conversion(self, ifc_file_path: Path) -> Dict[str, Any]:
		"""
		Validate conversion results
		
		Args:
			ifc_file_path: IFC file path to validate
			
		Returns:
			Validation result dictionary
		"""
		try:
			self.logger.info(f"Starting conversion validation: {ifc_file_path}")
			
			# Check element and relationship count from original IFC file
			ifc_file = self.parser.parse_file(ifc_file_path)
			if not ifc_file:
				return {'error': 'IFC file parsing failed'}
			
			original_elements = self.parser.extract_elements(ifc_file)
			original_relationships = self.parser.extract_relationships(ifc_file)
			
			# Check data from the same file in Neo4j
			# (Using overall statistics as file-specific distinction is difficult)
			db_stats = self.db.get_stats()
			
			validation_result = {
				'original_elements_count': len(original_elements),
				'original_relationships_count': len(original_relationships),
				'db_nodes_count': db_stats['total_nodes'],
				'db_relationships_count': db_stats['total_relationships'],
				'element_types': self._get_element_type_distribution(),
				'relationship_types': self._get_relationship_type_distribution()
			}
			
			# Basic consistency check
			validation_result['elements_match'] = validation_result['original_elements_count'] <= validation_result['db_nodes_count']
			validation_result['relationships_match'] = validation_result['original_relationships_count'] <= validation_result['db_relationships_count']
			
			self.logger.info(f"Conversion validation completed: {ifc_file_path}")
			return validation_result
			
		except Exception as e:
			self.logger.error(f"Error during conversion validation: {ifc_file_path}, error: {e}")
			return {'error': str(e)}