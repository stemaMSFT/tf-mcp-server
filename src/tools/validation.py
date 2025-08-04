"""
Validation tools for Azure Terraform MCP Server.

This module provides backward compatibility by re-exporting classes from
the reorganized terraform_runner and security_rules modules.
"""

from typing import Dict, Any
from core.models import ValidationResult

# Import from reorganized modules
from .terraform_runner import TerraformRunner, get_terraform_runner
from .security_rules import AzureSecurityValidator, get_azure_security_validator


# Backward compatibility aliases
class HCLValidator(TerraformRunner):
    """
    Backward compatibility alias for TerraformRunner.
    
    This class is deprecated. Use TerraformRunner from terraform_runner module instead.
    """
    pass


class SecurityValidator(AzureSecurityValidator):
    """
    Backward compatibility alias for AzureSecurityValidator.
    
    This class is deprecated. Use AzureSecurityValidator from security_rules module instead.
    """
    pass


# Backward compatibility factory functions
def get_hcl_validator() -> HCLValidator:
    """
    Get the global HCL validator instance.
    
    This function is deprecated. Use get_terraform_runner() instead.
    """
    return get_terraform_runner()


def get_security_validator() -> SecurityValidator:
    """
    Get the global security validator instance.
    
    This function is deprecated. Use get_azure_security_validator() instead.
    """
    return get_azure_security_validator()
