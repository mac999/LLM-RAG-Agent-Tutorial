"""
BIM Graph Agent - AI-powered BIM data query system using LangChain and Neo4j

This system provides an intelligent interface to query BIM graph data stored in Neo4j
using natural language queries, which are converted to Cypher queries and processed
to return structured JSON responses.

Architecture:
1. User Input (Natural Language) -> 
2. LLM1 (qwen2.5-coder:7b) converts to Cypher -> 
3. Neo4j Query Execution -> JSON Result -> 
4. LLM2 (gemma3) generates user-friendly response

Usage:
	python BIM_graph_agent.py

Contact: Taewook Kang (laputa99999@gmail.com)
"""

import json, sys, os, time, re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_ollama import ChatOllama
from neo4j import GraphDatabase

# Add project source to path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

class Neo4jQueryTool:
	"""Tool for executing Cypher queries against Neo4j BIM graph database"""
	
	def __init__(self, uri: str, user: str, password: str, database: str = "elements"):
		"""
		Initialize Neo4j connection
		
		Args:
			uri: Neo4j server URI
			user: Username
			password: Password  
			database: Database name
		"""
		self.uri = uri
		self.user = user
		self.password = password
		self.database = database
		self.driver = None
		
	def connect(self, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
		"""
		Connect to Neo4j database with retry logic
		
		Args:
			max_retries: Maximum number of connection attempts
			retry_delay: Delay between retry attempts in seconds
		"""
		for attempt in range(max_retries):
			try:
				print(f"Attempting to connect to Neo4j (attempt {attempt + 1}/{max_retries})...")
				
				# Close existing driver if any
				if self.driver:
					self.driver.close()
				
				# Create new driver with connection pooling settings
				self.driver = GraphDatabase.driver(
					self.uri, 
					auth=(self.user, self.password),
					max_connection_lifetime=3600,  # 1 hour
					max_connection_pool_size=10,
					connection_acquisition_timeout=30
				)
				
				# Test connection
				with self.driver.session(database=self.database) as session:
					result = session.run("RETURN 1 as test")
					record = result.single()
					if record and record['test'] == 1:
						print("Neo4j connection successful!")
						return True
				
			except Exception as e:
				print(f"Neo4j connection attempt {attempt + 1} failed: {e}")
				
				if attempt < max_retries - 1:
					print(f"Retrying in {retry_delay} seconds...")
					time.sleep(retry_delay)
				else:
					print("All connection attempts failed.")
					print("Please check:")
					print("1. Neo4j server is running")
					print("2. Connection settings in .env file")
					print("3. Database credentials are correct")
					print("4. Network connectivity to Neo4j server")
		
		return False
	
	def close(self):
		"""Close database connection"""
		if self.driver:
			try:
				self.driver.close()
				print("Neo4j connection closed")
			except Exception as e:
				print(f"Error closing Neo4j connection: {e}")
	
	def test_connection(self) -> bool:
		"""Test if the database connection is still alive"""
		if not self.driver:
			return False
		
		try:
			with self.driver.session(database=self.database) as session:
				session.run("RETURN 1")
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
		if not self.driver:
			return {"success": False, "error": "Not connected to database", "results": []}
		
		for attempt in range(max_retries):
			try:
				with self.driver.session(database=self.database) as session:
					result = session.run(cypher_query)
					
					# Convert result to list of dictionaries
					records = []
					for record in result:
						record_dict = {}
						for key in record.keys():
							value = record[key]
							# Handle Neo4j node/relationship objects
							if hasattr(value, '_properties'):
								record_dict[key] = dict(value._properties)
							elif hasattr(value, 'type'):  # Relationship
								record_dict[key] = {
									"type": value.type,
									"properties": dict(value._properties) if hasattr(value, '_properties') else {}
								}
							else:
								record_dict[key] = value
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
	"""BIM Graph Agent system using LangChain and Ollama models"""
	
	def __init__(self):
		"""Initialize the BIM Graph Agent system"""
		self.neo4j_tool = None
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
			
			# Model 1: Cypher Query Generator (qwen2.5-coder:7b)
			print("Loading qwen2.5-coder:7b model...")
			self.cypher_generator = ChatOllama(
				model="qwen2.5-coder:7b",
				temperature=0.1,  # Low temperature for precise query generation
				base_url="http://localhost:11434"
			)
			
			# Model 2: Response Generator (using same model for optimal performance)
			print("Using qwen2.5-coder:7b for response generation too (single model approach)...")
			self.response_generator = ChatOllama(
				model="qwen2.5-coder:7b",
				temperature=0.2,  # Slightly higher temperature for natural responses
				base_url="http://localhost:11434"
			)
			
			print("Preloading models with test queries...")
			
			# Preload cypher generator with a simple test query
			try:
				test_cypher_result = self.cypher_generator.invoke("Test connection")
				print("✓ Cypher generator model loaded and ready")
			except Exception as e:
				print(f"Warning: Cypher generator preload failed: {e}")
			
			# Note: Using same model instance for both tasks - no separate preload needed
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
	
	def setup_neo4j(self, uri: str, user: str, password: str, database: str = "elements"):
		"""Setup Neo4j connection with enhanced error handling"""
		print(f"Setting up Neo4j connection to {uri}, database: {database}")
		
		self.neo4j_tool = Neo4jQueryTool(uri, user, password, database)
		
		if not self.neo4j_tool.connect():
			print("\nNeo4j Connection Failed!")
			print("Troubleshooting steps:")
			print("1. Ensure Neo4j is running:")
			print("   - Start Neo4j Desktop or Neo4j service")
			print("   - Check if Neo4j is accessible at", uri)
			print("2. Verify database credentials in .env file")
			print("3. Check if the 'elements' database exists in Neo4j")
			print("4. Try accessing Neo4j Browser at http://localhost:7474")
			return False
		
		# Test if we can access the elements database
		test_result = self.neo4j_tool.execute_query("MATCH (n) RETURN count(n) as nodeCount LIMIT 1")
		if not test_result.get("success", False):
			print(f"\nWarning: Could not access elements database: {test_result.get('error', 'Unknown error')}")
			print("Make sure the 'elements' database exists and contains BIM data")
			print("Run 'python import_ifc.py' first to import IFC data")
		else:
			node_count = test_result.get("results", [{}])[0].get("nodeCount", 0)
			print(f"Connected successfully! Found {node_count} nodes in elements database")
		
		return True
	
	def create_cypher_chain(self):
		"""Create LangChain chain for converting natural language to Cypher"""
		
		# Schema information prompt
		schema_info = """
		BIM Graph Database Schema (Based on Actual Database Structure):
		
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
		- Find space by room name: MATCH (s:IfcSpace) WHERE s.properties CONTAINS 'A204' RETURN s.name, s.properties
		"""
		
		cypher_prompt = ChatPromptTemplate.from_messages([
			("system", """You are an agent in converting natural language queries to Neo4j Cypher queries for BIM/IFC data.
			
			""" + schema_info + """
			
			IMPORTANT: Properties are stored as nested JSON. For property-related queries (area, volume, etc.):
			- Return the full properties JSON: RETURN s.name, s.properties
			- Let the response processor extract specific values from the JSON
			- Don't try to access specific nested paths as they vary by modeling tool
			
			Rules for Cypher generation:
			1. Always use proper Cypher syntax
			2. Use specific IFC labels (IfcSpace, IfcWall, IfcDoor, etc.) as node labels
			3. Access element properties directly from the node (e.g., s.properties, s.name, s.globalId)
			4. Do NOT traverse relationships for basic element properties  
			5. Use WHERE clauses for additional filtering by name, etc.
			6. Use LIMIT to prevent large result sets (default LIMIT 100)
			7. For counts, use count() function
			8. For file information, match on IFCFile nodes
			9. For property searches (area, volume, etc.), return the entire properties JSON and let response processing extract relevant values
			10. Use simple property access: s.properties (return full JSON for analysis)
			11. For specific known properties, try common patterns but always include full properties as backup
			
			CORRECT Examples:
			- MATCH (s:IfcSpace {{name: 'A204'}}) RETURN s.name, s.globalId, s.properties
			- MATCH (w:IfcWall) RETURN count(w)
			- MATCH (d:IfcDoor) RETURN d.name, d.globalId, d.properties LIMIT 10
			- MATCH (f:IFCFile) RETURN f.fileName, f.fileSize
			- For property queries: Always include s.properties in RETURN clause
			
			WRONG Examples:
			- MATCH (e:Element {{ifcClass: 'IfcSpace'}}) (Use direct IfcSpace label)
			- Trying to access specific property paths like s.properties.PSet_Name.Property (paths vary by tool)
			
			Generate ONLY the Cypher query without explanation or markdown formatting.
			"""),
			("user", "Convert this query to Cypher: {query}")
		])
		
		return cypher_prompt | self.cypher_generator | StrOutputParser()
	
	def create_response_chain(self):
		"""Create LangChain chain for generating user-friendly responses"""
		
		response_prompt = ChatPromptTemplate.from_messages([
			("system", """You are a helpful BIM agent assistant specialized in analyzing IFC element properties and answering user questions. You receive JSON results from Neo4j database queries about BIM/IFC data.
			
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
			
			# Remove markdown code blocks (various formats)
			cleaned = re.sub(r'```cypher\s*\n?', '', cleaned, flags=re.IGNORECASE)
			cleaned = re.sub(r'```sql\s*\n?', '', cleaned, flags=re.IGNORECASE)
			cleaned = re.sub(r'```\s*\n?', '', cleaned)
			
			# Remove common prefixes that LLMs might add
			cleaned = re.sub(r'^(cypher|sql):\s*', '', cleaned, flags=re.IGNORECASE)
			cleaned = re.sub(r'^(cypher|sql)\s+', '', cleaned, flags=re.IGNORECASE)
			cleaned = re.sub(r'^query:\s*', '', cleaned, flags=re.IGNORECASE)
			
			# Remove explanation text (everything after newlines that don't contain Cypher keywords)
			cypher_keywords = ['MATCH', 'WHERE', 'RETURN', 'WITH', 'CREATE', 'DELETE', 'SET', 'REMOVE', 'MERGE', 'UNWIND', 'ORDER BY', 'LIMIT', 'SKIP']
			lines = cleaned.split('\n')
			cypher_lines = []
			
			for line in lines:
				line = line.strip()
				if not line:
					continue
				
				# Check if line contains Cypher keywords or continues a query
				is_cypher_line = any(keyword in line.upper() for keyword in cypher_keywords)
				is_continuation = line.startswith(('(', ')', '[', ']', '{', '}', ',', '.', '-', ':', '<', '>', '='))
				
				if is_cypher_line or is_continuation or not cypher_lines:
					cypher_lines.append(line)
				else:
					# Stop processing when we hit explanatory text
					break
			
			cleaned = ' '.join(cypher_lines)
			
			# Normalize whitespace
			cleaned = re.sub(r'\s+', ' ', cleaned)
			
			# Remove leading/trailing whitespace
			cleaned = cleaned.strip()
			
			# Remove trailing punctuation that's not part of Cypher
			cleaned = re.sub(r'[.!?]+\s*$', '', cleaned)
			
			# Remove trailing semicolons
			cleaned = re.sub(r';\s*$', '', cleaned)
			
			# Remove quotes around the entire query
			if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
				cleaned = cleaned[1:-1]
			
			return cleaned
			
		except Exception as e:
			print(f"Warning: Error cleaning Cypher query: {e}")
			# Fallback: basic cleanup
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
			query_results = self.neo4j_tool.execute_query(cypher_query)
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
		print("BIM Graph Agent - AI-Powered BIM Data Query System")
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
	env_path = Path(__file__).parent / '.env'
	if env_path.exists():
		load_dotenv(env_path)
	
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

def main():
	try:
		print("Starting BIM Graph Agent...")
		
		# Load environment
		try:
			env_config = load_environment()
			print("Environment configuration loaded")
		except Exception as e:
			print(f"Environment configuration error: {e}")
			print("Please check your .env file")
			return 1
		
		# Initialize BIM Graph Agent (this will preload models and chains)
		try:
			print("Initializing BIM Graph Agent system...")
			agent = BIMGraphAgent()
			print("BIM Graph Agent system ready!")
		except Exception as e:
			print(f"Failed to initialize BIM Graph Agent: {e}")
			print("Please check if Ollama is running and models are available")
			return 1
		
		# Setup Neo4j connection
		try:
			if not agent.setup_neo4j(
				uri=env_config['uri'],
				user=env_config['user'],
				password=env_config['password'],
				database=env_config['database']
			):
				print("\nCannot proceed without Neo4j connection.")
				return 1
		except Exception as e:
			print(f"Neo4j setup error: {e}")
			return 1
		
		# Run console interface
		try:
			agent.run_console_interface()
		except Exception as e:
			print(f"Console interface error: {e}")
		finally:
			# Cleanup
			if agent.neo4j_tool:
				agent.neo4j_tool.close()
		
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