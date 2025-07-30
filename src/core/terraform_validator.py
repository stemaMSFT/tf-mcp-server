"""
Terraform validation utilities for Azure Terraform MCP Server.
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


class TerraformValidator:
    """Terraform HCL validation and execution utilities."""
    
    def __init__(self, max_instances: int = 10):
        """
        Initialize the Terraform validator.
        
        Args:
            max_instances: Maximum number of validator instances to maintain
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
        """Get a validator instance with proper resource management."""
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
    
    async def init_terraform(self, working_dir: str) -> Dict[str, Any]:
        """
        Run terraform init in the specified directory.
        
        Args:
            working_dir: Directory to initialize
            
        Returns:
            Initialization result
        """
        return await self._run_terraform_command(['init', '-no-color'], working_dir)
    
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


# Global validator instance management
_validator_lock = asyncio.Lock()
_validator_instance: Optional[TerraformValidator] = None


@asynccontextmanager
async def get_terraform_validator():
    """Get the global Terraform validator instance."""
    global _validator_instance
    async with _validator_lock:
        if _validator_instance is None:
            _validator_instance = TerraformValidator()
            await _validator_instance.init_tf()
        
        async with _validator_instance.get_instance() as validator:
            yield validator
