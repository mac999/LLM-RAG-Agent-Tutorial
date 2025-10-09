"""
Module for IFC file parsing
"""
import ifcopenshell
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path


class IFCParser:
    """Class for parsing IFC files and extracting elements and relationships"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def parse_file(self, file_path: Path) -> Optional[ifcopenshell.file]:
        """
        Parse IFC file and return ifcopenshell file object
        
        Args:
            file_path: IFC file path
            
        Returns:
            ifcopenshell.file object or None (on failure)
        """
        try:
            self.logger.info(f"Starting IFC file parsing: {file_path}")
            ifc_file = ifcopenshell.open(str(file_path))
            self.logger.info(f"IFC file parsing completed: {file_path}")
            return ifc_file
        except Exception as e:
            self.logger.error(f"IFC file parsing failed: {file_path}, error: {e}")
            return None
    
    def extract_elements(self, ifc_file: ifcopenshell.file) -> List[Dict[str, Any]]:
        """
        Extract all elements from IFC file
        
        Args:
            ifc_file: ifcopenshell file object
            
        Returns:
            List of dictionaries containing element information
        """
        elements = []
        
        # Get all IFC element types
        for element in ifc_file.by_type('IfcProduct'):
            try:
                element_data = self._extract_element_data(element)
                if element_data:
                    elements.append(element_data)
            except Exception as e:
                self.logger.warning(f"Element extraction failed: {element}, error: {e}")
                continue
                
        self.logger.info(f"Extracted {len(elements)} elements in total.")
        return elements
    
    def _extract_element_data(self, element) -> Dict[str, Any]:
        """
        Extract data from individual element
        
        Args:
            element: IFC element object
            
        Returns:
            Element data dictionary
        """
        data = {
            'globalId': element.GlobalId,
            'ifcClass': element.is_a(),
            'name': getattr(element, 'Name', None) or '',
            'description': getattr(element, 'Description', None) or '',
            'objectType': getattr(element, 'ObjectType', None) or '',
            'tag': getattr(element, 'Tag', None) or '',
            'properties': self._extract_properties(element)
        }
        
        return data
    
    def _extract_properties(self, element) -> Dict[str, Any]:
        """
        Extract PropertySet information from element
        
        Args:
            element: IFC element object
            
        Returns:
            Property information dictionary
        """
        properties = {}
        
        try:
            # Find property sets through IfcRelDefinesByProperties relationship
            for rel in getattr(element, 'IsDefinedBy', []):
                if rel.is_a('IfcRelDefinesByProperties'):
                    prop_def = rel.RelatingPropertyDefinition
                    if prop_def.is_a('IfcPropertySet'):
                        pset_name = prop_def.Name
                        properties[pset_name] = {}
                        
                        for prop in prop_def.HasProperties:
                            if hasattr(prop, 'Name') and hasattr(prop, 'NominalValue'):
                                prop_name = prop.Name
                                prop_value = getattr(prop.NominalValue, 'wrappedValue', str(prop.NominalValue))
                                properties[pset_name][prop_name] = prop_value
                                
        except Exception as e:
            self.logger.warning(f"Property extraction failed: {element}, error: {e}")
            
        return properties
    
    def extract_relationships(self, ifc_file: ifcopenshell.file) -> List[Dict[str, Any]]:
        """
        Extract all relationships from IFC file
        
        Args:
            ifc_file: ifcopenshell file object
            
        Returns:
            List of dictionaries containing relationship information
        """
        relationships = []
        
        # Extract all relationship types
        rel_types = [
            'IfcRelAggregates',       # Aggregation relationship
            'IfcRelConnectsElements', # Connection relationship
            'IfcRelDefinesByProperties', # Property definition relationship
            'IfcRelContainedInSpatialStructure', # Spatial containment relationship
            'IfcRelAssignsToGroup',   # Group assignment relationship
        ]
        
        for rel_type in rel_types:
            for rel in ifc_file.by_type(rel_type):
                try:
                    rel_data = self._extract_relationship_data(rel)
                    if rel_data:
                        relationships.append(rel_data)
                except Exception as e:
                    self.logger.warning(f"Relationship extraction failed: {rel}, error: {e}")
                    continue
                    
        self.logger.info(f"Extracted {len(relationships)} relationships in total.")
        return relationships
    
    def _extract_relationship_data(self, rel) -> Optional[Dict[str, Any]]:
        """
        Extract data from individual relationship
        
        Args:
            rel: IFC relationship object
            
        Returns:
            Relationship data dictionary or None
        """
        rel_type = rel.is_a()
        
        # Different processing by relationship type
        if rel_type == 'IfcRelAggregates':
            return self._extract_aggregates_relationship(rel)
        elif rel_type == 'IfcRelConnectsElements':
            return self._extract_connects_relationship(rel)
        elif rel_type == 'IfcRelDefinesByProperties':
            return self._extract_properties_relationship(rel)
        elif rel_type == 'IfcRelContainedInSpatialStructure':
            return self._extract_spatial_relationship(rel)
        elif rel_type == 'IfcRelAssignsToGroup':
            return self._extract_group_relationship(rel)
        
        return None
    
    def _extract_aggregates_relationship(self, rel) -> Dict[str, Any]:
        """Extract aggregation relationship"""
        data = {
            'type': 'AGGREGATES',
            'globalId': rel.GlobalId,
            'from_element': rel.RelatingObject.GlobalId if rel.RelatingObject else None,
            'to_elements': [obj.GlobalId for obj in rel.RelatedObjects if hasattr(obj, 'GlobalId')]
        }
        return data
    
    def _extract_connects_relationship(self, rel) -> Dict[str, Any]:
        """Extract connection relationship"""
        data = {
            'type': 'CONNECTS_TO',
            'globalId': rel.GlobalId,
            'from_element': rel.RelatingElement.GlobalId if rel.RelatingElement else None,
            'to_element': rel.RelatedElement.GlobalId if rel.RelatedElement else None
        }
        return data
    
    def _extract_properties_relationship(self, rel) -> Dict[str, Any]:
        """Extract property definition relationship"""
        data = {
            'type': 'HAS_PROPERTY',
            'globalId': rel.GlobalId,
            'from_elements': [obj.GlobalId for obj in rel.RelatedObjects if hasattr(obj, 'GlobalId')],
            'to_property': rel.RelatingPropertyDefinition.GlobalId if hasattr(rel.RelatingPropertyDefinition, 'GlobalId') else None
        }
        return data
    
    def _extract_spatial_relationship(self, rel) -> Dict[str, Any]:
        """Extract spatial containment relationship"""
        data = {
            'type': 'CONTAINED_IN',
            'globalId': rel.GlobalId,
            'from_elements': [obj.GlobalId for obj in rel.RelatedElements if hasattr(obj, 'GlobalId')],
            'to_structure': rel.RelatingStructure.GlobalId if rel.RelatingStructure else None
        }
        return data
    
    def _extract_group_relationship(self, rel) -> Dict[str, Any]:
        """Extract group assignment relationship"""
        data = {
            'type': 'ASSIGNED_TO',
            'globalId': rel.GlobalId,
            'from_elements': [obj.GlobalId for obj in rel.RelatedObjects if hasattr(obj, 'GlobalId')],
            'to_group': rel.RelatingGroup.GlobalId if rel.RelatingGroup else None
        }
        return data