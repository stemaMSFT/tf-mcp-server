"""
Azure provider documentation tools for Azure Terraform MCP Server.
"""

import re
from typing import Dict, Any, List, Union, TYPE_CHECKING
from httpx import AsyncClient

# Try to import BeautifulSoup
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    BeautifulSoup = None

from core.models import TerraformAzureProviderDocsResult
from core.config import load_azapi_schema
from core.utils import normalize_resource_type


class AzureDocumentationProvider:
    """Provider for Azure Terraform documentation."""
    
    def __init__(self):
        """Initialize the documentation provider."""
        self.azapi_schema = load_azapi_schema()
        self.base_url = "https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources"
    
    async def search_azurerm_provider_docs(
        self, 
        resource_type: str, 
        search_query: str = ""
    ) -> TerraformAzureProviderDocsResult:
        """
        Search and retrieve comprehensive Azure provider documentation.
        
        Args:
            resource_type: Azure resource type to search for
            search_query: Optional specific query within the documentation
            
        Returns:
            Comprehensive documentation result
        """
        try:
            # Normalize resource type
            normalized_type = normalize_resource_type(resource_type)
            
            # Generate documentation URL
            doc_url = f"{self.base_url}/{normalized_type}"
            
            # Fetch documentation
            async with AsyncClient(timeout=30.0) as client:
                response = await client.get(doc_url)
                
                if response.status_code != 200:
                    return TerraformAzureProviderDocsResult(
                        resource_type=resource_type,
                        documentation_url=doc_url,
                        summary=f"Documentation not found for {resource_type} (HTTP {response.status_code})",
                        arguments=[],
                        attributes=[],
                        examples=[]
                    )
                
                # Parse the HTML content
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract information from the documentation page
                summary = self._extract_summary(soup, resource_type)
                arguments = self._extract_arguments(soup)
                attributes = self._extract_attributes(soup)
                examples = self._extract_examples(soup, normalized_type)
                
                return TerraformAzureProviderDocsResult(
                    resource_type=resource_type,
                    documentation_url=doc_url,
                    summary=summary,
                    arguments=arguments,
                    attributes=attributes,
                    examples=examples
                )
                
        except Exception as e:
            return TerraformAzureProviderDocsResult(
                resource_type=resource_type,
                documentation_url="",
                summary=f"Error retrieving documentation: {str(e)}",
                arguments=[],
                attributes=[],
                examples=[]
            )
    
    async def search_azapi_provider_docs(
        self, 
        resource_type: str, 
        api_version: str = ""
    ) -> Dict[str, Any]:
        """
        Search Azure API provider documentation and schemas.
        
        Args:
            resource_type: Azure API resource type
            api_version: Optional specific API version
            
        Returns:
            Dictionary containing AzAPI documentation and schema information
        """
        try:
            # Search in loaded schema
            schema_info = self._search_azapi_schema(resource_type, api_version)
            
            if schema_info:
                return {
                    "resource_type": resource_type,
                    "api_version": api_version or "latest",
                    "schema": schema_info,
                    "source": "azapi_schemas.json"
                }
            
            # If not found in local schema, try to fetch from Azure docs
            return await self._fetch_azapi_docs_online(resource_type, api_version)
            
        except Exception as e:
            return {
                "error": f"Error searching AzAPI documentation: {str(e)}",
                "resource_type": resource_type,
                "api_version": api_version
            }
    
    def _extract_summary(self, soup: Any, resource_type: str) -> str:
        """Extract summary from the documentation page."""
        # Try to find the description paragraph
        description_elem = soup.find('p')
        if description_elem:
            return description_elem.get_text().strip()
        
        return f"Manages an Azure {resource_type.replace('_', ' ').title()} resource."
    
    def _extract_arguments(self, soup: Any) -> List[Dict[str, str]]:
        """Extract argument information from the documentation."""
        arguments = []
        
        # Common Azure resource arguments
        common_args = [
            {
                "name": "name",
                "description": "Specifies the name of the resource.",
                "required": "true",
                "type": "string"
            },
            {
                "name": "resource_group_name",
                "description": "The name of the resource group in which to create the resource.",
                "required": "true",
                "type": "string"
            },
            {
                "name": "location",
                "description": "Specifies the supported Azure location where the resource exists.",
                "required": "true",
                "type": "string"
            },
            {
                "name": "tags",
                "description": "A mapping of tags to assign to the resource.",
                "required": "false",
                "type": "map(string)"
            }
        ]
        
        arguments.extend(common_args)
        
        # Try to extract specific arguments from the page
        if HAS_BS4:
            args_section = soup.find('h2', string=re.compile('Arguments? Reference', re.IGNORECASE))
            if args_section:
                # Find the next ul or table after the arguments header
                next_elem = args_section.find_next_sibling(['ul', 'table', 'div'])
                if next_elem:
                    items = next_elem.find_all('li') if next_elem.name == 'ul' else next_elem.find_all('tr')
                    
                    for item in items[:10]:  # Limit to first 10 items
                        text = item.get_text().strip()
                        if ' - ' in text:
                            parts = text.split(' - ', 1)
                            arg_name = parts[0].strip('`').strip()
                            description = parts[1].strip() if len(parts) > 1 else ""
                            
                            # Skip if already in common args
                            if not any(arg['name'] == arg_name for arg in arguments):
                                arguments.append({
                                    "name": arg_name,
                                    "description": description,
                                    "required": "Required" in description,
                                    "type": "string"  # Default type
                                })
        
        return arguments
    
    def _extract_attributes(self, soup: Any) -> List[Dict[str, str]]:
        """Extract attribute information from the documentation."""
        attributes = [
            {
                "name": "id",
                "description": "The ID of the resource."
            }
        ]
        
        # Try to extract specific attributes from the page
        if HAS_BS4:
            attrs_section = soup.find('h2', string=re.compile('Attributes? Reference', re.IGNORECASE))
            if attrs_section:
                next_elem = attrs_section.find_next_sibling(['ul', 'table', 'div'])
                if next_elem:
                    items = next_elem.find_all('li') if next_elem.name == 'ul' else next_elem.find_all('tr')
                    
                    for item in items[:10]:  # Limit to first 10 items
                        text = item.get_text().strip()
                        if ' - ' in text:
                            parts = text.split(' - ', 1)
                            attr_name = parts[0].strip('`').strip()
                            description = parts[1].strip() if len(parts) > 1 else ""
                            
                            # Skip if already exists
                            if not any(attr['name'] == attr_name for attr in attributes):
                                attributes.append({
                                    "name": attr_name,
                                    "description": description
                                })
        
        return attributes
    
    def _extract_examples(self, soup: Any, normalized_type: str) -> List[str]:
        """Extract example code from the documentation."""
        examples = []
        
        # Find code blocks
        if HAS_BS4:
            code_blocks = soup.find_all('code', class_='language-hcl') or soup.find_all('pre')
            
            for block in code_blocks[:3]:  # Limit to first 3 examples
                code_text = block.get_text().strip()
                if 'resource' in code_text and normalized_type.replace('-', '_') in code_text:
                    examples.append(code_text)
        
        # If no examples found, generate a basic one
        if not examples:
            resource_name = normalized_type.replace('-', '_')
            examples.append(f'''resource "azurerm_{resource_name}" "example" {{
  name                = "example-{normalized_type}"
  resource_group_name = azurerm_resource_group.example.name
  location            = azurerm_resource_group.example.location

  tags = {{
    Environment = "Development"
  }}
}}''')
        
        return examples
    
    def _search_azapi_schema(self, resource_type: str, api_version: str = "") -> Dict[str, Any]:
        """Search in the loaded AzAPI schema."""
        if not self.azapi_schema:
            return {}
        
        # Normalize the resource type for searching
        search_type = resource_type.lower()
        
        # Search through the schema
        for key, value in self.azapi_schema.items():
            if search_type in key.lower():
                return {
                    "definition": value,
                    "schema_key": key
                }
        
        return {}
    
    async def _fetch_azapi_docs_online(self, resource_type: str, api_version: str) -> Dict[str, Any]:
        """Fetch AzAPI documentation from online sources."""
        try:
            # Try Azure REST API documentation
            azure_docs_url = f"https://docs.microsoft.com/en-us/rest/api/{resource_type.lower()}"
            
            async with AsyncClient(timeout=30.0) as client:
                response = await client.get(azure_docs_url)
                
                if response.status_code == 200:
                    return {
                        "resource_type": resource_type,
                        "api_version": api_version or "latest",
                        "documentation_url": azure_docs_url,
                        "source": "Azure REST API docs",
                        "summary": f"Azure REST API documentation for {resource_type}"
                    }
        
        except Exception as e:
            pass  # Continue to fallback
        
        # Fallback response
        return {
            "resource_type": resource_type,
            "api_version": api_version or "latest",
            "summary": f"AzAPI resource type: {resource_type}",
            "documentation_url": "https://registry.terraform.io/providers/Azure/azapi/latest/docs",
            "source": "fallback"
        }


# Global instance
_doc_provider = None


def get_documentation_provider() -> AzureDocumentationProvider:
    """Get the global documentation provider instance."""
    global _doc_provider
    if _doc_provider is None:
        _doc_provider = AzureDocumentationProvider()
    return _doc_provider
