"""
Tests for TFLint runner functionality.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from tf_mcp_server.tools.tflint_runner import TFLintRunner, get_tflint_runner


@pytest.fixture
def tflint_runner():
    """Create a TFLint runner instance for testing."""
    return TFLintRunner()


@pytest.fixture
def sample_terraform_config():
    """Sample Terraform configuration for testing."""
    return '''
resource "azurerm_resource_group" "example" {
  name     = "example-resources"
  location = "West Europe"
}

resource "azurerm_storage_account" "example" {
  name                     = "examplestorageaccount"
  resource_group_name      = azurerm_resource_group.example.name
  location                 = azurerm_resource_group.example.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}
'''


@pytest.fixture
def sample_terraform_vars():
    """Sample Terraform variables for testing."""
    return '''
location = "West Europe"
environment = "test"
'''


class TestTFLintRunner:
    """Test cases for TFLint runner."""
    
    def test_tflint_runner_initialization(self, tflint_runner):
        """Test TFLint runner initialization."""
        assert isinstance(tflint_runner, TFLintRunner)
        assert hasattr(tflint_runner, 'tflint_executable')
    
    def test_get_tflint_runner_singleton(self):
        """Test that get_tflint_runner returns a singleton."""
        runner1 = get_tflint_runner()
        runner2 = get_tflint_runner()
        assert runner1 is runner2
    
    def test_create_tflint_config_basic(self, tflint_runner):
        """Test creation of basic TFLint configuration."""
        config = tflint_runner._create_tflint_config(enable_azure_plugin=False)
        assert 'plugin "terraform"' in config
        assert 'preset  = "recommended"' in config
        assert 'plugin "azurerm"' not in config
    
    def test_create_tflint_config_with_azure(self, tflint_runner):
        """Test creation of TFLint configuration with Azure plugin."""
        config = tflint_runner._create_tflint_config(enable_azure_plugin=True)
        assert 'plugin "terraform"' in config
        assert 'plugin "azurerm"' in config
        assert 'source  = "github.com/terraform-linters/tflint-ruleset-azurerm"' in config
    
    @patch('subprocess.run')
    def test_check_tflint_installation_success(self, mock_run, tflint_runner):
        """Test successful TFLint installation check."""
        # Mock successful tflint --version command
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "TFLint version 0.50.0"
        mock_run.return_value = mock_result
        
        # Note: This is an async method, so we need to use pytest-asyncio
        import asyncio
        result = asyncio.run(tflint_runner.check_tflint_installation())
        
        assert result['installed'] is True
        assert 'TFLint version 0.50.0' in result['version']
        assert 'executable_path' in result
    
    @patch('subprocess.run')
    def test_check_tflint_installation_not_found(self, mock_run, tflint_runner):
        """Test TFLint installation check when not found."""
        # Mock FileNotFoundError
        mock_run.side_effect = FileNotFoundError("tflint not found")
        
        import asyncio
        result = asyncio.run(tflint_runner.check_tflint_installation())
        
        assert result['installed'] is False
        assert 'not found' in result['error']
        assert 'installation_help' in result
        assert 'install_methods' in result['installation_help']
    
    @patch('subprocess.run')
    async def test_lint_terraform_configuration_success(self, mock_run, tflint_runner, sample_terraform_config):
        """Test successful TFLint analysis."""
        # Mock successful tflint --init
        init_result = Mock()
        init_result.returncode = 0
        init_result.stdout = "Plugins initialized"
        init_result.stderr = ""
        
        # Mock successful tflint analysis
        lint_result = Mock()
        lint_result.returncode = 0
        lint_result.stdout = '{"issues": []}'
        lint_result.stderr = ""
        
        mock_run.side_effect = [init_result, lint_result]
        
        result = await tflint_runner.lint_terraform_configuration(
            hcl_content=sample_terraform_config,
            output_format="json"
        )
        
        assert result['success'] is True
        assert result['issues'] == []
        assert result['summary']['total_issues'] == 0
    
    @patch('subprocess.run')
    async def test_lint_terraform_configuration_with_issues(self, mock_run, tflint_runner, sample_terraform_config):
        """Test TFLint analysis with issues found."""
        # Mock successful tflint --init
        init_result = Mock()
        init_result.returncode = 0
        init_result.stdout = "Plugins initialized"
        init_result.stderr = ""
        
        # Mock tflint analysis with issues (exit code 2)
        lint_result = Mock()
        lint_result.returncode = 2
        lint_result.stdout = '''
        {
            "issues": [
                {
                    "rule": {
                        "name": "azurerm_storage_account_min_tls_version",
                        "severity": "warning"
                    },
                    "message": "Missing min_tls_version argument",
                    "range": {
                        "filename": "main.tf",
                        "start": {"line": 8, "column": 1},
                        "end": {"line": 15, "column": 2}
                    }
                }
            ]
        }
        '''
        lint_result.stderr = ""
        
        mock_run.side_effect = [init_result, lint_result]
        
        result = await tflint_runner.lint_terraform_configuration(
            hcl_content=sample_terraform_config,
            output_format="json"
        )
        
        assert result['success'] is True
        assert len(result['issues']) == 1
        assert result['summary']['total_issues'] == 1
        assert result['summary']['warnings'] == 1
    
    async def test_lint_terraform_configuration_empty_content(self, tflint_runner):
        """Test TFLint analysis with empty content."""
        result = await tflint_runner.lint_terraform_configuration(
            hcl_content="",
            output_format="json"
        )
        
        assert result['success'] is False
        assert 'No HCL content provided' in result['error']
        assert result['issues'] == []
    
    @patch('subprocess.run')
    async def test_lint_terraform_configuration_timeout(self, mock_run, tflint_runner, sample_terraform_config):
        """Test TFLint analysis with timeout."""
        # Mock timeout on init
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("tflint", 60)
        
        result = await tflint_runner.lint_terraform_configuration(
            hcl_content=sample_terraform_config,
            output_format="json"
        )
        
        assert result['success'] is False
        assert 'timed out' in result['error']
    
    @patch('subprocess.run')
    async def test_run_tflint_init_success(self, mock_run, tflint_runner):
        """Test successful TFLint plugin initialization."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Installing plugins..."
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await tflint_runner._run_tflint_init(temp_dir)
            
            assert result['success'] is True
            assert 'Installing plugins' in result['stdout']
    
    @patch('subprocess.run')
    async def test_run_tflint_init_failure(self, mock_run, tflint_runner):
        """Test failed TFLint plugin initialization."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Failed to install plugins"
        mock_run.return_value = mock_result
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await tflint_runner._run_tflint_init(temp_dir)
            
            assert result['success'] is False
            assert 'Failed to install plugins' in result['error']
    
    def test_parse_tflint_output_json_format(self, tflint_runner):
        """Test parsing TFLint JSON output."""
        import subprocess
        
        # Mock successful result with JSON output
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 2  # Issues found
        mock_result.stdout = '''
        {
            "issues": [
                {
                    "rule": {"name": "test_rule", "severity": "error"},
                    "message": "Test error message"
                },
                {
                    "rule": {"name": "test_rule2", "severity": "warning"},
                    "message": "Test warning message"
                }
            ]
        }
        '''
        mock_result.stderr = ""
        
        result = tflint_runner._parse_tflint_output(mock_result, "json")
        
        assert result['success'] is True
        assert len(result['issues']) == 2
        assert result['summary']['total_issues'] == 2
        assert result['summary']['errors'] == 1
        assert result['summary']['warnings'] == 1
    
    def test_parse_tflint_output_execution_error(self, tflint_runner):
        """Test parsing TFLint output with execution error."""
        import subprocess
        
        # Mock failed result
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 1  # Execution error
        mock_result.stdout = ""
        mock_result.stderr = "TFLint execution failed"
        
        result = tflint_runner._parse_tflint_output(mock_result, "json")
        
        assert result['success'] is False
        assert 'TFLint execution failed' in result['error']
        assert result['summary']['total_issues'] == 0
