"""
FalkorDB database connection and data processing module

Contact: Taewook Kang (laputa99999@gmail.com)
"""
import logging
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from falkordb import FalkorDB


class FalkorDBDatabase:
	"""FalkorDB database connection and data management class"""
	
	def __init__(self, host: str, port: int, username: str = None, password: str = None, graph_name: str = "bim"):
		"""
		Initialize FalkorDB database connection
		
		Args:
			host: FalkorDB server host
			port: FalkorDB server port
			username: Username (optional)
			password: Password (optional)
			graph_name: Graph name
		"""
		self.logger = logging.getLogger(__name__)
		self.host = host
		self.port = port
		self.username = username
		self.password = password
		self.graph_name = graph_name
		self.client = None
		self.graph = None
		
	def connect(self) -> bool:
		"""
		Connect to FalkorDB database
		
		Returns:
			Connection success status
		"""
		try:
			self.client = FalkorDB(
				host=self.host,
				port=self.port,
				username=self.username,
				password=self.password
			)
			self.graph = self.client.select_graph(self.graph_name)
			
			# Connection test
			self.graph.query("RETURN 1")
			self.logger.info(f"FalkorDB connection successful: {self.host}:{self.port}/{self.graph_name}")
			return True
		except Exception as e:
			self.logger.error(f"FalkorDB connection failed: {e}")
			return False
	
	def close(self):
		"""Close database connection"""
		if self.client:
			self.client = None
			self.graph = None
			self.logger.info("FalkorDB connection closed")
	
	def clear_database(self) -> bool:
		"""
		Clear all data in the graph
		
		Returns:
			Success status
		"""
		try:
			self.graph.query("MATCH (n) DETACH DELETE n")
			self.logger.info("Database cleared successfully")
			return True
		except Exception as e:
			self.logger.error(f"Database clear failed: {e}")
			return False
	
	def create_file_node(self, file_path: Path) -> Optional[str]:
		"""
		Create IFC file metadata node
		
		Args:
			file_path: Path to the IFC file
			
		Returns:
			File ID if successful, None otherwise
		"""
		try:
			stat = file_path.stat()
			file_id = f"FILE_{file_path.stem}_{int(stat.st_mtime)}"
			
			file_data = {
				'fileId': file_id,
				'fileName': file_path.name,
				'filePath': str(file_path.absolute()),
				'fileSize': stat.st_size,
				'createdDate': datetime.fromtimestamp(stat.st_ctime).isoformat(),
				'modifiedDate': datetime.fromtimestamp(stat.st_mtime).isoformat(),
				'importDate': datetime.now().isoformat()
			}
			
			query = """
			MERGE (f:IFCFile {fileId: $fileId})
			SET f.fileName = $fileName,
				f.filePath = $filePath,
				f.fileSize = $fileSize,
				f.createdDate = $createdDate,
				f.modifiedDate = $modifiedDate,
				f.importDate = $importDate
			RETURN f.fileId
			"""
			
			params = {
				'fileId': file_id,
				'fileName': file_data['fileName'],
				'filePath': file_data['filePath'],
				'fileSize': file_data['fileSize'],
				'createdDate': file_data['createdDate'],
				'modifiedDate': file_data['modifiedDate'],
				'importDate': file_data['importDate']
			}
			
			result = self.graph.query(query, params)
			
			if result.result_set:
				self.logger.debug(f"File node created/updated: {file_id}")
				return file_id
			else:
				self.logger.warning(f"File node creation returned no result: {file_id}")
				return None
				
		except Exception as e:
			self.logger.error(f"File node creation failed: {file_path}, error: {e}")
			return None
	
	def create_element_node(self, element_data: Dict[str, Any], file_id: str = None) -> bool:
		"""
		Create IFC element as node
		
		Args:
			element_data: Element data dictionary
			file_id: Associated file ID
			
		Returns:
			Creation success status
		"""
		try:
			global_id = element_data['globalId']
			ifc_class = element_data['ifcClass']
			
			# Prepare properties
			properties = {
				'globalId': global_id,
				'name': element_data.get('name', ''),
				'ifcClass': ifc_class,
				'description': element_data.get('description', ''),
				'objectType': element_data.get('objectType', ''),
				'tag': element_data.get('tag', '')
			}
			
			if file_id:
				properties['sourceFileId'] = file_id
			
			# Store properties as JSON string
			if element_data.get('properties'):
				properties['properties'] = json.dumps(element_data['properties'])
			
			# Build query with multiple labels
			query = f"""
			MERGE (e:Element:{ifc_class} {{globalId: $globalId}})
			SET e.name = $name,
				e.ifcClass = $ifcClass,
				e.description = $description,
				e.objectType = $objectType,
				e.tag = $tag
			"""
			
			params = {
				'globalId': properties['globalId'],
				'name': properties['name'],
				'ifcClass': properties['ifcClass'],
				'description': properties['description'],
				'objectType': properties['objectType'],
				'tag': properties['tag']
			}
			
			if file_id:
				query += ", e.sourceFileId = $sourceFileId"
				params['sourceFileId'] = file_id
			
			if 'properties' in properties:
				query += ", e.properties = $properties"
				params['properties'] = properties['properties']
			
			# Create relationship to file if file_id is provided
			if file_id:
				query += """
				WITH e
				MATCH (f:IFCFile {fileId: $fileId})
				MERGE (e)-[:BELONGS_TO_FILE]->(f)
				"""
				params['fileId'] = file_id
			
			query += " RETURN e.globalId"
			
			result = self.graph.query(query, params)
			
			if result.result_set:
				self.logger.debug(f"Node created/updated: {global_id}")
				return True
			else:
				self.logger.warning(f"Node creation returned no result: {global_id}")
				return False
				
		except Exception as e:
			self.logger.error(f"Node creation failed: {element_data.get('globalId', 'Unknown')}, error: {e}")
			return False
	
	def create_relationship(self, rel_data: Dict[str, Any]) -> bool:
		"""
		Create IFC relationship
		
		Args:
			rel_data: Relationship data dictionary
			
		Returns:
			Creation success status
		"""
		try:
			rel_type = rel_data['type']
			
			# Different processing by relationship type
			if rel_type == 'AGGREGATES':
				return self._create_aggregates_relationship(rel_data)
			elif rel_type == 'CONNECTS_TO':
				return self._create_connects_relationship(rel_data)
			elif rel_type == 'HAS_PROPERTY':
				return self._create_property_relationship(rel_data)
			elif rel_type == 'CONTAINED_IN':
				return self._create_spatial_relationship(rel_data)
			elif rel_type == 'ASSIGNED_TO':
				return self._create_group_relationship(rel_data)
			
			return False
			
		except Exception as e:
			self.logger.error(f"Relationship creation failed: {rel_data.get('type', 'Unknown')}, error: {e}")
			return False
	
	def _create_aggregates_relationship(self, rel_data: Dict[str, Any]) -> bool:
		"""Create aggregation relationship"""
		from_id = rel_data['from_element']
		to_ids = rel_data['to_elements']
		
		if not from_id or not to_ids:
			return False
		
		success_count = 0
		for to_id in to_ids:
			try:
				query = """
				MATCH (from:Element {globalId: $from_id})
				MATCH (to:Element {globalId: $to_id})
				MERGE (from)-[r:AGGREGATES]->(to)
				SET r.globalId = $rel_id
				RETURN r
				"""
				
				params = {
					'from_id': from_id,
					'to_id': to_id,
					'rel_id': rel_data['globalId']
				}
				
				result = self.graph.query(query, params)
				if result.result_set:
					success_count += 1
			except Exception as e:
				self.logger.warning(f"Aggregation relationship creation failed: {from_id} -> {to_id}, error: {e}")
		
		return success_count > 0
	
	def _create_connects_relationship(self, rel_data: Dict[str, Any]) -> bool:
		"""Create connection relationship"""
		from_id = rel_data['from_element']
		to_id = rel_data['to_element']
		
		if not from_id or not to_id:
			return False
		
		try:
			query = """
			MATCH (from:Element {globalId: $from_id})
			MATCH (to:Element {globalId: $to_id})
			MERGE (from)-[r:CONNECTS_TO]->(to)
			SET r.globalId = $rel_id
			RETURN r
			"""
			
			params = {
				'from_id': from_id,
				'to_id': to_id,
				'rel_id': rel_data['globalId']
			}
			
			result = self.graph.query(query, params)
			return result.result_set is not None
		except Exception as e:
			self.logger.error(f"Connection relationship creation failed: {e}")
			return False
	
	def _create_property_relationship(self, rel_data: Dict[str, Any]) -> bool:
		"""Create property definition relationship"""
		from_ids = rel_data['from_elements']
		to_id = rel_data['to_property']
		
		if not from_ids or not to_id:
			return False
		
		success_count = 0
		for from_id in from_ids:
			try:
				query = """
				MATCH (from:Element {globalId: $from_id})
				MATCH (to:Element {globalId: $to_id})
				MERGE (from)-[r:HAS_PROPERTY]->(to)
				SET r.globalId = $rel_id
				RETURN r
				"""
				
				params = {
					'from_id': from_id,
					'to_id': to_id,
					'rel_id': rel_data['globalId']
				}
				
				result = self.graph.query(query, params)
				if result.result_set:
					success_count += 1
			except Exception as e:
				self.logger.warning(f"Property relationship creation failed: {from_id} -> {to_id}, error: {e}")
		
		return success_count > 0
	
	def _create_spatial_relationship(self, rel_data: Dict[str, Any]) -> bool:
		"""Create spatial containment relationship"""
		from_ids = rel_data['from_elements']
		to_id = rel_data['to_structure']
		
		if not from_ids or not to_id:
			return False
		
		success_count = 0
		for from_id in from_ids:
			try:
				query = """
				MATCH (from:Element {globalId: $from_id})
				MATCH (to:Element {globalId: $to_id})
				MERGE (from)-[r:CONTAINED_IN]->(to)
				SET r.globalId = $rel_id
				RETURN r
				"""
				
				params = {
					'from_id': from_id,
					'to_id': to_id,
					'rel_id': rel_data['globalId']
				}
				
				result = self.graph.query(query, params)
				if result.result_set:
					success_count += 1
			except Exception as e:
				self.logger.warning(f"Spatial relationship creation failed: {from_id} -> {to_id}, error: {e}")
		
		return success_count > 0
	
	def _create_group_relationship(self, rel_data: Dict[str, Any]) -> bool:
		"""Create group assignment relationship"""
		from_ids = rel_data['from_elements']
		to_id = rel_data['to_group']
		
		if not from_ids or not to_id:
			return False
		
		success_count = 0
		for from_id in from_ids:
			try:
				query = """
				MATCH (from:Element {globalId: $from_id})
				MATCH (to:Element {globalId: $to_id})
				MERGE (from)-[r:ASSIGNED_TO]->(to)
				SET r.globalId = $rel_id
				RETURN r
				"""
				
				params = {
					'from_id': from_id,
					'to_id': to_id,
					'rel_id': rel_data['globalId']
				}
				
				result = self.graph.query(query, params)
				if result.result_set:
					success_count += 1
			except Exception as e:
				self.logger.warning(f"Group relationship creation failed: {from_id} -> {to_id}, error: {e}")
		
		return success_count > 0
	
	def get_statistics(self) -> Dict[str, Any]:
		"""
		Get database statistics
		
		Returns:
			Statistics dictionary
		"""
		try:
			stats = {}
			
			# Total node count
			result = self.graph.query("MATCH (n) RETURN count(n) as count")
			stats['total_nodes'] = result.result_set[0][0] if result.result_set else 0
			
			# Total relationship count
			result = self.graph.query("MATCH ()-[r]->() RETURN count(r) as count")
			stats['total_relationships'] = result.result_set[0][0] if result.result_set else 0
			
			# Element type distribution
			result = self.graph.query("""
				MATCH (n:Element)
				RETURN n.ifcClass as type, count(n) as count
				ORDER BY count DESC
			""")
			
			element_types = {}
			if result.result_set:
				for row in result.result_set:
					element_types[row[0]] = row[1]
			stats['element_types'] = element_types
			
			# Relationship type distribution
			result = self.graph.query("""
				MATCH ()-[r]->()
				RETURN type(r) as type, count(r) as count
			""")
			
			relationship_types = {}
			if result.result_set:
				for row in result.result_set:
					relationship_types[row[0]] = row[1]
			stats['relationship_types'] = relationship_types
			
			return stats
		except Exception as e:
			self.logger.error(f"Statistics collection failed: {e}")
			return {}
