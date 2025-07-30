"""
Main server implementation for Azure Terraform MCP Server.
"""

import asyncio
import logging
from typing import Dict, Any
from pydantic import Field
from fastmcp import FastMCP

from core.config import Config
from core.models import (
    TerraformAzureProviderDocsResult,
    SecurityScanResult
)
from tools.documentation import get_documentation_provider
from tools.validation import get_hcl_validator, get_security_validator
from tools.best_practices import get_best_practices_provider

logger = logging.getLogger(__name__)


def create_server(config: Config) -> FastMCP:
    """
    Create and configure the FastMCP server.
    
    Args:
        config: Server configuration
        
    Returns:
        Configured FastMCP server instance
    """
    mcp = FastMCP("Azure Terraform MCP Server", version="0.1.0")
    
    # Get service instances
    doc_provider = get_documentation_provider()
    hcl_validator = get_hcl_validator()
    security_validator = get_security_validator()
    best_practices = get_best_practices_provider()
    
    # ==========================================
    # DOCUMENTATION TOOLS
    # ==========================================
    
    @mcp.tool("azurerm_terraform_documentation_retriever")
    async def retrieve_azurerm_docs(resource_type_name: str) -> str:
        """
        Retrieve documentation for a specific AzureRM resource type in Terraform.
        
        Args:
            resource_type_name: The name of the AzureRM resource type
            
        Returns:
            The documentation for the specified AzureRM resource type
        """
        try:
            result = await doc_provider.search_azurerm_provider_docs(resource_type_name)
            
            # Format the response
            formatted_doc = f"# {result.resource_type} Documentation\n\n"
            formatted_doc += f"**Summary:** {result.summary}\n\n"
            formatted_doc += f"**Documentation URL:** {result.documentation_url}\n\n"
            
            if result.arguments:
                formatted_doc += "## Arguments\n\n"
                for arg in result.arguments:
                    required = " (Required)" if arg.get("required") == "true" else ""
                    formatted_doc += f"- **{arg['name']}**{required}: {arg['description']}\n"
                formatted_doc += "\n"
            
            if result.attributes:
                formatted_doc += "## Attributes\n\n"
                for attr in result.attributes:
                    formatted_doc += f"- **{attr['name']}**: {attr['description']}\n"
                formatted_doc += "\n"
            
            if result.examples:
                formatted_doc += "## Examples\n\n"
                for i, example in enumerate(result.examples, 1):
                    formatted_doc += f"### Example {i}\n\n```hcl\n{example}\n```\n\n"
            
            return formatted_doc
            
        except Exception as e:
            logger.error(f"Error retrieving AzureRM documentation: {e}")
            return f"Error retrieving documentation for {resource_type_name}: {str(e)}"
    
    @mcp.tool("azapi_terraform_documentation_retriever") 
    async def retrieve_azapi_docs(resource_type_name: str) -> str:
        """
        Retrieve documentation for a specific AzAPI resource type in Terraform.
        
        Args:
            resource_type_name: The name of the AzAPI resource type
            
        Returns:
            The documentation for the specified AzAPI resource type
        """
        try:
            result = await doc_provider.search_azapi_provider_docs(resource_type_name)
            
            # Format the response
            if "error" in result:
                return f"Error: {result['error']}"
            
            formatted_doc = f"# AzAPI {result['resource_type']} Documentation\n\n"
            formatted_doc += f"**Resource Type:** {result['resource_type']}\n"
            formatted_doc += f"**API Version:** {result['api_version']}\n"
            formatted_doc += f"**Source:** {result['source']}\n\n"
            
            if 'summary' in result:
                formatted_doc += f"**Summary:** {result['summary']}\n\n"
            
            if 'documentation_url' in result:
                formatted_doc += f"**Documentation URL:** {result['documentation_url']}\n\n"
            
            if 'schema' in result:
                formatted_doc += "## Schema Information\n\n"
                schema = result['schema']
                if isinstance(schema, dict):
                    for key, value in schema.items():
                        formatted_doc += f"- **{key}**: {value}\n"
                else:
                    formatted_doc += f"{schema}\n"
            
            return formatted_doc
            
        except Exception as e:
            logger.error(f"Error retrieving AzAPI documentation: {e}")
            return f"Error retrieving AzAPI documentation for {resource_type_name}: {str(e)}"
    
    @mcp.tool("search_azurerm_provider_docs")
    async def search_azurerm_provider_docs(
        resource_type: str = Field(..., description="Azure resource type (e.g., 'virtual_machine', 'storage_account')"),
        search_query: str = Field("", description="Specific search query within the resource documentation")
    ) -> TerraformAzureProviderDocsResult:
        """
        Search and retrieve comprehensive Azure provider documentation for Terraform resources.
        
        Args:
            resource_type: The Azure resource type to search for
            search_query: Optional specific query to search within the documentation
            
        Returns:
            Comprehensive documentation result including arguments, attributes, and examples
        """
        return await doc_provider.search_azurerm_provider_docs(resource_type, search_query)
    
    # ==========================================
    # VALIDATION TOOLS
    # ==========================================
    
    @mcp.tool("terraform_hcl_code_validator")
    async def validate_hcl_code(hcl_content: str) -> str:
        """
        Validate HCL (HashiCorp Configuration Language) code and return validation errors if any.
        
        Args:
            hcl_content: The HCL code content to validate. Can contain code blocks with ```hcl markers.
            
        Returns:
            Validation result - either "Valid HCL code" or detailed error messages.
        """
        return await hcl_validator.validate_hcl_code(hcl_content)
    
    @mcp.tool("run_azure_security_scan")
    async def run_security_scan(hcl_content: str) -> SecurityScanResult:
        """
        Run security scanning on Azure Terraform configurations.
        
        Args:
            hcl_content: Terraform HCL content to scan for security issues
            
        Returns:
            Security scan results with findings and recommendations
        """
        return security_validator.validate_security(hcl_content)
    
    # ==========================================
    # BEST PRACTICES TOOLS
    # ==========================================
    
    @mcp.tool("get_azure_best_practices")
    async def get_azure_best_practices(
        resource_type: str = Field(..., description="Azure resource type to get best practices for"),
        category: str = Field("all", description="Category: 'security', 'performance', 'cost', 'reliability', 'all'")
    ) -> str:
        """
        Get Azure best practices for specific resource types and categories.
        
        Args:
            resource_type: Azure resource type to get best practices for
            category: Category of best practices to retrieve
            
        Returns:
            Formatted best practices guidance
        """
        return best_practices.get_best_practices(resource_type, category)
    
    # ==========================================
    # UTILITY TOOLS
    # ==========================================
    
    @mcp.tool("analyze_azure_resources")
    async def analyze_azure_resources(hcl_content: str) -> Dict[str, Any]:
        """
        Analyze Azure resources in Terraform configurations.
        
        Args:
            hcl_content: Terraform HCL content to analyze
            
        Returns:
            Analysis results with resource information and recommendations
        """
        try:
            # This is a simplified analysis - in a real implementation,
            # you would parse the HCL and extract detailed resource information
            
            resources_found = []
            lines = hcl_content.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('resource ') and 'azurerm_' in line:
                    # Extract resource type and name
                    parts = line.split('"')
                    if len(parts) >= 4:
                        resource_type = parts[1]
                        resource_name = parts[3]
                        resources_found.append({
                            "type": resource_type,
                            "name": resource_name
                        })
            
            return {
                "total_resources": len(resources_found),
                "azure_resources": resources_found,
                "analysis_summary": f"Found {len(resources_found)} Azure resources in the configuration",
                "recommendations": [
                    "Review security configurations for all resources",
                    "Ensure proper tagging strategy is implemented",
                    "Validate resource naming conventions",
                    "Check for best practices compliance"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error analyzing Azure resources: {e}")
            return {
                "error": f"Failed to analyze resources: {str(e)}",
                "total_resources": 0,
                "azure_resources": [],
                "analysis_summary": "Analysis failed",
                "recommendations": []
            }
    
    return mcp


async def run_server(config: Config) -> None:
    """
    Run the MCP server.
    
    Args:
        config: Server configuration
    """
    server = create_server(config)
    
    logger.info(f"Starting Azure Terraform MCP Server on {config.server.host}:{config.server.port}")
    
    try:
        await server.run_async(
            transport="http",
            host=config.server.host,
            port=config.server.port
        )
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
