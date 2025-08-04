"""
Terraform execution utilities for Azure Terraform MCP Server.
"""

import asyncio
import json
import logging
import shutil
import subprocess
import tempfile
from asyncio.subprocess import Process
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .models import ValidationResult
from .utils import extract_hcl_from_markdown, extract_error_messages

logger = logging.getLogger(__name__)


class TerraformExecutor:
    """Terraform HCL execution and validation utilities."""
    
    def __init__(self, max_instances: int = 10):
        """
        Initialize the Terraform executor.
        
        Args:
            max_instances: Maximum number of executor instances to maintain
        """
        self.max_instances = max_instances
        self.pool: asyncio.Queue = asyncio.Queue(max_instances)
        self.lock = asyncio.Lock()
        self._initialized = False
    
    async def init_tf(self) -> None:
        """Initialize Terraform in a temporary directory."""
        if self._initialized:
            return
        
        try:
            # Check if Terraform is installed
            result = await asyncio.create_subprocess_exec(
                'terraform', 'version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                raise RuntimeError(f"Terraform not found or not working: {stderr.decode()}")
            
            logger.info(f"Terraform version: {stdout.decode().strip()}")
            self._initialized = True
            
        except FileNotFoundError:
            raise RuntimeError("Terraform binary not found. Please install Terraform.")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Terraform: {e}")
    
    def clean_up(self) -> None:
        """Clean up temporary resources."""
        while not self.pool.empty():
            try:
                item = self.pool.get_nowait()
                if hasattr(item, 'clean_tmp'):
                    item.clean_tmp()
            except asyncio.QueueEmpty:
                break
    
    @asynccontextmanager
    async def get_instance(self):
        """Get an executor instance with proper resource management."""
        async with self.lock:
            if not self._initialized:
                await self.init_tf()
            yield self
    
    async def validate_hcl(self, hcl_content: str, file_name: str = "main.tf") -> ValidationResult:
        """
        Validate HCL content using Terraform.
        
        Args:
            hcl_content: HCL content to validate
            file_name: Name for the temporary file
            
        Returns:
            ValidationResult with validation details
        """
        if not hcl_content.strip():
            return ValidationResult(
                is_valid=False,
                errors=["Empty HCL content provided"],
                file_path=file_name
            )
        
        # Extract HCL from markdown if needed
        extracted_hcl = extract_hcl_from_markdown(hcl_content)
        if extracted_hcl:
            hcl_content = extracted_hcl
        
        # Create temporary directory for validation
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tf_file = temp_path / file_name
            
            try:
                # Write HCL content to temporary file
                tf_file.write_text(hcl_content, encoding='utf-8')
                
                # Run terraform validate
                result = await self._run_terraform_command(['validate'], str(temp_path))
                
                if result['exit_code'] == 0:
                    return ValidationResult(
                        is_valid=True,
                        file_path=str(tf_file)
                    )
                else:
                    # Parse validation errors
                    errors = self._parse_terraform_errors(result['stderr'])
                    return ValidationResult(
                        is_valid=False,
                        errors=errors,
                        file_path=str(tf_file)
                    )
                    
            except Exception as e:
                logger.error(f"Error during HCL validation: {e}")
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Validation error: {str(e)}"],
                    file_path=str(tf_file)
                )
    
    async def format_hcl(self, hcl_content: str) -> str:
        """
        Format HCL content using terraform fmt.
        
        Args:
            hcl_content: HCL content to format
            
        Returns:
            Formatted HCL content
        """
        # Extract HCL from markdown if needed
        extracted_hcl = extract_hcl_from_markdown(hcl_content)
        if extracted_hcl:
            hcl_content = extracted_hcl
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            tf_file = temp_path / "main.tf"
            
            try:
                # Write HCL content to temporary file
                tf_file.write_text(hcl_content, encoding='utf-8')
                
                # Run terraform fmt
                result = await self._run_terraform_command(['fmt', str(tf_file)], str(temp_path))
                
                if result['exit_code'] == 0:
                    # Read the formatted content
                    return tf_file.read_text(encoding='utf-8')
                else:
                    logger.warning(f"Failed to format HCL: {result['stderr']}")
                    return hcl_content  # Return original if formatting fails
                    
            except Exception as e:
                logger.error(f"Error during HCL formatting: {e}")
                return hcl_content  # Return original if error occurs
    
    async def plan_terraform(self, working_dir: str, var_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Run terraform plan in the specified directory.
        
        Args:
            working_dir: Directory containing Terraform files
            var_file: Optional variables file
            
        Returns:
            Plan execution result
        """
        cmd = ['plan', '-no-color', '-detailed-exitcode']
        
        if var_file:
            cmd.extend(['-var-file', var_file])
        
        return await self._run_terraform_command(cmd, working_dir)
    
    async def init_terraform(self, working_dir: str, upgrade: bool = False) -> Dict[str, Any]:
        """
        Run terraform init in the specified directory.
        
        Args:
            working_dir: Directory to initialize
            upgrade: Whether to upgrade modules and providers
            
        Returns:
            Initialization result
        """
        cmd = ['init', '-no-color']
        if upgrade:
            cmd.append('-upgrade')
        return await self._run_terraform_command(cmd, working_dir)
    
    async def apply_terraform(self, working_dir: str, var_file: Optional[str] = None, auto_approve: bool = False) -> Dict[str, Any]:
        """
        Run terraform apply in the specified directory.
        
        Args:
            working_dir: Directory containing Terraform files
            var_file: Optional variables file
            auto_approve: Whether to automatically approve the apply
            
        Returns:
            Apply execution result
        """
        cmd = ['apply', '-no-color']
        
        if auto_approve:
            cmd.append('-auto-approve')
        
        if var_file:
            cmd.extend(['-var-file', var_file])
        
        return await self._run_terraform_command(cmd, working_dir)
    
    async def destroy_terraform(self, working_dir: str, var_file: Optional[str] = None, auto_approve: bool = False) -> Dict[str, Any]:
        """
        Run terraform destroy in the specified directory.
        
        Args:
            working_dir: Directory containing Terraform files
            var_file: Optional variables file
            auto_approve: Whether to automatically approve the destroy
            
        Returns:
            Destroy execution result
        """
        cmd = ['destroy', '-no-color']
        
        if auto_approve:
            cmd.append('-auto-approve')
        
        if var_file:
            cmd.extend(['-var-file', var_file])
        
        return await self._run_terraform_command(cmd, working_dir)
    
    async def refresh_terraform(self, working_dir: str, var_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Run terraform refresh in the specified directory.
        
        Args:
            working_dir: Directory containing Terraform files
            var_file: Optional variables file
            
        Returns:
            Refresh execution result
        """
        cmd = ['refresh', '-no-color']
        
        if var_file:
            cmd.extend(['-var-file', var_file])
        
        return await self._run_terraform_command(cmd, working_dir)
    
    async def show_terraform(self, working_dir: str, state_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Run terraform show in the specified directory.
        
        Args:
            working_dir: Directory containing Terraform files
            state_file: Optional state file to show
            
        Returns:
            Show execution result
        """
        cmd = ['show', '-no-color']
        
        if state_file:
            cmd.append(state_file)
        
        return await self._run_terraform_command(cmd, working_dir)
    
    async def output_terraform(self, working_dir: str, output_name: Optional[str] = None, json_format: bool = False) -> Dict[str, Any]:
        """
        Run terraform output in the specified directory.
        
        Args:
            working_dir: Directory containing Terraform files
            output_name: Optional specific output to retrieve
            json_format: Whether to return output in JSON format
            
        Returns:
            Output execution result
        """
        cmd = ['output', '-no-color']
        
        if json_format:
            cmd.append('-json')
        
        if output_name:
            cmd.append(output_name)
        
        return await self._run_terraform_command(cmd, working_dir)
    
    async def workspace_list(self, working_dir: str) -> Dict[str, Any]:
        """
        List Terraform workspaces.
        
        Args:
            working_dir: Directory containing Terraform files
            
        Returns:
            Workspace list result
        """
        return await self._run_terraform_command(['workspace', 'list'], working_dir)
    
    async def workspace_select(self, working_dir: str, workspace_name: str) -> Dict[str, Any]:
        """
        Select a Terraform workspace.
        
        Args:
            working_dir: Directory containing Terraform files
            workspace_name: Name of the workspace to select
            
        Returns:
            Workspace selection result
        """
        return await self._run_terraform_command(['workspace', 'select', workspace_name], working_dir)
    
    async def workspace_new(self, working_dir: str, workspace_name: str) -> Dict[str, Any]:
        """
        Create a new Terraform workspace.
        
        Args:
            working_dir: Directory containing Terraform files
            workspace_name: Name of the new workspace
            
        Returns:
            Workspace creation result
        """
        return await self._run_terraform_command(['workspace', 'new', workspace_name], working_dir)
    
    async def state_list(self, working_dir: str) -> Dict[str, Any]:
        """
        List resources in Terraform state.
        
        Args:
            working_dir: Directory containing Terraform files
            
        Returns:
            State list result
        """
        return await self._run_terraform_command(['state', 'list'], working_dir)
    
    async def state_show(self, working_dir: str, resource_address: str) -> Dict[str, Any]:
        """
        Show a specific resource in Terraform state.
        
        Args:
            working_dir: Directory containing Terraform files
            resource_address: Address of the resource to show
            
        Returns:
            State show result
        """
        return await self._run_terraform_command(['state', 'show', resource_address], working_dir)
    
    async def execute_with_hcl_content(self, command: str, hcl_content: str, var_file_content: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute a Terraform command with provided HCL content in a temporary directory.
        
        Args:
            command: Terraform command to execute ('init', 'plan', 'apply', etc.)
            hcl_content: HCL content to write to main.tf
            var_file_content: Optional content for terraform.tfvars
            **kwargs: Additional arguments for the command
            
        Returns:
            Command execution result
        """
        # Extract HCL from markdown if needed
        extracted_hcl = extract_hcl_from_markdown(hcl_content)
        if extracted_hcl:
            hcl_content = extracted_hcl
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # Write HCL content to main.tf
                main_tf = temp_path / "main.tf"
                main_tf.write_text(hcl_content, encoding='utf-8')
                
                # Write variables file if provided
                if var_file_content:
                    tfvars = temp_path / "terraform.tfvars"
                    tfvars.write_text(var_file_content, encoding='utf-8')
                
                # Execute the command based on type
                if command == 'init':
                    return await self.init_terraform(str(temp_path), **kwargs)
                elif command == 'plan':
                    var_file = "terraform.tfvars" if var_file_content else None
                    return await self.plan_terraform(str(temp_path), var_file)
                elif command == 'apply':
                    var_file = "terraform.tfvars" if var_file_content else None
                    return await self.apply_terraform(str(temp_path), var_file, **kwargs)
                elif command == 'destroy':
                    var_file = "terraform.tfvars" if var_file_content else None
                    return await self.destroy_terraform(str(temp_path), var_file, **kwargs)
                elif command == 'validate':
                    # For validate, we need to init first
                    init_result = await self.init_terraform(str(temp_path))
                    if init_result['exit_code'] != 0:
                        return init_result
                    return await self._run_terraform_command(['validate'], str(temp_path))
                elif command == 'fmt':
                    return await self._run_terraform_command(['fmt', '-check'], str(temp_path))
                elif command == 'show':
                    return await self.show_terraform(str(temp_path))
                elif command == 'output':
                    return await self.output_terraform(str(temp_path), **kwargs)
                else:
                    return {
                        'exit_code': -1,
                        'stdout': '',
                        'stderr': f'Unsupported command: {command}',
                        'command': command
                    }
                    
            except Exception as e:
                logger.error(f"Error executing Terraform command {command}: {e}")
                return {
                    'exit_code': -1,
                    'stdout': '',
                    'stderr': str(e),
                    'command': command
                }
    
    async def init_with_formatting(self, hcl_content: str, upgrade: bool = False) -> str:
        """
        Initialize Terraform with provided HCL content and return formatted result.
        
        Args:
            hcl_content: HCL content to initialize
            upgrade: Whether to upgrade providers and modules
            
        Returns:
            Formatted initialization result
        """
        result = await self.execute_with_hcl_content('init', hcl_content, upgrade=upgrade)
        
        if result['exit_code'] == 0:
            return f"✅ Terraform initialization successful!\n\n{result['stdout']}"
        else:
            return f"❌ Terraform initialization failed:\n\n{result['stderr']}"
    
    async def plan_with_formatting(self, hcl_content: str, var_file_content: Optional[str] = None) -> str:
        """
        Run Terraform plan with provided HCL content and return formatted result.
        
        Args:
            hcl_content: HCL content to plan
            var_file_content: Optional variables content
            
        Returns:
            Formatted plan result
        """
        # First initialize
        init_result = await self.execute_with_hcl_content('init', hcl_content)
        if init_result['exit_code'] != 0:
            return f"❌ Terraform init failed before plan:\n\n{init_result['stderr']}"
        
        # Then run plan
        result = await self.execute_with_hcl_content('plan', hcl_content, var_file_content)
        
        if result['exit_code'] == 0:
            return f"✅ Terraform plan successful!\n\n{result['stdout']}"
        elif result['exit_code'] == 2:
            return f"📋 Terraform plan completed with changes:\n\n{result['stdout']}"
        else:
            return f"❌ Terraform plan failed:\n\n{result['stderr']}"
    
    async def apply_with_formatting(self, hcl_content: str, var_file_content: Optional[str] = None, auto_approve: bool = False) -> str:
        """
        Run Terraform apply with provided HCL content and return formatted result.
        
        Args:
            hcl_content: HCL content to apply
            var_file_content: Optional variables content
            auto_approve: Whether to automatically approve the apply
            
        Returns:
            Formatted apply result
        """
        # First initialize
        init_result = await self.execute_with_hcl_content('init', hcl_content)
        if init_result['exit_code'] != 0:
            return f"❌ Terraform init failed before apply:\n\n{init_result['stderr']}"
        
        # Then run apply
        result = await self.execute_with_hcl_content('apply', hcl_content, var_file_content, auto_approve=auto_approve)
        
        if result['exit_code'] == 0:
            return f"✅ Terraform apply successful!\n\n{result['stdout']}"
        else:
            return f"❌ Terraform apply failed:\n\n{result['stderr']}"
    
    async def destroy_with_formatting(self, hcl_content: str, var_file_content: Optional[str] = None, auto_approve: bool = False) -> str:
        """
        Run Terraform destroy with provided HCL content and return formatted result.
        
        Args:
            hcl_content: HCL content to destroy
            var_file_content: Optional variables content
            auto_approve: Whether to automatically approve the destroy
            
        Returns:
            Formatted destroy result
        """
        # First initialize
        init_result = await self.execute_with_hcl_content('init', hcl_content)
        if init_result['exit_code'] != 0:
            return f"❌ Terraform init failed before destroy:\n\n{init_result['stderr']}"
        
        # Then run destroy
        result = await self.execute_with_hcl_content('destroy', hcl_content, var_file_content, auto_approve=auto_approve)
        
        if result['exit_code'] == 0:
            return f"✅ Terraform destroy successful!\n\n{result['stdout']}"
        else:
            return f"❌ Terraform destroy failed:\n\n{result['stderr']}"
    
    async def format_hcl_with_error_handling(self, hcl_content: str) -> str:
        """
        Format HCL code using terraform fmt with error handling.
        
        Args:
            hcl_content: HCL content to format
            
        Returns:
            Formatted HCL content or error message
        """
        if not hcl_content or not hcl_content.strip():
            return "❌ Error: No HCL content provided for formatting."
        
        try:
            formatted_content = await self.format_hcl(hcl_content)
            return formatted_content
        except Exception as e:
            return f"❌ Error during HCL formatting: {str(e)}"
    
    async def _run_terraform_command(self, cmd: List[str], working_dir: str) -> Dict[str, Any]:
        """
        Run a Terraform command in the specified directory.
        
        Args:
            cmd: Terraform command and arguments
            working_dir: Working directory for the command
            
        Returns:
            Command execution result
        """
        full_cmd = ['terraform'] + cmd
        
        try:
            process = await asyncio.create_subprocess_exec(
                *full_cmd,
                cwd=working_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return {
                'exit_code': process.returncode,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8'),
                'command': ' '.join(full_cmd)
            }
            
        except Exception as e:
            logger.error(f"Error running Terraform command {full_cmd}: {e}")
            return {
                'exit_code': -1,
                'stdout': '',
                'stderr': str(e),
                'command': ' '.join(full_cmd)
            }
    
    def _parse_terraform_errors(self, stderr: str) -> List[str]:
        """
        Parse Terraform error output into structured messages.
        
        Args:
            stderr: Standard error output from Terraform
            
        Returns:
            List of error messages
        """
        errors = []
        
        if not stderr:
            return errors
        
        # Try to parse as JSON first (newer Terraform versions)
        try:
            lines = stderr.strip().split('\n')
            for line in lines:
                if line.startswith('{'):
                    error_data = json.loads(line)
                    if error_data.get('@level') == 'error':
                        message = error_data.get('@message', 'Unknown error')
                        errors.append(message)
        except (json.JSONDecodeError, ValueError):
            # Fall back to text parsing
            lines = stderr.strip().split('\n')
            current_error = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('Error:') or line.startswith('╷'):
                    if current_error:
                        errors.append('\n'.join(current_error))
                        current_error = []
                    if not line.startswith('╷'):
                        current_error.append(line)
                elif line and current_error:
                    current_error.append(line)
                elif line.startswith('╵') and current_error:
                    errors.append('\n'.join(current_error))
                    current_error = []
            
            # Add any remaining error
            if current_error:
                errors.append('\n'.join(current_error))
        
        # If no structured errors found, return the raw stderr
        if not errors and stderr.strip():
            errors.append(stderr.strip())
        
        return errors


# Global executor instance management
_executor_lock = asyncio.Lock()
_executor_instance: Optional[TerraformExecutor] = None


@asynccontextmanager
async def get_terraform_executor():
    """Get the global Terraform executor instance."""
    global _executor_instance
    async with _executor_lock:
        if _executor_instance is None:
            _executor_instance = TerraformExecutor()
            await _executor_instance.init_tf()
        
        async with _executor_instance.get_instance() as executor:
            yield executor
