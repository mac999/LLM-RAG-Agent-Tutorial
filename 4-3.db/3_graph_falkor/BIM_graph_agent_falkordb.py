"""
BIM Graph Agent - AI-powered BIM data query system using LangChain and FalkorDB

This system provides an intelligent interface to query BIM graph data stored in FalkorDB
using natural language queries, which are converted to Cypher queries and processed
to return structured JSON responses.

Architecture:
1. User Input (Natural Language) -> 
2. LLM (qwen2.5-coder:7b) converts to Cypher -> 
3. FalkorDB Query Execution -> JSON Result -> 
4. LLM generates user-friendly response

Usage:
	python BIM_graph_agent_falkordb.py

Contact: Taewook Kang (laputa99999@gmail.com)
"""

import json
import sys
import os
import time
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
from falkordb import FalkorDB

# Add project source to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


class FalkorDBQueryTool:
	"""Tool for executing Cypher queries against FalkorDB BIM graph database"""
	
	def __init__(self, host: str, port: int, username: str = None, password: str = None, graph_name: str = "bim"):
		"""
		Initialize FalkorDB connection
		
		Args:
			host: FalkorDB server host
			port: FalkorDB server port
			username: Username (optional)
			password: Password (optional)
			graph_name: Graph name
		"""
		self.host = host
		self.port = port
		self.username = username
		self.password = password
		self.graph_name = graph_name
		self.client = None
		self.graph = None
		
	def connect(self, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
		"""
		Connect to FalkorDB database with retry logic
		
		Args:
			max_retries: Maximum number of connection attempts
			retry_delay: Delay between retry attempts in seconds
		"""
		for attempt in range(max_retries):
			try:
				print(f"Attempting to connect to FalkorDB (attempt {attempt + 1}/{max_retries})...")
				
				# Close existing connection if any
				if self.client:
					self.client = None
					self.graph = None
				
				# Create new client
				self.client = FalkorDB(
					host=self.host,
					port=self.port,
					username=self.username,
					password=self.password
				)
				
				# Select graph
				self.graph = self.client.select_graph(self.graph_name)
				
				# Test connection
				result = self.graph.query("RETURN 1 as test")
				if result.result_set and result.result_set[0][0] == 1:
					print("FalkorDB connection successful!")
					return True
				
			except Exception as e:
				print(f"FalkorDB connection attempt {attempt + 1} failed: {e}")
				
				if attempt < max_retries - 1:
					print(f"Retrying in {retry_delay} seconds...")
					time.sleep(retry_delay)
				else:
					print("All connection attempts failed.")
					print("Please check:")
					print("1. FalkorDB server is running")
					print("2. Connection settings in .env file")
					print("3. Database credentials are correct")
					print("4. Network connectivity to FalkorDB server")
		
		return False
	
	def close(self):
		"""Close database connection"""
		if self.client:
			try:
				self.client = None
				self.graph = None
				print("FalkorDB connection closed")
			except Exception as e:
				print(f"Error closing FalkorDB connection: {e}")
	
	def test_connection(self) -> bool:
		"""Test if the database connection is still alive"""
		if not self.client or not self.graph:
			return False
		
		try:
			self.graph.query("RETURN 1")
			return True
		except Exception:
			return False
	
	def execute_query(self, cypher_query: str, max_retries: int = 2) -> Dict[str, Any]:
		"""
		Execute Cypher query with retry logic and return JSON result
		
		Args:
			cypher_query: Cypher query string
			max_retries: Maximum number of query execution attempts
			
		Returns:
			Dictionary containing query results or error information
		"""
		if not self.client or not self.graph:
			return {"success": False, "error": "Not connected to database", "results": []}
		
		for attempt in range(max_retries):
			try:
				result = self.graph.query(cypher_query)
				
				# Convert result to list of dictionaries
				records = []
				if result.result_set:
					# Get column headers
					headers = result.header if hasattr(result, 'header') else []
					
					for row in result.result_set:
						record_dict = {}
						for idx, value in enumerate(row):
							# Get column name
							col_name = headers[idx].name if idx < len(headers) and hasattr(headers[idx], 'name') else f"col_{idx}"
							
							# Handle FalkorDB node/relationship objects
							if hasattr(value, 'properties'):
								record_dict[col_name] = dict(value.properties)
							elif hasattr(value, 'relation'):  # Relationship
								record_dict[col_name] = {
									"type": value.relation if hasattr(value, 'relation') else "Unknown",
									"properties": dict(value.properties) if hasattr(value, 'properties') else {}
								}
							else:
								record_dict[col_name] = value
						
						records.append(record_dict)
				
				return {
					"success": True,
					"query": cypher_query,
					"results": records,
					"count": len(records)
				}
				
			except Exception as e:
				error_msg = str(e)
				
				# Check for connection-related errors
				if any(keyword in error_msg.lower() for keyword in ['connection', 'reset', 'refused', 'timeout']):
					print(f"Connection error on attempt {attempt + 1}: {error_msg}")
					
					if attempt < max_retries - 1:
						print("Attempting to reconnect...")
						if self.connect():
							continue
				
				return {
					"success": False,
					"query": cypher_query,
					"error": error_msg,
					"results": []
				}
		
		return {
			"success": False,
			"query": cypher_query,
			"error": "Query execution failed after all retry attempts",
			"results": []
		}


class BIMGraphAgent:
	"""BIM Graph Agent system using LangChain and Ollama models with FalkorDB"""
	
	def __init__(self):
		"""Initialize the BIM Graph Agent system"""
		self.falkordb_tool = None
		self.cypher_generator = None
		self.response_generator = None
		self.cypher_chain = None
		self.response_chain = None

		self.setup_models()
		self.setup_chains()
		
	def setup_models(self):
		"""Setup and preload Ollama models for Cypher generation and response generation"""
		try:
			print("Initializing single LLM model for optimal performance...")
			
			# Model: Cypher Query Generator & Response Generator (qwen2.5-coder:7b)
			print("Loading qwen2.5-coder:7b model...")
			self.cypher_generator = ChatOllama(
				model="qwen2.5-coder:7b",
				temperature=0.1,
				base_url="http://localhost:11434"
			)
			
			# Using same model for response generation
			print("Using qwen2.5-coder:7b for response generation too (single model approach)...")
			self.response_generator = ChatOllama(
				model="qwen2.5-coder:7b",
				temperature=0.2,
				base_url="http://localhost:11434"
			)
			
			print("Preloading models with test queries...")
			
			# Preload model with a simple test query
			try:
				test_result = self.cypher_generator.invoke("Test connection")
				print("✓ Cypher generator model loaded and ready")
			except Exception as e:
				print(f"Warning: Model preload failed: {e}")
			
			print("✓ Single model approach - qwen2.5-coder:7b handles both Cypher generation and responses")
			print("✓ Eliminates model switching overhead for faster performance")
			print("Single model initialized and preloaded successfully - ready for fast responses!")
			
		except Exception as e:
			print(f"Error initializing Ollama models: {e}")
			print("Make sure Ollama is running and models are available")
			print("You can check available models with: ollama list")
			sys.exit(1)
	
	def setup_chains(self):
		"""Setup and cache LangChain chains for faster query processing"""
		try:
			print("Setting up LangChain chains...")
			
			# Pre-create and cache the Cypher chain
			self.cypher_chain = self.create_cypher_chain()
			print("✓ Cypher chain created and cached")
			
			# Pre-create and cache the response chain
			self.response_chain = self.create_response_chain()
			print("✓ Response chain created and cached")
			
			print("All LangChain chains ready for fast processing")
			
		except Exception as e:
			print(f"Error setting up chains: {e}")
			sys.exit(1)
	
	def setup_falkordb(self, host: str, port: int, username: str = None, password: str = None, graph_name: str = "bim"):
		"""Setup FalkorDB connection with enhanced error handling"""
		print(f"Setting up FalkorDB connection to {host}:{port}, graph: {graph_name}")
		
		self.falkordb_tool = FalkorDBQueryTool(host, port, username, password, graph_name)
		
		if not self.falkordb_tool.connect():
			print("\nFalkorDB Connection Failed!")
			print("Troubleshooting steps:")
			print("1. Ensure FalkorDB is running:")
			print("   - Check if FalkorDB/Redis is accessible")
			print("   - Try: redis-cli ping")
			print("2. Verify connection settings in .env file")
			print("3. Check if the graph exists in FalkorDB")
			print("4. Try accessing FalkorDB with redis-cli")
			return False
		
		# Test if we can access the graph
		test_result = self.falkordb_tool.execute_query("MATCH (n) RETURN count(n) as nodeCount LIMIT 1")
		if not test_result.get("success", False):
			print(f"\nWarning: Could not access graph: {test_result.get('error', 'Unknown error')}")
			print("Make sure the graph exists and contains BIM data")
			print("Run 'python import_ifc_to_falkordb.py' first to import IFC data")
		else:
			node_count = test_result.get("results", [{}])[0].get("nodeCount", 0)
			print(f"Connected successfully! Found {node_count} nodes in graph")
		
		return True
	
	def create_cypher_chain(self):
		"""Create LangChain chain for converting natural language to Cypher"""
		
		schema_info = """
		BIM Graph Database Schema (FalkorDB):
		
		Node Labels (Each IFC class has its own label):
		- Element: Generic element properties
		- IFCFile: IFC file metadata  
		- IfcBeam, IfcBuilding, IfcBuildingStorey, IfcCovering, IfcDoor, IfcFooting
		- IfcFurnishingElement, IfcMember, IfcOpeningElement, IfcRailing
		- IfcRoof, IfcSite, IfcSlab, IfcSpace, IfcStair, IfcStairFlight
		- IfcWall, IfcWallStandardCase, IfcWindow
		
		Common Node Properties:
		- description, globalId, name, objectType, properties, sourceFileId, tag
		- All properties are stored directly in each node
		
		IFCFile Properties:
		- createdDate, fileId, fileName, filePath, fileSize, importDate, modifiedDate
		
		Relationship Types:
		- AGGREGATES: Element -> Element (aggregation relationships)
		- BELONGS_TO_FILE: Element -> IFCFile (links elements to their source file)  
		- CONTAINED_IN: Element -> Element (spatial containment)
		
		CRITICAL Schema Rules:
		1. Use specific IFC labels (IfcSpace, IfcWall, etc.) NOT generic Element label
		2. Properties are stored as nested JSON in the 'properties' field
		3. Do NOT try to access specific nested property paths - they vary by modeling tool
		4. For property-related queries: Always return full properties JSON for LLM analysis
		5. Standard approach: MATCH (s:IfcSpace {{name: 'A204'}}) RETURN s.name, s.properties
		
		Query Examples:
		- Find space properties: MATCH (s:IfcSpace {{name: 'A204'}}) RETURN s.properties
		- Count walls: MATCH (w:IfcWall) RETURN count(w)
		- Find all doors: MATCH (d:IfcDoor) RETURN d.name, d.properties LIMIT 10
		- Find file info: MATCH (f:IFCFile) RETURN f.fileName, f.fileSize
		- Get space with properties: MATCH (s:IfcSpace {{name: 'A204'}}) RETURN s.name, s.properties
		"""
		
		cypher_prompt = ChatPromptTemplate.from_messages([
			("system", """You are an agent in converting natural language queries to Cypher queries for BIM/IFC data in FalkorDB.
			
			""" + schema_info + """
			
			IMPORTANT: Properties are stored as nested JSON. For property-related queries (area, volume, etc.):
			- Return the full properties JSON: RETURN s.name, s.properties
			- Let the response processor extract specific values from the JSON
			- Don't try to access specific nested paths as they vary by modeling tool
			
			Rules for Cypher generation:
			1. Always use proper Cypher syntax compatible with FalkorDB
			2. Use specific IFC labels (IfcSpace, IfcWall, IfcDoor, etc.) as node labels
			3. Access element properties directly from the node (e.g., s.properties, s.name, s.globalId)
			4. Do NOT traverse relationships for basic element properties  
			5. Use WHERE clauses for additional filtering by name, etc.
			6. Use LIMIT to prevent large result sets (default LIMIT 100)
			7. For counts, use count() function
			8. For file information, match on IFCFile nodes
			9. For property searches, return the entire properties JSON
			10. Use simple property access: s.properties (return full JSON for analysis)
			
			CORRECT Examples:
			- MATCH (s:IfcSpace {{name: 'A204'}}) RETURN s.name, s.globalId, s.properties
			- MATCH (w:IfcWall) RETURN count(w)
			- MATCH (d:IfcDoor) RETURN d.name, d.globalId, d.properties LIMIT 10
			- MATCH (f:IFCFile) RETURN f.fileName, f.fileSize
			
			WRONG Examples:
			- MATCH (e:Element {{ifcClass: 'IfcSpace'}}) (Use direct IfcSpace label)
			- Trying to access specific property paths like s.properties.PSet_Name.Property
			
			Generate ONLY the Cypher query without explanation or markdown formatting.
			"""),
			("user", "Convert this query to Cypher: {query}")
		])
		
		return cypher_prompt | self.cypher_generator | StrOutputParser()
	
	def create_response_chain(self):
		"""Create LangChain chain for generating user-friendly responses"""
		
		response_prompt = ChatPromptTemplate.from_messages([
			("system", """You are a helpful BIM agent assistant specialized in analyzing IFC element properties and answering user questions. You receive JSON results from FalkorDB database queries about BIM/IFC data.
			
			CRITICAL: When analyzing element properties JSON:
			1. Look for relevant information in the nested properties structure
			2. Common property patterns to search for:
			   - Area: look for keys containing 'Area', 'area', 'GrossFloorArea', '면적' etc.
			   - Volume: look for 'Volume', 'volume', 'GrossVolume', '체적' etc.
			   - Name: look for 'Name', 'name', '이름', 'Number' etc.
			   - Level/Floor: look for 'Level', 'level', '층', 'Floor' etc.
			   - Material: look for 'Material', 'material', '재료' etc.
			3. Different modeling tools (Revit, ArchiCAD, Tekla, etc.) use different property set names
			4. Property sets may have names like: 'PSet_Revit_Dimensions', 'BaseQuantities', 'Pset_SpaceCommon' etc.
			5. Always search through ALL property sets to find relevant information
			
			Your responses should:
			1. Extract and highlight the specific information requested by the user
			2. Provide clear numerical values with appropriate units when available
			3. Explain where the information was found in the properties structure
			4. Be concise but informative for construction professionals
			5. Handle Korean and English property names equally
			
			If no relevant property is found, suggest what to look for or mention that the property might not be available in this model.
			"""),
			("user", """
			Original Query: {original_query}
			Cypher Query: {cypher_query}
			Query Results: {query_results}
			
			Please provide a helpful response based on these results.
			""")
		])
		
		return response_prompt | self.response_generator | StrOutputParser()
	
	def clean_cypher_query(self, cypher_query: str) -> str:
		"""
		Clean Cypher query by removing unnecessary keywords, markdown formatting, and newlines
		
		Args:
			cypher_query: Raw Cypher query string
			
		Returns:
			Cleaned Cypher query string
		"""
		try:
			cleaned = cypher_query
			
			# Remove markdown code blocks
			cleaned = re.sub(r'```cypher\s*\n?', '', cleaned, flags=re.IGNORECASE)
			cleaned = re.sub(r'```sql\s*\n?', '', cleaned, flags=re.IGNORECASE)
			cleaned = re.sub(r'```\s*\n?', '', cleaned)
			
			# Remove common prefixes
			cleaned = re.sub(r'^(cypher|sql):\s*', '', cleaned, flags=re.IGNORECASE)
			cleaned = re.sub(r'^(cypher|sql)\s+', '', cleaned, flags=re.IGNORECASE)
			cleaned = re.sub(r'^query:\s*', '', cleaned, flags=re.IGNORECASE)
			
			# Remove explanation text
			cypher_keywords = ['MATCH', 'WHERE', 'RETURN', 'WITH', 'CREATE', 'DELETE', 'SET', 'REMOVE', 'MERGE', 'UNWIND', 'ORDER BY', 'LIMIT', 'SKIP']
			lines = cleaned.split('\n')
			cypher_lines = []
			
			for line in lines:
				line = line.strip()
				if not line:
					continue
				
				is_cypher_line = any(keyword in line.upper() for keyword in cypher_keywords)
				is_continuation = line.startswith(('(', ')', '[', ']', '{', '}', ',', '.', '-', ':', '<', '>', '='))
				
				if is_cypher_line or is_continuation or not cypher_lines:
					cypher_lines.append(line)
				else:
					break
			
			cleaned = ' '.join(cypher_lines)
			
			# Normalize whitespace
			cleaned = re.sub(r'\s+', ' ', cleaned)
			cleaned = cleaned.strip()
			
			# Remove trailing punctuation
			cleaned = re.sub(r'[.!?]+\s*$', '', cleaned)
			cleaned = re.sub(r';\s*$', '', cleaned)
			
			# Remove quotes around the entire query
			if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
				cleaned = cleaned[1:-1]
			
			return cleaned
			
		except Exception as e:
			print(f"Warning: Error cleaning Cypher query: {e}")
			fallback = cypher_query.strip()
			fallback = re.sub(r'```cypher\s*\n?', '', fallback, flags=re.IGNORECASE)
			fallback = re.sub(r'```\s*\n?', '', fallback)
			fallback = re.sub(r'\s+', ' ', fallback)
			return fallback.strip()
	
	def process_query(self, user_query: str) -> str:
		"""
		Process user query through the complete chain
		
		Args:
			user_query: Natural language query from user
			
		Returns:
			Generated response string
		"""
		try:
			print(f"Processing query: {user_query}")
			
			# Step 1: Convert to Cypher using pre-cached chain
			raw_cypher_query = self.cypher_chain.invoke({"query": user_query})
			print(f"Raw generated Cypher: {raw_cypher_query}")
			
			# Step 1.5: Clean Cypher query
			cypher_query = self.clean_cypher_query(raw_cypher_query)
			print(f"Cleaned Cypher: {cypher_query}")
			
			# Step 2: Execute Cypher query
			query_results = self.falkordb_tool.execute_query(cypher_query)
			print(f"Query executed, found {query_results.get('count', 0)} results")
			
			# Step 3: Generate response using pre-cached chain
			response = self.response_chain.invoke({
				"original_query": user_query,
				"cypher_query": cypher_query,
				"query_results": json.dumps(query_results, indent=2)
			})
			
			return response
			
		except Exception as e:
			return f"Error processing query: {str(e)}"
	
	def run_console_interface(self):
		"""Run interactive console interface"""
		print("BIM Graph Agent - AI-Powered BIM Data Query System (FalkorDB)")
		print("Ask questions about your BIM data in natural language!")
		print("Examples:")
		print("- How many walls are in the building?")
		print("- Show me all doors in the project")
		print("- What IFC files are loaded?")
		print("- Find elements on the ground floor")
		print("\nType 'quit' or 'exit' to stop")
		
		while True:
			try:
				# Get user input
				user_query = input("\nYour question: ").strip()
				
				# Check for exit commands
				if user_query.lower() in ['quit', 'exit', 'q']:
					print("Thank you for using BIM Graph Agent!")
					break
				
				if not user_query:
					print("Please enter a question.")
					continue
				
				# Process query
				print("\nProcessing...")
				response = self.process_query(user_query)
				
				# Display response
				print(f"\nResponse:")
				print("-" * 40)
				print(response)
				print("-" * 40)
				
			except KeyboardInterrupt:
				print("\n\nGoodbye!")
				break
			except Exception as e:
				print(f"Error: {e}")


def load_environment():
	"""Load environment variables from .env file"""
	env_path = Path(__file__).parent / '.env'
	if env_path.exists():
		load_dotenv(env_path)
	
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


def main():
	try:
		print("Starting BIM Graph Agent (FalkorDB)...")
		
		# Load environment
		try:
			env_config = load_environment()
			print("Environment configuration loaded")
		except Exception as e:
			print(f"Environment configuration error: {e}")
			print("Please check your .env file")
			return 1
		
		# Initialize BIM Graph Agent
		try:
			print("Initializing BIM Graph Agent system...")
			agent = BIMGraphAgent()
			print("BIM Graph Agent system ready!")
		except Exception as e:
			print(f"Failed to initialize BIM Graph Agent: {e}")
			print("Please check if Ollama is running and models are available")
			return 1
		
		# Setup FalkorDB connection
		try:
			if not agent.setup_falkordb(
				host=env_config['host'],
				port=env_config['port'],
				username=env_config['username'],
				password=env_config['password'],
				graph_name=env_config['graph_name']
			):
				print("\nCannot proceed without FalkorDB connection.")
				return 1
		except Exception as e:
			print(f"FalkorDB setup error: {e}")
			return 1
		
		# Run console interface
		try:
			agent.run_console_interface()
		except Exception as e:
			print(f"Console interface error: {e}")
		finally:
			# Cleanup
			if agent.falkordb_tool:
				agent.falkordb_tool.close()
		
		return 0
		
	except KeyboardInterrupt:
		print("\nProgram interrupted by user.")
		return 130
	except Exception as e:
		print(f"Unexpected error: {e}")
		print("Please check the system requirements and try again")
		return 1


if __name__ == "__main__":
	sys.exit(main())
