# Azure Terraform MCP Server

A Model Context Protocol (MCP) server for Azure Terraform operations, providing intelligent assistance for infrastructure as code development with Azure resources.

## Overview

This MCP server provides support for Azure Terraform development, including:
- Azure provider documentation retrieval (AzureRM and AzAPI)
- HCL code validation
- Security scanning and compliance checking
- Best practices guidance
- Resource analysis and recommendations

## Features

## Features

### 🔍 Documentation & Discovery
- **Azure Provider Docs**: Comprehensive documentation retrieval for AzureRM resources
- **AzAPI Schema**: Schema lookup for Azure API resources
- **Resource Documentation**: Detailed arguments, attributes, and examples

### 🛡️ Security & Compliance
- **Security Scanning**: Built-in security rule validation for Azure resources
- **Best Practices**: Azure-specific best practices and recommendations

### 🔧 Development Tools
- **HCL Validation**: Syntax validation and error reporting for Terraform code
- **Resource Analysis**: Analyze Azure resources in Terraform configurations

### 🚀 Integration
- **MCP Protocol**: Full Model Context Protocol compliance for AI assistant integration
- **FastMCP Framework**: Built on FastMCP for high-performance async operations

## Installation

### Prerequisites
- Python 3.11 or higher
- [UV](https://docs.astral.sh/uv/) (recommended) or pip

### Quick Start with UV (Recommended)

1. **Install UV** (if not already installed):
   ```bash
   # On Windows
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # On macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd tf-mcp-server
   
   # Install dependencies and create virtual environment
   uv sync
   
   # Run the server
   uv run tf-mcp-server
   ```

3. **Development Setup**:
   ```bash
   # Install with development dependencies
   uv sync --dev
   
   # Run tests
   uv run pytest
   
   # Format code
   uv run black .
   
   # Run linting
   uv run flake8
   ```

### Alternative: Traditional pip Installation

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd tf-mcp-server
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install the package
   pip install -e .
   ```

## Configuration

### Environment Variables
```bash
# Server configuration
export MCP_HOST=localhost          # Default: localhost
export MCP_PORT=6801              # Default: 6801
export MCP_DEBUG=false            # Default: false
```

### Configuration File (.env.local)
Create a `.env.local` file in the project root for local configuration:
```bash
MCP_HOST=localhost
MCP_PORT=6801
MCP_DEBUG=false
```

## Usage

### Starting the Server

```bash
# Using the package entry point
python -m src

# Using the main script
python main.py
```

The server will start on `http://localhost:6801` by default.

### Available Tools

The server provides the following MCP tools:

#### Documentation Tools
- **`azurerm_terraform_documentation_retriever`**: Retrieve specific AzureRM resource documentation
- **`azurerm_datasource_documentation_retriever`**: Retrieve specific AzureRM data source documentation
- **`azapi_terraform_documentation_retriever`**: Retrieve AzAPI resource schemas and documentation
- **`search_azurerm_provider_docs`**: Search Azure provider documentation for both resources and data sources with optional filtering

#### Validation Tools
- **`terraform_hcl_code_validator`**: Validate HCL code syntax and structure

#### Security Tools
- **`run_azure_security_scan`**: Run security scans on Terraform configurations

#### Best Practices Tools
- **`get_azure_best_practices`**: Get Azure-specific best practices by resource type and category

#### Analysis Tools
- **`analyze_azure_resources`**: Analyze Azure resources in Terraform configurations

### Example Usage

#### Validate HCL Code
```python
# Using the MCP tool
{
  "tool": "terraform_hcl_code_validator",
  "arguments": {
    "hcl_content": "resource \"azurerm_storage_account\" \"example\" {\n  name = \"mystorageaccount\"\n  resource_group_name = \"myresourcegroup\"\n  location = \"East US\"\n  account_tier = \"Standard\"\n  account_replication_type = \"LRS\"\n}"
  }
}
```

#### Get Documentation
```python
# Using the MCP tool
{
  "tool": "search_azurerm_provider_docs",
  "arguments": {
    "resource_type": "storage_account",
    "search_query": "encryption"
  }
}
```

#### Get Data Source Documentation
```python
# Using the MCP tool for data sources
{
  "tool": "search_azurerm_provider_docs",
  "arguments": {
    "resource_type": "virtual_machine",
    "doc_type": "data-source"
  }
}

# Or use the dedicated data source tool
{
  "tool": "azurerm_datasource_documentation_retriever",
  "arguments": {
    "resource_type_name": "virtual_machine"
  }
}
```

#### Get Best Practices
```python
# Using the MCP tool
{
  "tool": "get_azure_best_practices",
  "arguments": {
    "resource_type": "storage_account",
    "category": "security"
  }
}
```

## Project Structure

```
tf-mcp-server/
├── src/                        # Main package
│   ├── __init__.py
│   ├── __main__.py             # Package entry point
│   ├── core/                   # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration management
│   │   ├── models.py           # Data models
│   │   ├── server.py           # FastMCP server implementation
│   │   ├── terraform_executor.py    # Terraform execution utilities
│   │   └── utils.py            # Utility functions
│   └── tools/                  # Tool implementations
│       ├── __init__.py
│       ├── best_practices.py   # Best practices provider
│       ├── documentation.py    # Documentation tools
│       └── validation.py       # Validation tools
├── data/                       # Data files
│   └── azapi_schemas.json      # AzAPI schemas
├── tests/                      # Test suite
├── tfsample/                   # Sample Terraform files
├── main.py                     # Main entry point
├── pyproject.toml              # Project configuration
├── requirements.txt            # Dependencies
├── requirements-dev.txt        # Development dependencies
└── README.md                   # This file
```

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd tf-mcp-server

# Install development dependencies
pip install -r requirements-dev.txt

# Install in development mode
pip install -e .

# Run tests
pytest tests/

# Run with debug logging
export MCP_DEBUG=true
python -m src
```

### Adding New Tools

To add new MCP tools, extend the server in `src/core/server.py`:

```python
@mcp.tool("your_new_tool")
async def your_new_tool(
    param: str = Field(..., description="Parameter description")
) -> Dict[str, Any]:
    """Tool description."""
    # Implementation
    return {"result": "success"}
```

### Running Tests

```bash
# Run tests (if available)
pytest tests/

# Run with coverage (if pytest-cov is installed)
pytest --cov=src tests/

# Run specific test file
pytest tests/test_utils.py
```

## Security Scanning

The server includes security scanning capabilities with built-in Azure security rules for common misconfigurations and security issues.

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Make sure dependencies are installed
   pip install -r requirements.txt
   ```

2. **Port Conflicts**
   ```bash
   # Change port via environment variable
   export MCP_PORT=6802
   python main.py
   ```

3. **Missing Dependencies**
   ```bash
   # Install optional dependencies
   pip install beautifulsoup4
   ```

### Debug Mode

Enable debug logging:
```bash
export MCP_DEBUG=true
python main.py
```

Check logs in `tf-mcp-server.log` for detailed information.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite: `pytest`
5. Format code: `black src/ tests/`
6. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section above
- Review existing documentation and tests

## Related Projects

- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [Azure Terraform Provider](https://github.com/hashicorp/terraform-provider-azurerm)
- [AzAPI Provider](https://github.com/Azure/terraform-provider-azapi)
- [Model Context Protocol](https://modelcontextprotocol.io)
