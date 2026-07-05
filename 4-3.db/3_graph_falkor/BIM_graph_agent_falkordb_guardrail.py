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
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
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
				if attempt > 0:
					print(f"Retrying FalkorDB connection (attempt {attempt + 1}/{max_retries})...")
				
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
					return True
				
			except Exception as e:
				if attempt >= max_retries - 1:
					print(f"FalkorDB connection failed: {e}")
					print("Check: 1) Server running 2) .env settings 3) Credentials 4) Network")
				
				if attempt < max_retries - 1:
					time.sleep(retry_delay)
		
		return False
	
	def close(self):
		"""Close database connection"""
		if self.client:
			try:
				self.client = None
				self.graph = None
			except Exception as e:
				print(f"Error closing connection: {e}")
	
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
					if attempt < max_retries - 1:
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


class CypherValidator:
	"""Cypher 쿼리 검증 클래스 (Solution 3 + Phase 1)"""
	
	# 유효한 IFC 노드 라벨들
	VALID_IFC_LABELS = {
		'IfcBeam', 'IfcBuilding', 'IfcBuildingStorey', 'IfcCovering', 
		'IfcDoor', 'IfcFooting', 'IfcFurnishingElement', 'IfcMember',
		'IfcOpeningElement', 'IfcRailing', 'IfcRoof', 'IfcSite', 
		'IfcSlab', 'IfcSpace', 'IfcStair', 'IfcStairFlight', 
		'IfcWall', 'IfcWallStandardCase', 'IfcWindow', 'IFCFile'
	}
	
	# 유효한 관계 타입들
	VALID_RELATIONSHIPS = {
		'AGGREGATES', 'BELONGS_TO_FILE', 'CONTAINED_IN'
	}
	
	# 라벨 매핑 (잘못된 입력 -> 올바른 라벨)
	LABEL_MAPPINGS = {
		'IfcFloor': 'IfcBuildingStorey',
		'IfcFloors': 'IfcBuildingStorey',
		'IfcLevel': 'IfcBuildingStorey',
		'IfcStory': 'IfcBuildingStorey',
		'IfcStorey': 'IfcBuildingStorey',
		'IfcRoom': 'IfcSpace',
	}
	
	# 존재할 수 없는 속성들 (엔티티별)
	IMPOSSIBLE_PROPERTIES = {
		'IfcSpace': ['cost', 'price', 'construction_cost', 'material', 'weight', 'occupancyrate', 'occupancy_rate'],
		'IfcWall': ['cost', 'price', 'temperature', 'humidity'],
		'IfcDoor': ['cost', 'price', 'temperature', 'firerating', 'fire_rating'],
		'IfcWindow': ['cost', 'price', 'temperature'],
	}
	
	@staticmethod
	def validate_cypher(cypher: str) -> tuple:
		"""
		Cypher 쿼리의 기본 유효성 검증
		
		Returns:
			(is_valid, error_message) 튜플
		"""
		if not cypher or not cypher.strip():
			return False, "Empty query"
		
		cypher = cypher.strip()
		
		# 1. 반드시 MATCH, CREATE, MERGE, WITH로 시작
		if not re.match(r'^(MATCH|CREATE|MERGE|WITH)\s+', cypher, re.IGNORECASE):
			return False, "Query must start with MATCH, CREATE, MERGE, or WITH"
		
		# 2. RETURN 문이 있어야 함 (READ 쿼리의 경우)
		if cypher.upper().startswith('MATCH') and 'RETURN' not in cypher.upper():
			return False, "MATCH query must have RETURN clause"
		
		# 3. 괄호 쌍 검사
		if cypher.count('(') != cypher.count(')'):
			return False, "Unmatched parentheses"
		
		if cypher.count('{') != cypher.count('}'):
			return False, "Unmatched curly braces"
		
		# 4. SQL 문법 섞임 검사
		sql_keywords = ['SELECT', 'FROM', 'JOIN', 'INSERT', 'UPDATE']
		if any(f' {kw} ' in f' {cypher.upper()} ' for kw in sql_keywords):
			return False, "SQL syntax detected - this is Cypher, not SQL"
		
		return True, "Valid"
	
	@staticmethod
	def validate_labels(cypher: str) -> Tuple[bool, str]:
		"""Cypher에 사용된 라벨이 유효한지 검증"""
		# 라벨 추출: (:IfcWall), (w:IfcSpace) 패턴
		label_pattern = r':([A-Z][a-zA-Z0-9_]*)'
		found_labels = set(re.findall(label_pattern, cypher))
		
		invalid_labels = found_labels - CypherValidator.VALID_IFC_LABELS
		
		if invalid_labels:
			# 제안 가능한 라벨 찾기
			suggestions = []
			for invalid in invalid_labels:
				if invalid in CypherValidator.LABEL_MAPPINGS:
					suggestions.append(f"{invalid} -> {CypherValidator.LABEL_MAPPINGS[invalid]}")
			
			if suggestions:
				return False, f"Invalid labels found. Did you mean: {', '.join(suggestions)}?"
			else:
				return False, f"Invalid labels: {invalid_labels}. Valid labels: {CypherValidator.VALID_IFC_LABELS}"
		
		return True, "Labels valid"
	
	@staticmethod
	def validate_relationships(cypher: str) -> Tuple[bool, str]:
		"""Cypher에 사용된 관계가 유효한지 검증"""
		# 관계 추출: [:CONTAINS], -[:AGGREGATES]-> 패턴
		rel_pattern = r'\[:([A-Z_]+)\]'
		found_rels = set(re.findall(rel_pattern, cypher))
		
		invalid_rels = found_rels - CypherValidator.VALID_RELATIONSHIPS
		
		if invalid_rels:
			return False, f"Invalid relationships: {invalid_rels}. Valid: {CypherValidator.VALID_RELATIONSHIPS}"
		
		return True, "Relationships valid"
	
	@staticmethod
	def check_impossible_properties(query: str, cypher: str) -> Tuple[bool, str]:
		"""존재할 수 없는 속성 요청 감지"""
		query_lower = query.lower().replace('_', '').replace('-', '')
		
		# Cypher에서 엔티티 타입 추출
		for entity_type, impossible_props in CypherValidator.IMPOSSIBLE_PROPERTIES.items():
			if entity_type in cypher:
				# 쿼리에 불가능한 속성이 언급되었는지 확인 (대소문자 무시, 언더스코어 무시)
				for prop in impossible_props:
					prop_normalized = prop.lower().replace('_', '').replace('-', '')
					if prop_normalized in query_lower:
						return False, f"'{prop}' is not available for {entity_type}. Try querying .properties field instead."
		
		return True, "Properties check passed"
	
	@staticmethod
	def detect_nested_property_access(cypher: str) -> Tuple[bool, str]:
		"""중첩 속성 직접 접근 감지 (예: s.properties.area)"""
		# properties.xxx 패턴 찾기
		nested_pattern = r'\.properties\.[a-zA-Z_][a-zA-Z0-9_]*'
		if re.search(nested_pattern, cypher):
			return False, "Nested property access (e.g., .properties.area) is not supported. Use RETURN .properties and process in application."
		
		return True, "No nested property access"
	
	@staticmethod
	def has_hallucination_markers(cypher: str) -> bool:
		"""환각(hallucination) 징후 감지"""
		# 너무 긴 쿼리
		if len(cypher) > 500:
			return True
		
		# 자연어 설명 포함 감지
		explanation_patterns = [
			r'this query', r'the following', r'here is',
			r'we can', r'you can', r'to find', r'in order to'
		]
		
		for pattern in explanation_patterns:
			if re.search(pattern, cypher, re.IGNORECASE):
				return True
		
		return False


class HallucinationTester:
	TEST_CASES = [
		# 형식: (질문, 예상_Cypher, 카테고리)
		("What IFC files are loaded?", "MATCH (f:IFCFile) RETURN f.fileName, f.fileSize, f.importDate", "file_query"),
		("List all properties of space A204", "MATCH (s:IfcSpace {name: 'A204'}) RETURN s.name, s.globalId, s.properties", "property_query"),
		("How many IfcWall are there?", "MATCH (w:IfcWall) RETURN count(w)", "count_query"),
		("Show me all IfcDoor", "MATCH (d:IfcDoor) RETURN d.name, d.globalId, d.properties LIMIT 100", "list_query"),
		("Count IfcWallStandardCase", "MATCH (w:IfcWallStandardCase) RETURN count(w)", "count_query"),
		("Get properties of space A204", "MATCH (s:IfcSpace {name: 'A204'}) RETURN s.name, s.globalId, s.properties", "property_query"),
		("List all IfcSpace names", "MATCH (s:IfcSpace) RETURN s.name LIMIT 100", "list_query"),
		("How many IfcWindow?", "MATCH (w:IfcWindow) RETURN count(w)", "count_query"),
		("What is the construction cost of space A204?", "REFUSE:", "non_existent_property"),
		("Show me all walls on the second floor that are connected to spaces larger than 50 square meters", "REFUSE:", "complex_multi_condition"),
		("SELECT * FROM spaces WHERE area > 100", "REFUSE:", "sql_syntax"),
		("List all properties of the bathroom on the first floor", "REFUSE:", "ambiguous_reference"),
		("Calculate the average area of all spaces per floor", "REFUSE:", "complex_aggregation"),
		("Find all windows that belong to walls in space A204", "REFUSE:", "complex_relationship"),
		("How many IfcFloors are there?", "REFUSE:", "wrong_label"),
		("Get the Pset_SpaceCommon.NetFloorArea value for space A204", "REFUSE:", "nested_property_access"),
		("Show all IfcBeam elements", "MATCH (b:IfcBeam) RETURN b.name, b.globalId, b.properties LIMIT 100", "list_new_entity"),
		("Get IfcRoof properties", "MATCH (r:IfcRoof) RETURN r.name, r.globalId, r.properties LIMIT 100", "property_new_entity"),
		("What is the fireRating of all doors?", "REFUSE:", "realistic_fake_property"),
		("List all IfcRoom in the building", "REFUSE:", "plausible_wrong_label"),
		("Find spaces with occupancyRate greater than 0.8", "REFUSE:", "fake_property_with_condition"),
	]
	
	def __init__(self, agent):
		self.agent = agent
		self.results = []
	
	def evaluate_query(self, query: str, expected_cypher: str, category: str) -> Dict[str, Any]:
		"""
		Cypher 쿼리 생성 테스트:
		- 생성된 Cypher와 예상 Cypher를 비교
		- 정규화된 형태로 비교 (공백, 대소문자 무시)
		"""
		try:
			# Cypher 생성
			normalized_query = self.agent.normalize_query(query)
			raw_cypher = self.agent.cypher_chain.invoke({"query": normalized_query})
			generated_cypher = self.agent.clean_cypher_query(raw_cypher)
			
			# Cypher 정규화 함수
			def normalize_cypher(cypher: str) -> str:
				# 공백 정규화, 대소문자 통일, 작은따옴표/큰따옴표 통일
				normalized = re.sub(r'\s+', ' ', cypher.strip().upper())
				normalized = normalized.replace('"', "'")
				return normalized
			
			expected_normalized = normalize_cypher(expected_cypher)
			generated_normalized = normalize_cypher(generated_cypher)
			
			# 비교 로직
			if expected_cypher.startswith("REFUSE:"):
				# 거부해야 하는 케이스
				match = generated_cypher.startswith("REFUSE:")
			else:
				# 정상 쿼리 케이스 - 핵심 부분 포함 여부 확인
				# MATCH, RETURN 절의 핵심 요소가 모두 포함되어 있는지 확인
				expected_parts = expected_normalized.split()
				match = all(part in generated_normalized for part in expected_parts if len(part) > 2)
			
			# 결과 구조
			return {
				'query': query,
				'category': category,
				'expected_cypher': expected_cypher,
				'generated_cypher': generated_cypher,
				'match': match
			}
			
		except Exception as e:
			return {
				'query': query,
				'category': category,
				'expected_cypher': expected_cypher,
				'generated_cypher': f'ERROR: {str(e)}',
				'match': False
			}
	
	def run_evaluation(self) -> Dict[str, Any]:
		print("\n" + "="*80)
		print("Cypher Query Generation Test")
		print("="*80)
		
		self.results = []
		
		for idx, (query, expected_cypher, category) in enumerate(self.TEST_CASES, 1):
			print(f"\n[{idx}/{len(self.TEST_CASES)}] {query[:60]}...")
			result = self.evaluate_query(query, expected_cypher, category)
			self.results.append(result)
			
			status = "MATCH" if result['match'] else "MISMATCH"
			print(f"  {status}")
			if not result['match']:
				print(f"  Expected: {result['expected_cypher'][:70]}...")
				print(f"  Generated: {result['generated_cypher'][:70]}...")
		
		metrics = self.calculate_metrics()
		self.print_metrics(metrics)
		return {'results': self.results, 'metrics': metrics}
	
	def calculate_metrics(self) -> Dict[str, float]:
		total = len(self.results)
		matched = sum(1 for r in self.results if r['match'])
		mismatched = total - matched
		accuracy = matched / total if total > 0 else 0
		
		category_accuracy = {}
		for category in set(r['category'] for r in self.results):
			cat_results = [r for r in self.results if r['category'] == category]
			cat_matched = sum(1 for r in cat_results if r['match'])
			category_accuracy[category] = cat_matched / len(cat_results) if cat_results else 0
		
		return {
			'total_cases': total,
			'matched': matched,
			'mismatched': mismatched,
			'accuracy': accuracy,
			'category_accuracy': category_accuracy
		}
	
	def print_metrics(self, metrics: Dict[str, float]):
		print("\n" + "="*80)
		print("Test Results Summary")
		print("="*80)
		print(f"\nOverall:")
		print(f"  Total:      {metrics['total_cases']}")
		print(f"  Matched:    {metrics['matched']}")
		print(f"  Mismatched: {metrics['mismatched']}")
		print(f"  Accuracy:   {metrics['accuracy']:.1%}")
		print(f"\nCategory Accuracy:")
		for category, acc in sorted(metrics['category_accuracy'].items()):
			print(f"  {category:35s}: {acc:.1%}")
	
	def save_results(self, output_path: str):
		"""
		간단한 JSON 구조로 저장:
		- 각 테스트 케이스의 질문, 예상/생성 Cypher, 매칭 여부
		- 사용자가 FalkorDB에서 직접 검증 가능
		"""
		metrics = self.calculate_metrics()
		output = {
			'test_cases': self.results,
			'summary': metrics
		}
		
		with open(output_path, 'w', encoding='utf-8') as f:
			json.dump(output, f, indent=2, ensure_ascii=False)
		print(f"\nResults saved: {output_path}")
		print(f"  You can verify Cypher queries in FalkorDB directly")


class BIMGraphAgent:
	"""BIM Graph Agent system using LangChain and Ollama models with FalkorDB
	"""
	
	def __init__(self):
		"""Initialize the BIM Graph Agent system"""
		self.falkordb_tool = None
		self.cypher_generator = None
		self.response_generator = None
		self.cypher_chain = None
		self.response_chain = None
		self.validator = CypherValidator()  # Solution 3

		self.setup_models()
		self.setup_chains()
		
	def setup_models(self):
		"""Setup and preload Ollama models for Cypher generation and response generation"""
		try:
			# Model: Cypher Query Generator & Response Generator (qwen2.5-coder:7b)
			self.cypher_generator = ChatOllama(
				model="qwen2.5-coder:7b",
				temperature=0.1,
				base_url="http://localhost:11434"
			)
			
			# Using same model for response generation
			self.response_generator = ChatOllama(
				model="qwen2.5-coder:7b",
				temperature=0.2,
				base_url="http://localhost:11434"
			)
			
			# Preload model with a simple test query
			try:
				test_result = self.cypher_generator.invoke("Test connection")
			except Exception as e:
				print(f"Warning: Model preload failed: {e}")
			
		except Exception as e:
			print(f"Error initializing Ollama models: {e}")
			print("Make sure Ollama is running and models are available")
			print("You can check available models with: ollama list")
			sys.exit(1)
	
	def setup_chains(self):
		"""Setup and cache LangChain chains for faster query processing"""
		try:
			self.cypher_chain = self.create_cypher_chain()
			self.response_chain = self.create_response_chain()
			
		except Exception as e:
			print(f"Error setting up chains: {e}")
			sys.exit(1)
	
	def setup_falkordb(self, host: str, port: int, username: str = None, password: str = None, graph_name: str = "bim"):
		"""Setup FalkorDB connection with enhanced error handling"""
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
		
		test_result = self.falkordb_tool.execute_query("MATCH (n) RETURN count(n) as nodeCount LIMIT 1")
		if not test_result.get("success", False):
			print(f"Warning: Could not access graph: {test_result.get('error', 'Unknown error')}")
		else:
			node_count = test_result.get("results", [{}])[0].get("nodeCount", 0)
			print(f"Connected: {node_count} nodes in graph")
		
		return True
	
	def normalize_query(self, query: str) -> str:
		"""
		사용자 쿼리 정규화 (Solution 1)
		질문 부호, 불필요한 단어 제거하여 LLM이 더 잘 이해하도록 함
		
		Args:
			query: 원본 사용자 질문
			
		Returns:
			정규화된 질문
		"""
		normalized = query.strip()
		
		# 일반적인 요청 패턴 제거
		request_patterns = [
			r'^(give\s+me\s+)', r'^(show\s+me\s+)', 
			r'^(can\s+you\s+)', r'^(could\s+you\s+)',
			r'^(please\s+)', r'^(i\s+want\s+to\s+)',
			r'^(i\s+need\s+)', r'^(tell\s+me\s+)',
			r'^(let\s+me\s+know\s+)',
		]
		
		for pattern in request_patterns:
			normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
		
		# 질문 부호 제거
		normalized = normalized.rstrip('?!.')
		
		# 중복 공백 제거
		normalized = re.sub(r'\s+', ' ', normalized).strip()
		
		return normalized
	
	def create_cypher_chain(self):
		"""Create LangChain chain with enhanced few-shot examples (Solution 2)"""
		
		schema_info = """
		BIM Graph Database Schema (FalkorDB):
		
		Node Labels: IfcBeam, IfcBuilding, IfcBuildingStorey, IfcCovering, IfcDoor, 
		             IfcFooting, IfcFurnishingElement, IfcMember, IfcOpeningElement, 
		             IfcRailing, IfcRoof, IfcSite, IfcSlab, IfcSpace, IfcStair, 
		             IfcStairFlight, IfcWall, IfcWallStandardCase, IfcWindow, IFCFile
		
		Common Properties: description, globalId, name, objectType, properties, 
		                   sourceFileId, tag
		
		Relationship Types: AGGREGATES, BELONGS_TO_FILE, CONTAINED_IN
		"""
		
		# 강화된 Few-shot 예시들 (Solution 2)
		few_shot_examples = """
		
		FEW-SHOT EXAMPLES (다양한 질문 패턴):
		
		Example 1:
		Question: "List all properties of space A204"
		Cypher: MATCH (s:IfcSpace {{name: 'A204'}}) RETURN s.name, s.globalId, s.properties
		
		Example 2:
		Question: "What are the properties of space A204"
		Cypher: MATCH (s:IfcSpace {{name: 'A204'}}) RETURN s.name, s.globalId, s.properties
		
		Example 3:
		Question: "Show me properties for space A204"
		Cypher: MATCH (s:IfcSpace {{name: 'A204'}}) RETURN s.name, s.globalId, s.properties
		
		Example 4:
		Question: "All properties of space A204"
		Cypher: MATCH (s:IfcSpace {{name: 'A204'}}) RETURN s.name, s.globalId, s.properties
		
		Example 5:
		Question: "Properties of space A204"
		Cypher: MATCH (s:IfcSpace {{name: 'A204'}}) RETURN s.name, s.globalId, s.properties
		
		Example 6:
		Question: "How many walls are there"
		Cypher: MATCH (w:IfcWall) RETURN count(w)
		
		Example 7:
		Question: "Count the number of IfcWallStandardCase"
		Cypher: MATCH (w:IfcWallStandardCase) RETURN count(w)
		
		Example 8:
		Question: "What walls do we have"
		Cypher: MATCH (w:IfcWall) RETURN w.name, w.globalId, w.properties LIMIT 100
		
		Example 9:
		Question: "List all doors"
		Cypher: MATCH (d:IfcDoor) RETURN d.name, d.globalId, d.properties LIMIT 100
		
		Example 10:
		Question: "Show me all the doors in the building"
		Cypher: MATCH (d:IfcDoor) RETURN d.name, d.globalId, d.properties LIMIT 100
		
		Example 11:
		Question: "Find elements in space A204"
		Cypher: MATCH (e)-[:CONTAINED_IN]->(s:IfcSpace {{name: 'A204'}}) RETURN e, s.name LIMIT 100
		
		Example 12:
		Question: "What IFC files are loaded"
		Cypher: MATCH (f:IFCFile) RETURN f.fileName, f.fileSize, f.importDate
		
		IMPORTANT PATTERNS:
		- Questions with/without "?" -> Process the same way
		- Focus on core request, ignore polite words
		- Always use specific IFC labels (IfcSpace, IfcWall, etc.)
		- Always return .properties for property-related queries
		- Use LIMIT 100 for list queries
		"""
		
		cypher_prompt = ChatPromptTemplate.from_messages([
			("system", """You are an expert at converting natural language to Cypher queries for BIM/IFC data.

""" + schema_info + """

""" + few_shot_examples + """

GENERATION RULES:
1. Generate ONLY a valid Cypher query, no explanations
2. Use ONLY these IFC labels: IfcSpace, IfcWall, IfcWallStandardCase, IfcDoor, IfcWindow, IfcBuildingStorey, etc.
3. Use ONLY these relationships: AGGREGATES, BELONGS_TO_FILE, CONTAINED_IN
4. For property queries: RETURN s.name, s.globalId, s.properties
5. For count queries: RETURN count(node)
6. For list queries: Add LIMIT 100
7. Properties are stored as nested JSON - return full .properties field
8. Do NOT access nested property paths (e.g., s.properties.area is INVALID)

IMPORTANT - WHEN TO REFUSE:
If the query asks for:
- Non-existent properties (cost, price, construction_cost, temperature, fireRating, occupancyRate, etc.)
- Complex aggregations with nested properties (e.g., filtering by properties.area > 100)
- Invalid IFC labels (e.g., IfcFloor -> use IfcBuildingStorey, IfcRoom -> use IfcSpace)
- Relationships not in the schema (CONTAINS, HAS, CONNECTED_TO, SUPPORTING, etc.)
- Ambiguous references without specific names/IDs
- Conditions on nested properties (e.g., WHERE s.properties.occupancyRate > 0.8)

Then respond with: REFUSE: [specific reason]

Otherwise, output ONLY the Cypher query (no markdown, no explanation).

Examples of REFUSE:
- "What is the cost of space A204?" -> REFUSE: Cost property not available in IFC data
- "How many IfcFloors?" -> REFUSE: IfcFloor is not valid. Use IfcBuildingStorey
- "List all IfcRoom" -> REFUSE: IfcRoom is not valid. Use IfcSpace
- "Find windows connected to walls" -> REFUSE: Complex relationship traversal not supported
- "What is the fireRating?" -> REFUSE: fireRating property not available in IFC data
- "Find spaces with occupancyRate > 0.8" -> REFUSE: occupancyRate property not available and cannot filter by nested properties
			"""),
			("user", "Convert this to Cypher: {query}")
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
	
	def process_query(self, user_query: str, max_retries: int = 2) -> str:
		"""
		Process user query with all three solutions integrated:
		- Solution 1: Input normalization
		- Solution 2: Enhanced few-shot (in create_cypher_chain)
		- Solution 3: Validation and retry
		
		Args:
			user_query: Natural language query from user
			max_retries: Maximum retry attempts for invalid Cypher
			
		Returns:
			Generated response string
		"""
		try:
			# Solution 1: Normalize input query
			normalized_query = self.normalize_query(user_query)
			
			# Solution 3: Validation and retry loop
			for attempt in range(max_retries + 1):
				try:
					# Step 1: Convert to Cypher
					if attempt == 0:
						raw_cypher_query = self.cypher_chain.invoke({"query": normalized_query})
					else:
						retry_prompt = f"""Generate valid FalkorDB Cypher for: {normalized_query}
						
						Rules:
						1. Start with MATCH
						2. Include RETURN
						3. Use IFC labels (IfcSpace, IfcWall, etc.)
						4. No SQL syntax
						5. Pure Cypher only"""
						raw_cypher_query = self.cypher_chain.invoke({"query": retry_prompt})
					
					# Step 1.5: Clean Cypher query
					cypher_query = self.clean_cypher_query(raw_cypher_query)
					
					# Phase 1: Check for explicit refusal
					if cypher_query.startswith('REFUSE:'):
						reason = cypher_query[7:].strip()
						return f"I cannot process this query.\n\nReason: {reason}\n\nSuggestion: Try asking for available data first, or simplify your query."
					
					# Phase 1: Enhanced validation
					# 1. 기본 Cypher 검증
					is_valid, error_msg = self.validator.validate_cypher(cypher_query)
					if not is_valid:
						if attempt < max_retries:
							continue
						else:
							return f"Error: Invalid Cypher syntax. {error_msg}"
					
					# 2. 라벨 검증
					labels_valid, label_msg = self.validator.validate_labels(cypher_query)
					if not labels_valid:
						return f"Error: {label_msg}"
					
					# 3. 관계 검증
					rels_valid, rel_msg = self.validator.validate_relationships(cypher_query)
					if not rels_valid:
						return f"Error: {rel_msg}\n\nValid relationships: AGGREGATES, BELONGS_TO_FILE, CONTAINED_IN"
					
					# 4. 불가능한 속성 검사
					props_valid, prop_msg = self.validator.check_impossible_properties(user_query, cypher_query)
					if not props_valid:
						return f"Error: {prop_msg}"
					
					# 5. 중첩 속성 접근 검사
					nested_valid, nested_msg = self.validator.detect_nested_property_access(cypher_query)
					if not nested_valid:
						return f"Error: {nested_msg}"
					
					# 6. 환각 마커 검사
					if self.validator.has_hallucination_markers(cypher_query):
						if attempt < max_retries:
							continue
					
					# Step 2: Execute Cypher query
					query_results = self.falkordb_tool.execute_query(cypher_query)
					
					if not query_results.get('success', False):
						if attempt < max_retries:
							continue
						else:
							return f"Error executing Cypher: {query_results.get('error', 'Unknown error')}"
					
					# Step 3: Generate response using pre-cached chain
					response = self.response_chain.invoke({
						"original_query": user_query,
						"cypher_query": cypher_query,
						"query_results": json.dumps(query_results, indent=2)
					})
					
					return response
					
				except Exception as e:
					if attempt >= max_retries:
						return f"Error: All retry attempts exhausted. Last error: {str(e)}"
			
			return "Error: Unexpected failure in retry loop"
			
		except Exception as e:
			return f"Error processing query: {str(e)}"
	
	def run_console_interface(self):
		"""Run interactive console interface"""
		print("BIM Graph Agent (FalkorDB)")
		print("Type 'quit' or 'exit' to stop")
		
		while True:
			try:
				# Get user input
				user_query = input("\nYour question: ").strip()
				
				# Check for exit commands
				if user_query.lower() in ['quit', 'exit', 'q']:
					print("Thank you for using BIM Graph Agent!")
					break
				
				if not user_query:
					continue
				
				# Process query
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
	cur_module_dir = Path(__file__).parent
	output_json_file = cur_module_dir / 'hallucination_guardrail_test_results.json'	
	parser = argparse.ArgumentParser(description='BIM Graph Agent - AI-powered BIM data query system')
	parser.add_argument('--test', action='store_true', default=True, help='Run hallucination detection evaluation')
	parser.add_argument('--test-output', type=str, default=output_json_file, 
	                   help='Output file for test results (default: hallucination_guardrail_test_results.json)')
	args = parser.parse_args()
	
	try:
		# Load environment
		try:
			env_config = load_environment()
		except Exception as e:
			print(f"Environment error: {e}")
			return 1
		
		# Initialize BIM Graph Agent
		try:
			agent = BIMGraphAgent()
		except Exception as e:
			print(f"Initialization failed: {e}")
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
		
		if args.test:
			tester = HallucinationTester(agent)
			evaluation_result = tester.run_evaluation()
			tester.save_results(args.test_output)
			accuracy = evaluation_result['metrics']['accuracy']
			if accuracy >= 0.8:
				print(f"\n[PASS] Test PASSED (Accuracy = {accuracy:.1%} >= 80%)")
				return 0
			else:
				print(f"\n[FAIL] Test FAILED (Accuracy = {accuracy:.1%} < 80%)")
				return 1
		else:
			try:
				agent.run_console_interface()
			except Exception as e:
				print(f"Console interface error: {e}")
			finally:
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
	main()
