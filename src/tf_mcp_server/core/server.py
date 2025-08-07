"""
Main server implementation for Azure Terraform MCP Server.
"""

import logging
from typing import Dict, Any
from pydantic import Field
from fastmcp import FastMCP

from .config import Config
from .models import SecurityScanResult
from ..tools.azurerm_docs_provider import get_azurerm_documentation_provider
from ..tools.azapi_docs_provider import get_azapi_documentation_provider
from ..tools.terraform_runner import get_terraform_runner
from ..tools.security_rules import get_azure_security_validator
from ..tools.best_practices import get_best_practices_provider

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
    azurerm_doc_provider = get_azurerm_documentation_provider()
    azapi_doc_provider = get_azapi_documentation_provider()
    terraform_runner = get_terraform_runner()
    security_validator = get_azure_security_validator()
    best_practices = get_best_practices_provider()
    
    # ==========================================
    # DOCUMENTATION TOOLS
    # ==========================================
    
    @mcp.tool("azurerm_terraform_documentation_retriever")
    async def retrieve_azurerm_docs(
        resource_type_name: str,
        doc_type: str = Field("resource", description="Type of documentation: 'resource' for resources or 'data-source' for data sources"),
        argument_name: str = Field("", description="Specific argument name to retrieve details for (optional)"),
        attribute_name: str = Field("", description="Specific attribute name to retrieve details for (optional)")
    ) -> Dict[str, Any]:
        """
        Retrieve documentation for a specific AzureRM resource type in Terraform.
        
        Args:
            resource_type_name: The name of the AzureRM resource type
            doc_type: Type of documentation to retrieve ('resource' or 'data-source')
            argument_name: Optional specific argument name to get details for
            attribute_name: Optional specific attribute name to get details for
            
        Returns:
            JSON object with the documentation for the specified AzureRM resource type, or specific argument/attribute details
        """
        try:
            result = await azurerm_doc_provider.search_azurerm_provider_docs(resource_type_name, "", doc_type)
            
            # If specific argument requested
            if argument_name:
                for arg in result.arguments:
                    if arg.name.lower() == argument_name.lower():
                        response_data = {
                            "type": "argument",
                            "name": arg.name,
                            "resource_type": result.resource_type,
                            "required": arg.required,
                            "description": arg.description
                        }
                        
                        if arg.block_arguments:
                            response_data["block_arguments"] = [
                                {
                                    "name": block_arg.name,
                                    "required": block_arg.required,
                                    "description": block_arg.description
                                }
                                for block_arg in arg.block_arguments
                            ]
                        
                        return response_data
                
                available_args = [arg.name for arg in result.arguments]
                return {
                    "error": f"Argument '{argument_name}' not found in {result.resource_type} documentation",
                    "resource_type": result.resource_type,
                    "available_arguments": available_args
                }
            
            # If specific attribute requested
            if attribute_name:
                for attr in result.attributes:
                    if attr['name'].lower() == attribute_name.lower():
                        return {
                            "type": "attribute",
                            "name": attr['name'],
                            "resource_type": result.resource_type,
                            "description": attr['description']
                        }
                
                available_attrs = [attr['name'] for attr in result.attributes]
                return {
                    "error": f"Attribute '{attribute_name}' not found in {result.resource_type} documentation",
                    "resource_type": result.resource_type,
                    "available_attributes": available_attrs
                }
            
            # Return full documentation as JSON
            doc_type_display = "Data Source" if doc_type.lower() in ["data-source", "datasource", "data_source"] else "Resource"
            
            response_data = {
                "resource_type": result.resource_type,
                "doc_type": doc_type_display,
                "summary": result.summary,
                "documentation_url": result.documentation_url,
                "arguments": [],
                "attributes": [],
                "examples": result.examples if result.examples else [],
                "notes": result.notes if result.notes else []
            }
            
            # Add arguments
            if result.arguments:
                for arg in result.arguments:
                    arg_data = {
                        "name": arg.name,
                        "required": arg.required,
                        "description": arg.description
                    }
                    
                    if arg.block_arguments:
                        arg_data["block_arguments"] = [
                            {
                                "name": block_arg.name,
                                "required": block_arg.required,
                                "description": block_arg.description
                            }
                            for block_arg in arg.block_arguments
                        ]
                    
                    response_data["arguments"].append(arg_data)
            
            # Add attributes
            if result.attributes:
                response_data["attributes"] = [
                    {
                        "name": attr['name'],
                        "description": attr['description']
                    }
                    for attr in result.attributes
                ]
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error retrieving AzureRM documentation: {e}")
            return {
                "error": f"Error retrieving documentation for {resource_type_name}: {str(e)}",
                "resource_type": resource_type_name
            }
    
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
            result = await azapi_doc_provider.search_azapi_provider_docs(resource_type_name)
            
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
    

    
    # ==========================================
    # TERRAFORM COMMAND TOOLS
    # ==========================================
    
    @mcp.tool("run_terraform_command")
    async def run_terraform_command(
        command: str = Field(..., description="Terraform command to execute (init, plan, apply, destroy, validate, fmt)"),
        hcl_content: str = Field(..., description="HCL content to execute the command against"),
        var_file_content: str = Field("", description="Optional Terraform variables content (terraform.tfvars format)"),
        auto_approve: bool = Field(False, description="Auto-approve for apply/destroy commands (USE WITH CAUTION!)"),
        upgrade: bool = Field(False, description="Upgrade providers/modules for init command")
    ) -> Dict[str, Any]:
        """
        Execute any Terraform command with provided HCL content.
        
        This unified tool replaces individual terraform_init, terraform_plan, terraform_apply, 
        terraform_destroy, terraform_format, and terraform_execute_command tools.
        
        Args:
            command: Terraform command to execute:
                - 'init': Initialize Terraform working directory
                - 'plan': Show execution plan for changes
                - 'apply': Apply changes to create/update resources
                - 'destroy': Destroy Terraform-managed resources
                - 'validate': Validate configuration files
                - 'fmt': Format configuration files
            hcl_content: HCL content to execute the command against
            var_file_content: Optional Terraform variables content
            auto_approve: Auto-approve for destructive operations (apply/destroy)
            upgrade: Upgrade providers/modules during init
            
        Returns:
            Command execution result with details based on command type:
            - For 'fmt': Returns formatted HCL content as string
            - For others: Returns Dict with exit_code, stdout, stderr, and command-specific data
        """
        vars_content = var_file_content if var_file_content.strip() else None
        
        # Handle format command separately as it returns formatted content
        if command == 'fmt':
            formatted_content = await terraform_runner.format_hcl_code(hcl_content)
            return {
                "command": "fmt",
                "success": True,
                "formatted_content": formatted_content,
                "exit_code": 0,
                "stdout": "Successfully formatted HCL content",
                "stderr": ""
            }
        
        # Handle other commands using the unified execution method
        kwargs = {}
        if command in ['apply', 'destroy'] and auto_approve:
            kwargs['auto_approve'] = auto_approve
        elif command == 'init' and upgrade:
            kwargs['upgrade'] = upgrade
        
        try:
            # Use the existing execute_terraform_command method
            result = await terraform_runner.execute_terraform_command(command, hcl_content, vars_content, **kwargs)
            
            # Ensure result is a dictionary
            if isinstance(result, str):
                # If the validator returns a string, wrap it in a proper response
                return {
                    "command": command,
                    "success": True,
                    "output": result,
                    "exit_code": 0,
                    "stdout": result,
                    "stderr": ""
                }
            elif isinstance(result, dict):
                # Add command info to the result
                result["command"] = command
                return result
            else:
                # Fallback for unexpected return types
                return {
                    "command": command,
                    "success": False,
                    "output": str(result),
                    "exit_code": 1,
                    "stdout": "",
                    "stderr": f"Unexpected result type: {type(result)}"
                }
                
        except Exception as e:
            return {
                "command": command,
                "success": False,
                "error": str(e),
                "exit_code": 1,
                "stdout": "",
                "stderr": str(e)
            }
    
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
