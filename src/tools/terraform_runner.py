"""
Terraform command execution utilities for Azure Terraform MCP Server.
"""

from typing import Dict, Any
from ..core.terraform_executor import get_terraform_executor
from ..core.utils import extract_hcl_from_markdown


class TerraformRunner:
    """Terraform command execution utilities with simplified interface."""
    
    async def execute_terraform_command(self, command: str, hcl_content: str, var_file_content: str = None, **kwargs) -> Dict[str, Any]:
        """
        Execute a Terraform command with provided HCL content.
        
        Args:
            command: Terraform command to execute ('init', 'plan', 'apply', 'validate', etc.)
            hcl_content: HCL content to execute the command against
            var_file_content: Optional Terraform variables content
            **kwargs: Additional command-specific arguments
            
        Returns:
            Execution result with stdout, stderr, exit_code
        """
        if not hcl_content or not hcl_content.strip():
            return {
                'exit_code': -1,
                'stdout': '',
                'stderr': 'No HCL content provided',
                'command': command
            }
        
        try:
            async with get_terraform_executor() as executor:
                result = await executor.execute_with_hcl_content(
                    command=command,
                    hcl_content=hcl_content,
                    var_file_content=var_file_content,
                    **kwargs
                )
                return result
                
        except Exception as e:
            return {
                'exit_code': -1,
                'stdout': '',
                'stderr': f'Command execution error: {str(e)}',
                'command': command
            }
    
    async def terraform_init(self, hcl_content: str, upgrade: bool = False) -> str:
        """
        Initialize Terraform with provided HCL content.
        
        Args:
            hcl_content: HCL content to initialize
            upgrade: Whether to upgrade providers and modules
            
        Returns:
            Formatted initialization result
        """
        try:
            async with get_terraform_executor() as executor:
                return await executor.init_with_formatting(hcl_content, upgrade=upgrade)
        except Exception as e:
            return f"❌ Error during Terraform initialization: {str(e)}"
    
    async def terraform_plan(self, hcl_content: str, var_file_content: str = None) -> str:
        """
        Run Terraform plan with provided HCL content.
        
        Args:
            hcl_content: HCL content to plan
            var_file_content: Optional variables content
            
        Returns:
            Formatted plan result
        """
        try:
            async with get_terraform_executor() as executor:
                return await executor.plan_with_formatting(hcl_content, var_file_content)
        except Exception as e:
            return f"❌ Error during Terraform plan: {str(e)}"
    
    async def terraform_apply(self, hcl_content: str, var_file_content: str = None, auto_approve: bool = False) -> str:
        """
        Run Terraform apply with provided HCL content.
        
        Args:
            hcl_content: HCL content to apply
            var_file_content: Optional variables content
            auto_approve: Whether to automatically approve the apply
            
        Returns:
            Formatted apply result
        """
        try:
            async with get_terraform_executor() as executor:
                return await executor.apply_with_formatting(hcl_content, var_file_content, auto_approve)
        except Exception as e:
            return f"❌ Error during Terraform apply: {str(e)}"
    
    async def terraform_destroy(self, hcl_content: str, var_file_content: str = None, auto_approve: bool = False) -> str:
        """
        Run Terraform destroy with provided HCL content.
        
        Args:
            hcl_content: HCL content to destroy
            var_file_content: Optional variables content
            auto_approve: Whether to automatically approve the destroy
            
        Returns:
            Formatted destroy result
        """
        try:
            async with get_terraform_executor() as executor:
                return await executor.destroy_with_formatting(hcl_content, var_file_content, auto_approve)
        except Exception as e:
            return f"❌ Error during Terraform destroy: {str(e)}"
    
    async def format_hcl_code(self, hcl_content: str) -> str:
        """
        Format HCL code using terraform fmt.
        
        Args:
            hcl_content: HCL content to format
            
        Returns:
            Formatted HCL content or error message
        """
        try:
            async with get_terraform_executor() as executor:
                return await executor.format_hcl_with_error_handling(hcl_content)
        except Exception as e:
            return f"❌ Error during HCL formatting: {str(e)}"


# Global instance
_terraform_runner = None


def get_terraform_runner() -> TerraformRunner:
    """Get the global Terraform runner instance."""
    global _terraform_runner
    if _terraform_runner is None:
        _terraform_runner = TerraformRunner()
    return _terraform_runner
