"""
Neo4j database connection and data processing module
"""
from neo4j import GraphDatabase
import logging
from typing import Dict, List, Any, Optional
import json
from pathlib import Path
import os
from datetime import datetime


class Neo4jDatabase:
    """Neo4j database connection and data management class"""
    
    def __init__(self, uri: str, user: str, password: str, database: str = "elements"):
        """
        Initialize Neo4j database connection
        
        Args:
            uri: Neo4j server URI
            user: Username
            password: Password
            database: Database name
        """
        self.logger = logging.getLogger(__name__)
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver = None
        
    def connect(self) -> bool:
        """
        Connect to Neo4j database
        
        Returns:
            Connection success status
        """
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Connection test
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            self.logger.info(f"Neo4j database connection successful: {self.uri}")
            return True
        except Exception as e:
            self.logger.error(f"Neo4j database connection failed: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j database connection closed")
    
    def create_file_node(self, file_path: Path) -> Optional[str]:
        """
        Create IFC file metadata node in Neo4j
        
        Args:
            file_path: Path to the IFC file
            
        Returns:
            File ID if successful, None otherwise
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.execute_write(self._create_file_tx, file_path)
                return result
        except Exception as e:
            self.logger.error(f"File node creation failed: {file_path}, error: {e}")
            return None
    
    def _create_file_tx(self, tx, file_path: Path) -> Optional[str]:
        """File node creation transaction"""
        try:
            # Get file information
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
            SET f += $fileData
            RETURN f.fileId as fileId
            """
            
            result = tx.run(query, fileId=file_id, fileData=file_data)
            record = result.single()
            
            if record:
                self.logger.debug(f"File node created/updated: {file_id}")
                return file_id
            else:
                self.logger.warning(f"File node creation returned no result: {file_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"File node creation transaction failed: {e}")
            return None
    
    def create_element_node(self, element_data: Dict[str, Any], file_id: str = None) -> bool:
        """
        Create IFC element as Neo4j node (using MERGE)
        
        Args:
            element_data: Element data dictionary
            file_id: Associated file ID
            
        Returns:
            Creation success status
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.execute_write(self._create_element_tx, element_data, file_id)
                return result
        except Exception as e:
            self.logger.error(f"Node creation failed: {element_data.get('globalId', 'Unknown')}, error: {e}")
            return False
    
    def _create_element_tx(self, tx, element_data: Dict[str, Any], file_id: str = None) -> bool:
        """Element node creation transaction"""
        try:
            global_id = element_data['globalId']
            ifc_class = element_data['ifcClass']
            
            # Basic properties
            properties = {
                'globalId': global_id,
                'name': element_data.get('name', ''),
                'ifcClass': ifc_class,
                'description': element_data.get('description', ''),
                'objectType': element_data.get('objectType', ''),
                'tag': element_data.get('tag', '')
            }
            
            # Add file reference if provided
            if file_id:
                properties['sourceFileId'] = file_id
            
            # Store PropertySet as JSON string
            if element_data.get('properties'):
                properties['properties'] = json.dumps(element_data['properties'])
            
            # Dynamic label creation (Element and IFC class name)
            labels = f":Element:{ifc_class}"
            
            query = f"""
            MERGE (e{labels} {{globalId: $globalId}})
            SET e += $properties
            """
            
            # Create relationship to file if file_id is provided
            if file_id:
                query += """
                WITH e
                MATCH (f:IFCFile {fileId: $fileId})
                MERGE (e)-[:BELONGS_TO_FILE]->(f)
                """
            
            query += "RETURN e.globalId as globalId"
            
            result = tx.run(query, globalId=global_id, properties=properties, fileId=file_id)
            record = result.single()
            
            if record:
                self.logger.debug(f"Node created/updated: {global_id}")
                return True
            else:
                self.logger.warning(f"Node creation returned no result: {global_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Node creation transaction failed: {e}")
            return False
    
    def create_relationship(self, rel_data: Dict[str, Any]) -> bool:
        """
        Create IFC relationship as Neo4j relationship
        
        Args:
            rel_data: Relationship data dictionary
            
        Returns:
            Creation success status
        """
        try:
            with self.driver.session(database=self.database) as session:
                result = session.execute_write(self._create_relationship_tx, rel_data)
                return result
        except Exception as e:
            self.logger.error(f"Relationship creation failed: {rel_data.get('type', 'Unknown')}, error: {e}")
            return False
    
    def _create_relationship_tx(self, tx, rel_data: Dict[str, Any]) -> bool:
        """Relationship creation transaction"""
        try:
            rel_type = rel_data['type']
            
            # Different processing by relationship type
            if rel_type == 'AGGREGATES':
                return self._create_aggregates_relationship(tx, rel_data)
            elif rel_type == 'CONNECTS_TO':
                return self._create_connects_relationship(tx, rel_data)
            elif rel_type == 'HAS_PROPERTY':
                return self._create_property_relationship(tx, rel_data)
            elif rel_type == 'CONTAINED_IN':
                return self._create_spatial_relationship(tx, rel_data)
            elif rel_type == 'ASSIGNED_TO':
                return self._create_group_relationship(tx, rel_data)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Relationship creation transaction failed: {e}")
            return False
    
    def _create_aggregates_relationship(self, tx, rel_data: Dict[str, Any]) -> bool:
        """Create aggregation relationship"""
        from_id = rel_data['from_element']
        to_ids = rel_data['to_elements']
        
        if not from_id or not to_ids:
            return False
        
        success_count = 0
        for to_id in to_ids:
            query = """
            MATCH (from:Element {globalId: $from_id})
            MATCH (to:Element {globalId: $to_id})
            MERGE (from)-[r:AGGREGATES]->(to)
            SET r.globalId = $rel_id
            RETURN r
            """
            
            result = tx.run(query, 
                          from_id=from_id, 
                          to_id=to_id, 
                          rel_id=rel_data['globalId'])
            
            if result.single():
                success_count += 1
        
        return success_count > 0
    
    def _create_connects_relationship(self, tx, rel_data: Dict[str, Any]) -> bool:
        """Create connection relationship"""
        from_id = rel_data['from_element']
        to_id = rel_data['to_element']
        
        if not from_id or not to_id:
            return False
        
        query = """
        MATCH (from:Element {globalId: $from_id})
        MATCH (to:Element {globalId: $to_id})
        MERGE (from)-[r:CONNECTS_TO]->(to)
        SET r.globalId = $rel_id
        RETURN r
        """
        
        result = tx.run(query, 
                      from_id=from_id, 
                      to_id=to_id, 
                      rel_id=rel_data['globalId'])
        
        return result.single() is not None
    
    def _create_property_relationship(self, tx, rel_data: Dict[str, Any]) -> bool:
        """Create property relationship (PropertySet is handled as node attributes)"""
        # PropertySet is already stored as element node attributes, no separate relationship needed
        return True
    
    def _create_spatial_relationship(self, tx, rel_data: Dict[str, Any]) -> bool:
        """Create spatial containment relationship"""
        from_ids = rel_data['from_elements']
        to_id = rel_data['to_structure']
        
        if not from_ids or not to_id:
            return False
        
        success_count = 0
        for from_id in from_ids:
            query = """
            MATCH (from:Element {globalId: $from_id})
            MATCH (to:Element {globalId: $to_id})
            MERGE (from)-[r:CONTAINED_IN]->(to)
            SET r.globalId = $rel_id
            RETURN r
            """
            
            result = tx.run(query, 
                          from_id=from_id, 
                          to_id=to_id, 
                          rel_id=rel_data['globalId'])
            
            if result.single():
                success_count += 1
        
        return success_count > 0
    
    def _create_group_relationship(self, tx, rel_data: Dict[str, Any]) -> bool:
        """Create group assignment relationship"""
        from_ids = rel_data['from_elements']
        to_id = rel_data['to_group']
        
        if not from_ids or not to_id:
            return False
        
        success_count = 0
        for from_id in from_ids:
            query = """
            MATCH (from:Element {globalId: $from_id})
            MATCH (to:Element {globalId: $to_id})
            MERGE (from)-[r:ASSIGNED_TO]->(to)
            SET r.globalId = $rel_id
            RETURN r
            """
            
            result = tx.run(query, 
                          from_id=from_id, 
                          to_id=to_id, 
                          rel_id=rel_data['globalId'])
            
            if result.single():
                success_count += 1
        
        return success_count > 0
    
    def clear_database(self) -> bool:
        """
        Delete all nodes and relationships from database (for development/testing)
        
        Returns:
            Deletion success status
        """
        try:
            with self.driver.session(database=self.database) as session:
                session.run("MATCH (n) DETACH DELETE n")
            self.logger.info("Database initialization completed")
            return True
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """
        Query database statistics
        
        Returns:
            Node and relationship count information
        """
        try:
            with self.driver.session(database=self.database) as session:
                # Node count
                node_result = session.run("MATCH (n) RETURN count(n) as count")
                node_count = node_result.single()['count']
                
                # Relationship count
                rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_count = rel_result.single()['count']
                
                # Node count by label (using basic Cypher only)
                label_counts = {}
                try:
                    # Count Element nodes (main label)
                    element_result = session.run("MATCH (n:Element) RETURN count(n) as count")
                    element_count = element_result.single()['count']
                    if element_count > 0:
                        label_counts['Element'] = element_count
                        
                    # Count IFCFile nodes
                    file_result = session.run("MATCH (n:IFCFile) RETURN count(n) as count")
                    file_count = file_result.single()['count']
                    if file_count > 0:
                        label_counts['IFCFile'] = file_count
                except:
                    pass
                
                return {
                    'total_nodes': node_count,
                    'total_relationships': rel_count,
                    'label_counts': label_counts
                }
                
        except Exception as e:
            self.logger.error(f"Statistics query failed: {e}")
            return {
                'total_nodes': 0,
                'total_relationships': 0,
                'label_counts': {}
            }