"""
Azure best practices guidance for Terraform configurations.
"""

from typing import Dict, Any, List, Optional


class AzureBestPracticesProvider:
    """Provider for Azure Terraform best practices."""
    
    def __init__(self):
        """Initialize the best practices provider."""
        self.best_practices_db = self._load_best_practices()
    
    def get_best_practices(self, resource_type: str, category: str = "all") -> str:
        """
        Get Azure best practices for a specific resource type.
        
        Args:
            resource_type: Azure resource type
            category: Category of best practices (security, performance, cost, reliability, all)
            
        Returns:
            Formatted best practices guidance
        """
        # Normalize resource type
        normalized_type = resource_type.lower().replace('azurerm_', '')
        
        # Get best practices for the resource type
        practices = self.best_practices_db.get(f"azurerm_{normalized_type}", {})
        
        if not practices:
            return self._get_generic_best_practices(resource_type, category)
        
        # Filter by category if specified
        if category != "all" and category in practices:
            filtered_practices = {category: practices[category]}
        else:
            filtered_practices = practices
        
        # Format the response
        return self._format_best_practices(resource_type, filtered_practices)
    
    def get_template_with_best_practices(self, resource_type: str) -> str:
        """
        Generate a Terraform template with best practices applied.
        
        Args:
            resource_type: Azure resource type
            
        Returns:
            Terraform template with best practices
        """
        normalized_type = resource_type.lower().replace('azurerm_', '')
        
        # Get template for the resource type
        if f"azurerm_{normalized_type}" in self.best_practices_db:
            return self._generate_template(f"azurerm_{normalized_type}")
        else:
            return self._generate_generic_template(resource_type)
    
    def _load_best_practices(self) -> Dict[str, Dict[str, List[str]]]:
        """Load Azure best practices database."""
        return {
            "azurerm_virtual_machine": {
                "security": [
                    "Enable disk encryption using Azure Disk Encryption",
                    "Use managed identities instead of service principals",
                    "Configure network security groups with least privilege",
                    "Enable boot diagnostics for troubleshooting",
                    "Use Azure Security Center recommendations",
                    "Disable unused network interfaces and ports",
                    "Enable Azure Antimalware extension",
                    "Use strong authentication methods"
                ],
                "performance": [
                    "Choose appropriate VM size based on workload",
                    "Use Premium SSD for production workloads",
                    "Enable accelerated networking when supported",
                    "Configure proper load balancing",
                    "Use proximity placement groups for latency-sensitive apps",
                    "Optimize VM placement with availability sets/zones",
                    "Monitor performance metrics regularly"
                ],
                "cost": [
                    "Use Azure Reserved Instances for predictable workloads",
                    "Implement auto-shutdown for dev/test environments",
                    "Right-size VMs based on actual utilization",
                    "Use spot instances for fault-tolerant workloads",
                    "Monitor and optimize with Azure Cost Management",
                    "Deallocate VMs when not in use",
                    "Use Azure Hybrid Benefit for Windows/SQL licenses"
                ],
                "reliability": [
                    "Deploy across availability zones",
                    "Use availability sets for planned maintenance",
                    "Implement backup and disaster recovery",
                    "Configure health probes and monitoring",
                    "Use infrastructure as code for consistency",
                    "Implement automated failover mechanisms",
                    "Regular testing of disaster recovery procedures"
                ]
            },
            "azurerm_storage_account": {
                "security": [
                    "Enable secure transfer (HTTPS only)",
                    "Use private endpoints for secure connectivity",
                    "Configure firewall rules and virtual network access",
                    "Enable Azure Defender for Storage",
                    "Use customer-managed encryption keys when required",
                    "Enable blob soft delete for data protection",
                    "Configure shared access signature (SAS) policies properly",
                    "Regular audit of access permissions"
                ],
                "performance": [
                    "Choose appropriate performance tier (Standard vs Premium)",
                    "Use hot/cool/archive tiers based on access patterns",
                    "Configure CDN for globally distributed content",
                    "Optimize blob storage with proper container structure",
                    "Use read-access geo-redundant storage for high availability",
                    "Implement connection pooling for applications",
                    "Monitor storage metrics and optimize access patterns"
                ],
                "cost": [
                    "Implement lifecycle management policies",
                    "Use appropriate redundancy level (LRS/ZRS/GRS)",
                    "Monitor storage metrics and optimize usage",
                    "Configure blob tier automation",
                    "Clean up orphaned resources regularly",
                    "Use storage reserved capacity for predictable workloads",
                    "Optimize data transfer costs"
                ],
                "reliability": [
                    "Configure geo-redundant storage for critical data",
                    "Implement backup strategies for important data",
                    "Monitor storage health and availability",
                    "Use multiple storage accounts to avoid limits",
                    "Implement retry logic in applications",
                    "Regular testing of backup and restore procedures",
                    "Monitor for storage account limits and quotas"
                ]
            },
            "azurerm_key_vault": {
                "security": [
                    "Use Azure RBAC for fine-grained access control",
                    "Enable firewall and virtual network rules",
                    "Use private endpoints for network isolation",
                    "Enable soft delete and purge protection",
                    "Rotate keys and secrets regularly",
                    "Use managed identities for application access",
                    "Enable auditing and monitoring",
                    "Implement least privilege access policies"
                ],
                "performance": [
                    "Use appropriate Key Vault tier (Standard vs Premium)",
                    "Implement connection pooling and caching",
                    "Monitor request rates and throttling",
                    "Use bulk operations when possible",
                    "Optimize key and secret retrieval patterns",
                    "Consider regional placement for latency"
                ],
                "cost": [
                    "Monitor Key Vault transaction costs",
                    "Optimize secret and key operations",
                    "Use Standard tier unless HSM is required",
                    "Implement efficient caching strategies",
                    "Regular cleanup of unused secrets and keys"
                ],
                "reliability": [
                    "Enable backup for critical keys and secrets",
                    "Implement disaster recovery procedures",
                    "Monitor Key Vault availability",
                    "Use multiple Key Vaults for high availability",
                    "Implement proper error handling and retry logic",
                    "Regular testing of backup and restore procedures"
                ]
            },
            "azurerm_application_gateway": {
                "security": [
                    "Enable Web Application Firewall (WAF)",
                    "Use SSL/TLS termination with strong ciphers",
                    "Configure custom SSL certificates",
                    "Implement proper backend pool health checks",
                    "Use private IP addresses for backend pools",
                    "Enable request and response logging",
                    "Configure security headers"
                ],
                "performance": [
                    "Choose appropriate tier and size",
                    "Configure connection draining",
                    "Optimize backend pool configuration",
                    "Use cookie-based session affinity when needed",
                    "Monitor performance metrics",
                    "Configure appropriate timeout values"
                ],
                "cost": [
                    "Right-size the Application Gateway",
                    "Monitor capacity and scaling requirements",
                    "Use reserved capacity for predictable workloads",
                    "Optimize routing rules and listeners",
                    "Regular review of usage patterns"
                ],
                "reliability": [
                    "Deploy across availability zones",
                    "Configure health probes for backend pools",
                    "Implement proper error handling",
                    "Monitor gateway health and performance",
                    "Use multiple instances for high availability",
                    "Implement disaster recovery procedures"
                ]
            }
        }
    
    def _get_generic_best_practices(self, resource_type: str, category: str) -> str:
        """Get generic best practices for unknown resource types."""
        generic_practices = {
            "security": [
                "Use managed identities for authentication",
                "Enable encryption at rest and in transit", 
                "Configure network security groups with least privilege",
                "Use private endpoints when available",
                "Enable monitoring and auditing",
                "Implement proper access controls"
            ],
            "performance": [
                "Choose appropriate resource sizing",
                "Monitor performance metrics",
                "Optimize configuration for workload",
                "Use appropriate Azure regions",
                "Implement caching strategies",
                "Configure load balancing when needed"
            ],
            "cost": [
                "Right-size resources based on usage",
                "Use reserved instances for predictable workloads",
                "Monitor costs regularly",
                "Implement resource lifecycle management",
                "Use appropriate pricing tiers",
                "Clean up unused resources"
            ],
            "reliability": [
                "Deploy across availability zones",
                "Implement backup and disaster recovery",
                "Monitor resource health",
                "Use infrastructure as code",
                "Implement proper error handling",
                "Test disaster recovery procedures"
            ]
        }
        
        if category != "all" and category in generic_practices:
            practices = {category: generic_practices[category]}
        else:
            practices = generic_practices
        
        return self._format_best_practices(resource_type, practices)
    
    def _format_best_practices(self, resource_type: str, practices: Dict[str, List[str]]) -> str:
        """Format best practices into a readable string."""
        formatted = f"# Azure Best Practices for {resource_type}\n\n"

        # use 4.x for azurerm provider and use 2.x for azapi provider
        formatted += "## Provider Version\n\n"
        formatted += "Use `azurerm` provider version `~> 4.x` for Azure resources.\n\n"
        formatted += "Use `azapi` provider version `~> 2.x` for advanced Azure resources.\n\n"
        
        for category, items in practices.items():
            formatted += f"## {category.title()}\n\n"
            for item in items:
                formatted += f"• {item}\n"
            formatted += "\n"
        
        # Add general recommendations
        formatted += """## General Recommendations

### Resource Naming
- Follow Azure naming conventions
- Use consistent naming patterns across resources
- Include environment and purpose in names

### Tagging Strategy
- Implement consistent tagging for cost management
- Tag resources by environment, owner, and purpose
- Use tags for automation and governance

### Infrastructure as Code
- Use version control for Terraform configurations
- Implement CI/CD pipelines for deployments
- Test configurations before applying to production
- Use remote state management

### Monitoring and Logging
- Enable diagnostic settings for all resources
- Use Azure Monitor for centralized monitoring
- Set up alerts for critical metrics
- Implement log retention policies

### Security
- Follow Azure Security Center recommendations
- Implement network segmentation
- Use Azure Policy for governance
- Regular security assessments and audits
"""
        
        return formatted
    
    def _generate_template(self, resource_type: str) -> str:
        """Generate a Terraform template with best practices."""
        normalized_name = resource_type.replace('azurerm_', '')
        
        template = f'''# {resource_type.replace('_', ' ').title()} with Best Practices Applied

terraform {{
  required_version = ">= 1.0"
  required_providers {{
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }}
  }}
}}

provider "azurerm" {{
  features {{}}
}}

# Variables
variable "resource_group_name" {{
  description = "Name of the resource group"
  type        = string
}}

variable "location" {{
  description = "Azure region for deployment"
  type        = string
  default     = "East US"
}}

variable "environment" {{
  description = "Environment name"
  type        = string
  default     = "dev"
  
  validation {{
    condition     = contains(["dev", "test", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, test, staging, prod."
  }}
}}

variable "common_tags" {{
  description = "Common tags for all resources"
  type        = map(string)
  default     = {{}}
}}

# Main resource
resource "{resource_type}" "main" {{
  name                = "${{var.environment}}-{normalized_name}"
  resource_group_name = var.resource_group_name
  location           = var.location
  
  # Add comprehensive tags
  tags = merge(
    var.common_tags,
    {{
      "Environment" = var.environment
      "ManagedBy"   = "Terraform"
      "Purpose"     = "main-workload"
    }}
  )
}}

# Outputs
output "{normalized_name}_id" {{
  description = "ID of the {normalized_name}"
  value       = {resource_type}.main.id
}}

output "{normalized_name}_name" {{
  description = "Name of the {normalized_name}"
  value       = {resource_type}.main.name
}}
'''
        
        return template
    
    def _generate_generic_template(self, resource_type: str) -> str:
        """Generate a generic template for unknown resource types."""
        return f'''# Generic template for {resource_type}

terraform {{
  required_version = ">= 1.0"
  required_providers {{
    azurerm = {{
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }}
  }}
}}

provider "azurerm" {{
  features {{}}
}}

resource "{resource_type}" "main" {{
  name                = "example-resource"
  resource_group_name = "example-rg"
  location           = "East US"
  
  tags = {{
    Environment = "Development"
    ManagedBy   = "Terraform"
  }}
}}
'''


# Global instance
_best_practices_provider = None


def get_best_practices_provider() -> AzureBestPracticesProvider:
    """Get the global best practices provider instance."""
    global _best_practices_provider
    if _best_practices_provider is None:
        _best_practices_provider = AzureBestPracticesProvider()
    return _best_practices_provider
