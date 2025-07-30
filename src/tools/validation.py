"""
Validation tools for Azure Terraform MCP Server.
"""

from typing import Dict, Any, List
from core.models import ValidationResult
from core.terraform_validator import get_terraform_validator
from core.utils import extract_hcl_from_markdown


class HCLValidator:
    """HCL code validation utilities."""
    
    async def validate_hcl_code(self, hcl_content: str) -> str:
        """
        Validate HCL code and return formatted result.
        
        Args:
            hcl_content: HCL content to validate
            
        Returns:
            Formatted validation result string
        """
        if not hcl_content or not hcl_content.strip():
            return "❌ Error: No HCL content provided for validation."
        
        try:
            async with get_terraform_validator() as validator:
                result = await validator.validate_hcl(hcl_content)
                
                if result.is_valid:
                    return "✅ HCL code is valid!"
                else:
                    errors_text = "\n".join(f"  • {error}" for error in result.errors)
                    return f"❌ HCL Validation Errors:\n\n{errors_text}"
                    
        except Exception as e:
            return f"❌ Error during HCL validation: {str(e)}"
    
    async def format_hcl_code(self, hcl_content: str) -> str:
        """
        Format HCL code using terraform fmt.
        
        Args:
            hcl_content: HCL content to format
            
        Returns:
            Formatted HCL content or error message
        """
        if not hcl_content or not hcl_content.strip():
            return "❌ Error: No HCL content provided for formatting."
        
        try:
            async with get_terraform_validator() as validator:
                formatted_content = await validator.format_hcl(hcl_content)
                return formatted_content
                
        except Exception as e:
            return f"❌ Error during HCL formatting: {str(e)}"


class SecurityValidator:
    """Security validation for Terraform configurations."""
    
    def __init__(self):
        """Initialize the security validator."""
        self.security_rules = self._load_security_rules()
    
    def validate_security(self, hcl_content: str) -> Dict[str, Any]:
        """
        Perform security validation on HCL content.
        
        Args:
            hcl_content: HCL content to validate
            
        Returns:
            Security validation result
        """
        findings = []
        
        # Extract HCL if needed
        extracted_hcl = extract_hcl_from_markdown(hcl_content)
        if extracted_hcl:
            hcl_content = extracted_hcl
        
        # Run security checks
        findings.extend(self._check_encryption(hcl_content))
        findings.extend(self._check_network_security(hcl_content))
        findings.extend(self._check_access_control(hcl_content))
        findings.extend(self._check_storage_security(hcl_content))
        findings.extend(self._check_monitoring(hcl_content))
        
        # Calculate summary
        total_checks = len(self.security_rules)
        failed_checks = len(findings)
        passed_checks = total_checks - failed_checks
        
        return {
            "scan_type": "Azure Security Best Practices",
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "skipped_checks": 0,
            "findings": findings,
            "summary": f"Security scan completed: {passed_checks} passed, {failed_checks} failed"
        }
    
    def _load_security_rules(self) -> List[Dict[str, Any]]:
        """Load security validation rules."""
        return [
            {
                "id": "AZURE_001",
                "name": "Storage Account Encryption",
                "description": "Storage accounts should have encryption enabled",
                "severity": "HIGH"
            },
            {
                "id": "AZURE_002", 
                "name": "Network Security Groups",
                "description": "Network security groups should not allow unrestricted access",
                "severity": "HIGH"
            },
            {
                "id": "AZURE_003",
                "name": "Key Vault Access Policies",
                "description": "Key Vault should have proper access policies configured",
                "severity": "MEDIUM"
            },
            {
                "id": "AZURE_004",
                "name": "Public IP Restrictions",
                "description": "Public IPs should have restrictions when possible",
                "severity": "MEDIUM"
            },
            {
                "id": "AZURE_005",
                "name": "Resource Tagging",
                "description": "Resources should have appropriate tags",
                "severity": "LOW"
            },
            {
                "id": "AZURE_006",
                "name": "Diagnostic Settings",
                "description": "Resources should have diagnostic settings enabled",
                "severity": "MEDIUM"
            }
        ]
    
    def _check_encryption(self, hcl_content: str) -> List[Dict[str, Any]]:
        """Check for encryption-related security issues."""
        findings = []
        
        # Check for storage account without encryption
        if "azurerm_storage_account" in hcl_content:
            if "enable_blob_encryption" not in hcl_content and "encryption" not in hcl_content:
                findings.append({
                    "rule_id": "AZURE_001",
                    "severity": "HIGH",
                    "message": "Storage account does not have encryption explicitly configured",
                    "resource_type": "azurerm_storage_account",
                    "recommendation": "Add encryption block to storage account configuration"
                })
        
        return findings
    
    def _check_network_security(self, hcl_content: str) -> List[Dict[str, Any]]:
        """Check for network security issues."""
        findings = []
        
        # Check for overly permissive NSG rules
        if "azurerm_network_security_rule" in hcl_content:
            if '"*"' in hcl_content and ("source_address_prefix" in hcl_content or "destination_address_prefix" in hcl_content):
                findings.append({
                    "rule_id": "AZURE_002",
                    "severity": "HIGH", 
                    "message": "Network security rule allows unrestricted access (*)",
                    "resource_type": "azurerm_network_security_rule",
                    "recommendation": "Restrict source and destination address prefixes"
                })
        
        return findings
    
    def _check_access_control(self, hcl_content: str) -> List[Dict[str, Any]]:
        """Check for access control issues."""
        findings = []
        
        # Check for Key Vault without access policies
        if "azurerm_key_vault" in hcl_content:
            if "access_policy" not in hcl_content:
                findings.append({
                    "rule_id": "AZURE_003",
                    "severity": "MEDIUM",
                    "message": "Key Vault does not have access policies configured",
                    "resource_type": "azurerm_key_vault",
                    "recommendation": "Configure appropriate access policies for Key Vault"
                })
        
        return findings
    
    def _check_storage_security(self, hcl_content: str) -> List[Dict[str, Any]]:
        """Check for storage-specific security issues."""
        findings = []
        
        # Check for public access on storage containers
        if "azurerm_storage_container" in hcl_content:
            if 'container_access_type = "blob"' in hcl_content or 'container_access_type = "container"' in hcl_content:
                findings.append({
                    "rule_id": "AZURE_004",
                    "severity": "MEDIUM",
                    "message": "Storage container allows public access",
                    "resource_type": "azurerm_storage_container",
                    "recommendation": "Consider using private access unless public access is required"
                })
        
        return findings
    
    def _check_monitoring(self, hcl_content: str) -> List[Dict[str, Any]]:
        """Check for monitoring and logging issues."""
        findings = []
        
        # Check for missing diagnostic settings
        azure_resources = [
            "azurerm_storage_account",
            "azurerm_key_vault", 
            "azurerm_virtual_machine",
            "azurerm_application_gateway"
        ]
        
        for resource in azure_resources:
            if resource in hcl_content and "azurerm_monitor_diagnostic_setting" not in hcl_content:
                findings.append({
                    "rule_id": "AZURE_006",
                    "severity": "MEDIUM",
                    "message": f"{resource} does not have diagnostic settings configured",
                    "resource_type": resource,
                    "recommendation": "Add diagnostic settings to enable monitoring and logging"
                })
                break  # Only report once per configuration
        
        return findings


# Global instances
_hcl_validator = None
_security_validator = None


def get_hcl_validator() -> HCLValidator:
    """Get the global HCL validator instance."""
    global _hcl_validator
    if _hcl_validator is None:
        _hcl_validator = HCLValidator()
    return _hcl_validator


def get_security_validator() -> SecurityValidator:
    """Get the global security validator instance."""
    global _security_validator
    if _security_validator is None:
        _security_validator = SecurityValidator()
    return _security_validator
