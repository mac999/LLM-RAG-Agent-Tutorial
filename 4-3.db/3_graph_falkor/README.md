# BIM Graph Agent

BIM graph agent with data processing system that converts IFC files to Neo4j graph database and provides AI-powered natural language querying capabilities. This project is example and demonstration to show how to use graph database like neo4j as the viewpoint of RAG and AI Agent development.

<p align="center">
<img src="https://github.com/mac999/BIM_graph_agent/blob/main/doc/img2.jpg" width="750"> </img></br>
<img src="https://github.com/mac999/BIM_graph_agent/blob/main/doc/img1.jpg" height="200"> </img>
<img src="https://github.com/mac999/BIM_graph_agent/blob/main/doc/img3.jpg" height="200"> </img></br>
<img src="https://github.com/mac999/BIM_graph_agent/blob/main/doc/img9.jpg" height="255"> </img>
<img src="https://github.com/mac999/BIM_graph_agent/blob/main/doc/img7.jpg" height="255"> </img>
<img src="https://github.com/mac999/BIM_graph_agent/blob/main/doc/img8.jpg" height="255"> </img>
</p>

## Features

### Core System
- **IFC to Graph Conversion**: Automatically processes IFC files and converts them to Neo4j graph database
- **Data Integrity**: Accurately converts IFC elements and relationships without data loss
- **File Metadata Management**: Stores and links IFC file information with graph structure

### BIM Graph Agent (AI-Powered Expert System)
- **Natural Language Querying**: Ask questions about BIM data in plain English or Korean
- **Smart Property Analysis**: Analyzes nested JSON properties regardless of modeling tool
- **Interactive Console Interface**: Real-time conversational interface for BIM data exploration

## Requirements

### System Requirements
- Python 3.9 or higher
- Neo4j database (version 4.0 or higher)
- 8GB RAM minimum (16GB recommended for large IFC files)
- 2GB free disk space for database storage

### AI Agent Requirements
- Ollama server (local LLM runtime)
- qwen2.5-coder:7b model (for Cypher query generation)
- 8GB VRAM recommended (NVIDIA GPU optional for faster processing)
- Internet connection for initial model download

## Installation
1. Create elements database in Neo4j like below
<p align="center">
   <img src="https://github.com/mac999/BIM_graph_agent/blob/main/doc/db1.jpg" height="300"></img>
</p>

2. Clone or download this project
3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
   
   Required packages include:
   - `ifcopenshell` - IFC file parsing
   - `neo4j` - Neo4j database driver
   - `langchain` ecosystem - AI framework
   - `ollama` - Local LLM integration
   - `streamlit` - Web interface framework
4. Configure environment variables in `.env` file:
   ```
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   NEO4J_DATABASE=elements
   ```
5. Install and setup Ollama for BIM Graph Agent:
   ```bash
   # Install Ollama from https://ollama.ai
   
   # Pull required model (optimized single model approach)
   ollama pull qwen2.5-coder:7b
   
   # Start Ollama server
   ollama serve
   ```

## Usage

### Create elements graph databsae in Neo4j from input IFC files
```bash
python import_ifc.py [options]

Options:
  --input-dir DIR     Input directory containing IFC files (default: ./input)
  --clear-db          Initialize database before conversion
  --log-level LEVEL   Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  --no-log-file       Disable file logging
  --validate          Run validation after conversion
  --stats             Output statistics after conversion completion
  --help              Show help message
```

Convert all IFC files in the input directory:
```bash
python import_ifc.py --input-dir ./input --stats
```

Clear database and convert with debug logging:
```bash
python import_ifc.py --clear-db --log-level DEBUG --validate
```

### BIM Graph Agent (AI Expert System)

#### Console Interface

Launch the AI-powered natural language console interface:
```bash
python BIM_graph_agent.py
```

#### Web Interface

Launch the Streamlit web application for a user-friendly interface:
```bash
streamlit run BIM_graph_agent_web.py
```

The web app will automatically open in your browser at `http://localhost:8501`

**Web App Features:**
- Dark mode chatbot interface
- Real-time query processing
- Markdown rendering for formatted responses

#### Example Queries

**Basic Element Queries:**
- How many walls are in the building?
- Show me all doors in the project
- List all windows with their properties
<p align="center">
   <img src="https://github.com/mac999/BIM_graph_agent/blob/main/doc/img4.jpg" width="400"></img>
</p>

**Property-Specific Queries:**
- What is the area of room A204?
<p align="center">
   <img src="https://github.com/mac999/BIM_graph_agent/blob/main/doc/img5.jpg" width="400"></img>
</p>

**File and Metadata Queries:**
- What IFC files are loaded in the database?
- Show me the file information for this model
<p align="center">
   <img src="https://github.com/mac999/BIM_graph_agent/blob/main/doc/img6.jpg" width="400"></img>
</p>

**Advanced Analysis:**
- Find all load-bearing walls

**TBD (Relationship Queries etc)**
- Find all spaces on the Level 2
- Show me walls with thickness greater than 200mm
- What elements are connected to this wall?
- Find all elements that belong to the ground floor
- Calculate total floor area by level
- List all mechanical equipment in the building

## Project Structure

```
BIM_graph_rag/
├── input/                      # Input directory for IFC files
│   └── Duplex_A_20110907.ifc   # Sample IFC file
├── src/                        # Source code modules
│   ├── ifc_parser.py           # IFC file parsing module
│   ├── neo4j_database.py       # Neo4j database connection module
│   ├── graph_converter.py      # IFC to graph conversion logic
│   └── utils.py                # Logging utilities
├── logs/                       # Log files directory
├── requirements.txt            # Required Python packages
├── .env                        # Environment configuration
├── import_ifc.py              # Main CLI application
├── BIM_graph_expert.py        # BIM Graph Agent (AI expert system)
└── README.md                  # This file
```

## Graph Data Model

### Nodes
- **IFCFile**: Contains file metadata (filename, path, creation date, etc.)
- **Element**: Represents IFC elements with labels like `:Element:IfcWall`, `:Element:IfcDoor`

### Node Properties
- `globalId`: IFC GlobalId (unique identifier)
- `name`: Element name
- `ifcClass`: IFC class name
- `description`: Element description
- `sourceFileId`: Reference to source IFC file
- `properties`: PropertySet information (stored as JSON)

### Relationships
- `BELONGS_TO_FILE`: Links elements to their source IFC file
- `AGGREGATES`: Aggregation relationships between elements
- `CONNECTS_TO`: Connection relationships between elements
- `CONTAINED_IN`: Spatial containment relationships
- `ASSIGNED_TO`: Group assignment relationships

## Output

The application provides:
- Real-time progress logging
- Conversion statistics (node/relationship counts)
- Element type distribution
- Validation results (optional)
- Comprehensive error handling and reporting

## BIM Graph Agent Architecture

The BIM Graph Agent is an advanced AI system that enables natural language querying of BIM graph data with intelligent property analysis.

### System Architecture
1. **Natural Language Processing**: User enters questions in English or Korean
2. **Smart Query Generation**: qwen2.5-coder:7b model creates optimized Cypher queries
3. **Graph Data Retrieval**: Executes queries against Neo4j elements database
4. **Intelligent Property Analysis**: Analyzes nested JSON properties from any modeling tool
5. **Contextual Response Generation**: Provides detailed answers with data sources and units

### Key Capabilities
- **Universal Property Support**: Analyzes properties from any BIM modeling tool (Revit, ArchiCAD, Tekla, etc.)
- **Multi-Language Support**: Handles English and Korean property names and queries
- **Smart Schema Detection**: Automatically adapts to different IFC modeling approaches
- **Performance Optimization**: Single LLM model approach eliminates memory switching overhead
- **Interactive Learning**: Shows generated Cypher queries for educational purposes

### Advanced Features
- **Flexible Property Matching**: Finds area, volume, and other properties regardless of naming conventions
- **Cross-Tool Compatibility**: Works with models from different BIM software vendors
- **Intelligent Fallback**: Returns full property JSON when specific paths are unavailable
- **Real-Time Analysis**: Processes queries and responses in real-time conversation flow

### Usage Guidelines
- Ask questions in natural language (no technical Cypher knowledge required)
- Be specific about elements (walls, doors, spaces, etc.) for better results
- Property queries automatically search through all available property sets
- The system shows the generated Cypher query and data sources for transparency

## Performance Optimization

### Current Performance Analysis

**Strengths:**
- Modular architecture with excellent scalability
- Universal BIM software compatibility (Revit, ArchiCAD, Tekla)
- Natural language interface without technical knowledge requirement
- Educational value through Cypher query visualization

**Performance Bottlenecks:**
- **Response Time**: 10+ seconds (RTX 3090 12GB VRAM limitation)
- **Model Size**: qwen2.5-coder:7b (4.7GB) loading overhead
- **Memory Constraints**: Single GPU VRAM limitations
- **Concurrent Users**: Limited to single-user sessions

### Optimization Strategies

#### 1. Model Optimization (Immediate Impact)

**Lightweight Models:**
```bash
# Replace current model with smaller alternatives
ollama pull qwen2.5-coder:3b     # 50% size reduction
ollama pull deepseek-coder:6.7b  # Coding-optimized
```

**Quantized Models:**
```bash
# 4-bit quantization for 75% memory reduction
ollama pull qwen2.5-coder:7b-q4_0  # ~2.5GB
```

#### 2. High-Performance Inference Libraries

**llama-cpp-python (Recommended for Simplicity):**
- Direct model loading without Ollama overhead
- Automatic CPU/GPU detection and optimization
- GGUF quantized model support (4-8bit)
- 50-70% performance improvement with minimal setup

```bash
pip install llama-cpp-python
```

**vLLM (Maximum Performance):**
- 2-5x inference speed improvement
- Advanced memory management and optimization
- Multi-GPU tensor parallelism support
- Production-grade deployment features

```bash
pip install vllm>=0.2.0
```

**Optimum (Hugging Face Integration):**
- One-click optimization with minimal code changes
- ONNX Runtime automatic graph optimization
- Cross-platform hardware acceleration

```bash
pip install optimum[onnxruntime-gpu]
```

#### 3. Hardware Scaling

**Multi-GPU Configuration:**
- RTX 3090 x2 setup for parallel processing
- vLLM tensor parallelism support
- 80-90% performance improvement potential

### Performance Improvement Roadmap

| Phase | Duration | Methods | Expected Improvement | Cost |
|-------|----------|---------|---------------------|------|
| **Phase 1** | 1-2 days | llama-cpp-python + Lightweight models | 50-60% (10s → 4-5s) | Free |
| **Phase 2** | 1 week | vLLM or Optimum integration | 70-80% (10s → 2-3s) | Free |
| **Phase 3** | 1 month | Multi-GPU + Model fine-tuning | 85% (10s → 1.5s) | $1000+ |

### Recommended Quick Wins

1. **Switch to llama-cpp-python** - Direct model loading, 50% speed boost
2. **Use qwen2.5-coder:3b or quantized models** - Immediate memory and speed improvement
3. **Optimize system settings** - Neo4j indexing and Ollama configuration

### Library Comparison

| Library | Setup Complexity | Performance Gain | Memory Savings | Stability |
|---------|------------------|------------------|----------------|-----------|
| **llama-cpp-python** | Very Easy | 50-70% | 30% | High |
| **Optimum** | Easy | 30-50% | 20% | High |
| **vLLM** | Moderate | 70-200% | 10% | Good |
| **CTranslate2** | Easy | 80-150% | 25% | High |

### Alternative Solutions

**Cloud API Integration:**
- OpenAI GPT-4 or Anthropic Claude API
- Sub-second response times
- Monthly cost: $50-200 depending on usage
- 95%+ performance improvement

**Dedicated Inference Server:**
- vLLM or llama-cpp-python server deployment
- Load balancing for multiple users
- Professional-grade performance optimization

## Database Selection Guidelines

### Graph Database vs Traditional Database

This project uses Neo4j as a demonstration of graph database capabilities for BIM data. However, the choice between graph and traditional databases depends on specific use cases and requirements.

#### When to Choose Graph Databases (Neo4j)

**Optimal Use Cases:**
- **Complex Multi-hop Queries**: 10+ level deep relationship traversals
- **Real-time Path Finding**: Navigation, routing, network analysis
- **Operations Research Problems**: Supply chain optimization, logistics
- **Pattern Detection**: Fraud detection, recommendation engines
- **Network Analysis**: Social networks, infrastructure networks

**Example Scenarios:**
```cypher
-- Complex relationship traversal (Neo4j strength)
MATCH path = shortestPath((start)-[*10..50]-(end))
WHERE all(r in relationships(path) WHERE r.weight < 100)
RETURN path, length(path) as hop_count
```

**Advantages:**
- Exceptional performance for deep graph traversals
- Intuitive modeling of complex relationships
- Built-in graph algorithms and analytics
- Visual query representation with Cypher

**Disadvantages:**
- Steep learning curve (Cypher vs SQL)
- Limited aggregation and reporting capabilities
- Higher operational complexity
- Enterprise licensing costs ($15K-500K+ annually)
- Single-node limitations in Community Edition

#### When to Choose Traditional Databases

**MySQL/PostgreSQL Optimal Use Cases:**
- **Simple to Medium Queries**: 1-3 level joins (90% of BIM queries)
- **Property-based Searches**: Area, material, quantity lookups
- **Aggregation and Reporting**: Statistics, summaries, dashboards
- **High-frequency CRUD Operations**: Standard web applications

**Example Schema:**
```sql
-- Relational approach for BIM data
CREATE TABLE ifc_elements (
    id VARCHAR(36) PRIMARY KEY,
    ifc_class VARCHAR(50),
    name VARCHAR(255),
    properties JSON,
    INDEX idx_class (ifc_class),
    INDEX idx_area ((CAST(properties->'$.Area' AS DECIMAL)))
);
```

**Advantages:**
- Mature ecosystem and tooling
- Universal SQL knowledge
- Excellent performance for simple queries
- Cost-effective (free/low-cost licensing)
- Rich aggregation and analytical capabilities

**MongoDB Optimal Use Cases:**
- **Document-centric BIM Data**: Natural fit for IFC property sets
- **Flexible Schema Evolution**: Varying property structures
- **Horizontal Scaling**: Large datasets across multiple servers
- **JSON-native Operations**: Direct property manipulation

### Performance Comparison

| Query Type | Neo4j | MySQL | MongoDB | PostgreSQL |
|------------|-------|-------|---------|------------|
| **1-2 hop relationships** | 10ms | 5ms | 8ms | 6ms |
| **10+ hop traversals** | 50ms | 10s+ | N/A | 15s+ |
| **Property aggregations** | 100ms | 20ms | 30ms | 25ms |
| **Full-text search** | Limited | Good | Excellent | Excellent |
| **Complex analytics** | Limited | Excellent | Good | Excellent |

### Selection Decision Matrix

#### Choose **Neo4j** when:
- Complex relationship analysis is core business requirement
- 10+ hop graph traversals are frequent
- Real-time pathfinding is essential
- Budget allows for enterprise licensing ($50K+)
- Team has graph database expertise

#### Choose **MySQL/PostgreSQL** when:
- Property-based queries dominate (90% of BIM use cases)
- Cost optimization is priority
- Standard SQL expertise is available
- Reporting and analytics are important
- Proven stability is required

#### Choose **MongoDB** when:
- Document structure varies significantly
- Horizontal scaling is needed
- JSON manipulation is frequent
- Schema flexibility is important

#### Choose **Hybrid Approach** when:
```python
# Smart routing based on query complexity
class HybridBIMAgent:
    def process_query(self, query):
        if self.requires_deep_traversal(query):
            return self.neo4j_engine.process(query)  # Complex relationships
        else:
            return self.mysql_engine.process(query)  # Standard queries
```

### Recommended Architecture

**For BIM Projects:**

1. **Education/Demo**: Neo4j Community (free) - Good for learning graph concepts
2. **Small Projects**: MySQL + JSON properties - Cost-effective and sufficient
3. **Medium Projects**: PostgreSQL + specialized graph queries when needed
4. **Large Enterprise**: Hybrid approach - MySQL primary + Neo4j for complex analysis
5. **Research Projects**: Neo4j Enterprise - Advanced graph analytics capabilities

### Migration Considerations

**From Neo4j to SQL:**
- 5-10x faster development for standard queries
- 80% cost reduction in licensing and operations
- Easier team onboarding and maintenance
- Better integration with existing tools

**From SQL to Neo4j:**
- Significant performance gain for relationship queries
- Better modeling of complex interconnections
- Enhanced analytical capabilities
- Higher operational overhead

## Troubleshooting

### Common Issues

1. **Neo4j Connection Failed**
   - Ensure Neo4j is running
   - Check connection settings in `.env` file
   - Verify database credentials

2. **IFC File Parsing Failed**
   - Check if IFC file is valid (IFC2x3 or IFC4 schema)
   - Ensure file is not corrupted
   - Check file permissions

3. **Memory Issues with Large Files**
   - Increase available system memory
   - Process files individually if needed

4. **Slow AI Response Times**
   - Consider switching to lighter models (qwen2.5-coder:3b)
   - Optimize Ollama configuration settings
   - Consider vLLM for production deployments

### Log Files
Log files are automatically created in the `logs/` directory with timestamps for troubleshooting.

## License

This project is developed for BIM data processing and graph analysis purposes.

## Author

Taewook Kang (laputa99999@gmail.com)
