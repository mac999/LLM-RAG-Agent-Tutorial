# IFC to Neo4j Graph Converter

BIM Graph Data Importer - A CLI application that converts IFC (Industry Foundation Classes) files to Neo4j graph database format.

## Features

- **Automatic Processing**: Automatically processes all IFC files in the specified input directory
- **Data Integrity**: Accurately converts IFC elements and relationships to graph data model without loss or distortion
- **File Metadata**: Stores IFC file information (filename, creation date, etc.) and links it with the IFC graph structure
- **Reliability**: Stable handling of exception cases (file errors, DB connection failures, etc.) with minimal memory issues for large IFC files
- **Modularity**: Designed with modular structure for easy integration with other BIM data processing pipelines

## Requirements

- Python 3.9 or higher
- Neo4j database (running locally or remotely)
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone or download this project
2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables in `.env` file:
   ```
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   NEO4J_DATABASE=elements
   ```

## Usage

### Basic Usage
```bash
python import_ifc.py
```

### Command Line Options
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

### Examples

Convert all IFC files in the input directory:
```bash
python import_ifc.py --input-dir ./input --stats
```

Clear database and convert with debug logging:
```bash
python import_ifc.py --clear-db --log-level DEBUG --validate
```

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
├── test_basic.py              # Basic functionality tests
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

### Log Files
Log files are automatically created in the `logs/` directory with timestamps for troubleshooting.

## Development

### Adding New IFC Element Types
Modify the `IFCParser.extract_elements()` method to handle additional IFC types.

### Extending Graph Relationships
Add new relationship types in the `Neo4jDatabase._create_relationship_tx()` method.

### Custom Property Extraction
Enhance the `IFCParser._extract_properties()` method for specific PropertySet handling.

## License

This project is developed for BIM data processing and graph analysis purposes.

## Version History

- **v1.0.0**: Initial release with basic IFC to Neo4j conversion
  - File metadata storage and linking
  - Comprehensive error handling
  - Multi-language support (English interface)
  - Modular architecture

## Author
Taewook Kang (laputa99999@gmail.com)