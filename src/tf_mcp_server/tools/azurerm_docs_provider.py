"""
AzureRM provider documentation tools for Azure Terraform MCP Server.
"""

import re
from typing import Dict, Any, List, Optional, Union
from httpx import AsyncClient
from pydantic import BaseModel, Field

from ..core.models import ArgumentDetail, TerraformAzureProviderDocsResult

class AzureRMDocumentationProvider:
    """Provider for AzureRM Terraform documentation."""
    
    def __init__(self):
        """Initialize the AzureRM documentation provider."""
        self.base_resources_url = "https://raw.githubusercontent.com/hashicorp/terraform-provider-azurerm/main/website/docs/r"
        self.base_datasources_url = "https://raw.githubusercontent.com/hashicorp/terraform-provider-azurerm/main/website/docs/d"
    
    async def search_azurerm_provider_docs(
        self, 
        resource_type: str, 
        search_query: str = "",
        doc_type: str = "resource"
    ) -> TerraformAzureProviderDocsResult:
        """
        Search and retrieve comprehensive AzureRM provider documentation.
        
        Args:
            resource_type: Azure resource type to search for
            search_query: Optional specific query within the documentation
            doc_type: Type of documentation to search ("resource" or "data-source")
            
        Returns:
            Comprehensive documentation result
        """
        try:
            # Normalize resource type for GitHub markdown files (keep underscores)
            # Remove azurerm_ prefix if present
            normalized_type = resource_type.lower().replace('azurerm_', '')
            
            # Generate documentation URL based on type
            if doc_type.lower() in ["data-source", "datasource", "data_source"]:
                doc_url = f"{self.base_datasources_url}/{normalized_type}.html.markdown"
            else:
                doc_url = f"{self.base_resources_url}/{normalized_type}.html.markdown"
            
            # Fetch documentation
            async with AsyncClient(timeout=30.0) as client:
                response = await client.get(doc_url)
                
                if response.status_code != 200:
                    # If resource not found, try the other type
                    if doc_type.lower() in ["data-source", "datasource", "data_source"]:
                        fallback_url = f"{self.base_resources_url}/{normalized_type}.html.markdown"
                    else:
                        fallback_url = f"{self.base_datasources_url}/{normalized_type}.html.markdown"
                    
                    fallback_response = await client.get(fallback_url)
                    if fallback_response.status_code == 200:
                        response = fallback_response
                        doc_url = fallback_url
                    else:
                        return TerraformAzureProviderDocsResult(
                            resource_type=resource_type,
                            documentation_url=doc_url,
                            summary=f"Documentation not found for {resource_type} (HTTP {response.status_code})",
                            arguments=[],
                            attributes=[],
                            examples=[]
                        )
                
                # Parse the markdown content
                markdown_content = response.text
                
                # Determine if this is a data source or resource based on URL
                is_data_source = "docs/d/" in doc_url
                
                # Extract information from the documentation page
                summary = self._extract_summary(markdown_content, resource_type, is_data_source)
                arguments = self._extract_arguments(markdown_content, is_data_source)
                attributes = self._extract_attributes(markdown_content)
                examples = self._extract_examples(markdown_content, normalized_type, is_data_source)
                
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
    
    def _extract_summary(self, markdown_content: str, resource_type: str, is_data_source: bool = False) -> str:
        """Extract summary from the markdown documentation."""
        lines = markdown_content.split('\n')
        
        # Look for the description after the front matter
        in_frontmatter = False
        frontmatter_ended = False
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Track frontmatter boundaries
            if line == '---':
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    frontmatter_ended = True
                    continue
            
            # Skip frontmatter content
            if in_frontmatter and not frontmatter_ended:
                continue
                
            # Look for description after frontmatter
            if frontmatter_ended and line and not line.startswith('#'):
                # This is likely the description paragraph
                if len(line) > 20:  # Reasonable length for a description
                    return line
            
            # Also look for description under ## Description header
            if line.lower().startswith('## description'):
                # Get the next non-empty line
                for j in range(i + 1, min(i + 5, len(lines))):
                    desc_line = lines[j].strip()
                    if desc_line and not desc_line.startswith('#'):
                        return desc_line
        
        # Fallback to generating appropriate summary
        return self._generate_default_summary(resource_type, is_data_source)
    
    def _generate_default_summary(self, resource_type: str, is_data_source: bool) -> str:
        """Generate a default summary based on resource type and whether it's a data source."""
        resource_display_name = resource_type.replace('_', ' ').title()
        
        if is_data_source:
            return f"Use this data source to access information about an existing {resource_display_name}."
        else:
            return f"Manages an Azure {resource_display_name} resource."
    
    def _extract_arguments(self, markdown_content: str, is_data_source: bool = False) -> List[ArgumentDetail]:
        """Extract argument information from the markdown documentation."""
        arguments = []
        lines = markdown_content.split('\n')
        
        # First pass: Find all main arguments in the Arguments Reference section
        in_arguments_section = False
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Look for Arguments Reference section
            if re.match(r'^##\s+(Arguments?\s+Reference|Argument\s+Reference)', line_stripped, re.IGNORECASE):
                in_arguments_section = True
                continue
            
            # Stop when we hit another major section OR when we hit the first block definition
            # Note: We continue past '---' separators as they're just visual dividers within the arguments
            if (in_arguments_section and 
                ((line_stripped.startswith('## ') and not re.match(r'^##\s+(Arguments?\s+Reference|Argument\s+Reference)', line_stripped, re.IGNORECASE)) or
                 re.match(r'^(?:A|An|The)\s+`[^`]+`\s+block\s+supports\s+the\s+following:', line_stripped, re.IGNORECASE))):
                break
            
            if in_arguments_section and line_stripped:
                # Look for argument definitions (start with * or -)
                arg_match = re.match(r'^[\*\-]\s*`([^`]+)`\s*[-–—]\s*(.+)', line_stripped)
                if arg_match:
                    arg_name = arg_match.group(1).strip()
                    description = arg_match.group(2).strip()
                    
                    # Determine if required
                    required = "(Required)" in description or "(required)" in description
                    
                    # Clean up description by removing required/optional indicators
                    cleaned_description = re.sub(r'\s*\((?:Required|Optional)\)\s*[-–—]?\s*', '', description, flags=re.IGNORECASE).strip()
                    # Remove leading dash if it remains after cleanup
                    cleaned_description = re.sub(r'^[-–—]\s*', '', cleaned_description).strip()
                    
                    # Determine if this is a block argument
                    is_block = "block" in cleaned_description.lower()
                    
                    # Determine type
                    if is_block:
                        arg_type = "Block"
                    else:
                        arg_type = "Single"
                    
                    arg_detail = ArgumentDetail(
                        name=arg_name,
                        description=cleaned_description,
                        required=required,
                        type=arg_type,
                        block_arguments=[] if is_block else None
                    )
                    
                    arguments.append(arg_detail)
        
        # Second pass: Find block definitions and populate nested arguments
        block_definitions = self._extract_block_definitions(markdown_content)
        
        # Match block definitions to arguments
        for arg in arguments:
            if arg.type == "Block" and arg.name in block_definitions:
                arg.block_arguments = block_definitions[arg.name]
                    
        # Add common arguments if none were found
        if not arguments:
            if is_data_source:
                arguments = [
                    ArgumentDetail(
                        name="name",
                        description="Specifies the name of the resource to retrieve information about.",
                        required=False,
                        type="Single"
                    ),
                    ArgumentDetail(
                        name="resource_group_name",
                        description="The name of the resource group containing the resource.",
                        required=False,
                        type="Single"
                    )
                ]
            else:
                arguments = [
                    ArgumentDetail(
                        name="name",
                        description="Specifies the name of the resource.",
                        required=True,
                        type="Single"
                    ),
                    ArgumentDetail(
                        name="resource_group_name",
                        description="The name of the resource group in which to create the resource.",
                        required=True,
                        type="Single"
                    ),
                    ArgumentDetail(
                        name="location",
                        description="Specifies the supported Azure location where the resource exists.",
                        required=True,
                        type="Single"
                    ),
                    ArgumentDetail(
                        name="tags",
                        description="A mapping of tags to assign to the resource.",
                        required=False,
                        type="Single"
                    )
                ]
        
        return arguments
    
    def _extract_block_definitions(self, markdown_content: str) -> Dict[str, List[ArgumentDetail]]:
        """Extract block definitions from the markdown documentation."""
        block_definitions = {}
        lines = markdown_content.split('\n')
        
        current_block_name = None
        current_block_args = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Look for block definition headers
            block_header_match = re.match(r'^(?:A|An|The)\s+`([^`]+)`\s+block\s+supports\s+the\s+following:', line_stripped, re.IGNORECASE)
            if block_header_match:
                # Save previous block if exists
                if current_block_name and current_block_args:
                    block_definitions[current_block_name] = current_block_args
                
                # Start new block
                current_block_name = block_header_match.group(1).strip()
                current_block_args = []
                continue
            
            # Look for end of block (indicated by ---, ## header, or empty line followed by A/An/The block)
            if current_block_name:
                if (line_stripped == '---' or 
                    line_stripped.startswith('## ') or
                    (line_stripped == '' and i + 1 < len(lines) and 
                     re.match(r'^(?:A|An|The)\s+`[^`]+`\s+block\s+supports\s+the\s+following:', lines[i + 1].strip(), re.IGNORECASE))):
                    
                    # Save current block
                    if current_block_args:
                        block_definitions[current_block_name] = current_block_args
                    
                    current_block_name = None
                    current_block_args = []
                    continue
                
                # Look for argument definitions within block
                arg_match = re.match(r'^[\*\-]\s*`([^`]+)`\s*[-–—]\s*(.+)', line_stripped)
                if arg_match:
                    arg_name = arg_match.group(1).strip()
                    description = arg_match.group(2).strip()
                    
                    # Determine if required
                    required = "(Required)" in description or "(required)" in description
                    
                    # Clean up description by removing required/optional indicators
                    cleaned_description = re.sub(r'\s*\((?:Required|Optional)\)\s*[-–—]?\s*', '', description, flags=re.IGNORECASE).strip()
                    # Remove leading dash if it remains after cleanup
                    cleaned_description = re.sub(r'^[-–—]\s*', '', cleaned_description).strip()
                    
                    # Determine if this nested argument is also a block
                    is_nested_block = "block" in cleaned_description.lower()
                    
                    arg_detail = ArgumentDetail(
                        name=arg_name,
                        description=cleaned_description,
                        required=required,
                        type="Block" if is_nested_block else "Single",
                        block_arguments=[] if is_nested_block else None
                    )
                    
                    current_block_args.append(arg_detail)
        
        # Handle the last block if exists
        if current_block_name and current_block_args:
            block_definitions[current_block_name] = current_block_args
        
        return block_definitions
    
    def _extract_attributes(self, markdown_content: str) -> List[Dict[str, str]]:
        """Extract attribute information from the markdown documentation."""
        attributes = [
            {
                "name": "id",
                "description": "The ID of the resource."
            }
        ]
        
        lines = markdown_content.split('\n')
        
        # Find the Attributes Reference section
        in_attributes_section = False
        in_block = False
        current_block = None
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Look for Attributes Reference section
            if re.match(r'^##\s+(Attributes?\s+Reference|Attribute\s+Reference)', line_stripped, re.IGNORECASE):
                in_attributes_section = True
                continue
            
            # Stop when we hit another major section
            if in_attributes_section and line_stripped.startswith('## ') and not re.match(r'^##\s+(Attributes?\s+Reference|Attribute\s+Reference)', line_stripped, re.IGNORECASE):
                break
            
            if in_attributes_section:
                # Look for attribute definitions (usually start with * or -)
                if re.match(r'^[\*\-]\s*`([^`]+)`', line_stripped):
                    match = re.match(r'^[\*\-]\s*`([^`]+)`\s*[-–—]\s*(.+)', line_stripped)
                    if match:
                        attr_name = match.group(1).strip()
                        description = match.group(2).strip()
                        
                        # Skip if already exists
                        if not any(attr['name'] == attr_name for attr in attributes):
                            attributes.append({
                                "name": attr_name,
                                "description": description
                            })
                
                # Look for nested block attributes (indented)
                elif re.match(r'^\s+[\*\-]\s*`([^`]+)`', line_stripped):
                    match = re.match(r'^\s+[\*\-]\s*`([^`]+)`\s*[-–—]\s*(.+)', line_stripped)
                    if match and current_block:
                        nested_attr = match.group(1).strip()
                        nested_desc = match.group(2).strip()
                        
                        # Add as nested attribute with block prefix
                        if not any(attr['name'] == f"{current_block}.{nested_attr}" for attr in attributes):
                            attributes.append({
                                "name": f"{current_block}.{nested_attr}",
                                "description": f"(Block attribute) {nested_desc}"
                            })
                
                # Track current block context - look for block attributes first
                if re.match(r'^[\*\-]\s*`([^`]+)`.*block', line_stripped, re.IGNORECASE):
                    block_match = re.match(r'^[\*\-]\s*`([^`]+)`', line_stripped)
                    if block_match:
                        current_block = block_match.group(1).strip()
        
        # If no attributes were extracted, provide known attributes for common Azure resources
        if len(attributes) == 1:  # Only has the default 'id' attribute
            attributes.extend(self._get_known_attributes())
        
        return attributes
    
    def _get_known_attributes(self) -> List[Dict[str, str]]:
        """Get known attributes for common Azure data sources since the registry uses JS rendering."""
        # Note: This is a fallback for when the HTML parsing fails due to JS-rendered content
        return [
            {
                "name": "location",
                "description": "The Azure location where the Virtual Machine exists."
            },
            {
                "name": "size",
                "description": "The size of the Virtual Machine."
            },
            {
                "name": "admin_username",
                "description": "The admin username of the Virtual Machine."
            },
            {
                "name": "network_interface_ids",
                "description": "A list of the Network Interface IDs which are attached to the Virtual Machine."
            },
            {
                "name": "os_disk",
                "description": "A os_disk block as defined below."
            },
            {
                "name": "storage_data_disk",
                "description": "One or more storage_data_disk blocks as defined below."
            },
            {
                "name": "identity",
                "description": "A identity block as defined below."
            }
        ]
    
    def _extract_examples(self, markdown_content: str, normalized_type: str, is_data_source: bool = False) -> List[str]:
        """Extract example code from the markdown documentation."""
        examples = []
        lines = markdown_content.split('\n')
        
        # Find code blocks (```hcl or ```terraform)
        in_code_block = False
        current_code = []
        code_block_lang = None
        
        for line in lines:
            # Check for code block start
            if line.strip().startswith('```'):
                if not in_code_block:
                    # Starting a code block
                    in_code_block = True
                    code_block_lang = line.strip()[3:].strip().lower()
                    current_code = []
                else:
                    # Ending a code block
                    in_code_block = False
                    
                    # Check if this is a relevant code block
                    if code_block_lang in ['hcl', 'terraform', ''] and current_code:
                        code_text = '\n'.join(current_code).strip()
                        
                        # Check if it contains the resource/data source
                        block_type = "data" if is_data_source else "resource"
                        resource_name = normalized_type.replace('-', '_')
                        
                        if (block_type in code_text and 
                            (f"azurerm_{resource_name}" in code_text or 
                             f'"{resource_name}"' in code_text or
                             resource_name in code_text)):
                            examples.append(code_text)
                            if len(examples) >= 3:  # Limit to 3 examples
                                break
                    
                    current_code = []
                    code_block_lang = None
            elif in_code_block:
                current_code.append(line)
        
        # If no examples found, generate a basic one
        if not examples:
            resource_name = normalized_type.replace('-', '_')
            if is_data_source:
                examples.append(f'''data "azurerm_{resource_name}" "example" {{
  name                = "example-{normalized_type}"
  resource_group_name = "example-resource-group"
}}

# Use the data source
output "{resource_name}_id" {{
  value = data.azurerm_{resource_name}.example.id
}}''')
            else:
                examples.append(f'''resource "azurerm_{resource_name}" "example" {{
  name                = "example-{normalized_type}"
  resource_group_name = azurerm_resource_group.example.name
  location            = azurerm_resource_group.example.location

  tags = {{
    Environment = "Development"
  }}
}}''')
        
        return examples


# Global instance
_azurerm_provider = None


def get_azurerm_documentation_provider() -> AzureRMDocumentationProvider:
    """Get the global AzureRM documentation provider instance."""
    global _azurerm_provider
    if _azurerm_provider is None:
        _azurerm_provider = AzureRMDocumentationProvider()
    return _azurerm_provider
