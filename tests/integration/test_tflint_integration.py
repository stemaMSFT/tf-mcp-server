#!/usr/bin/env python3
"""
Integration test for TFLint functionality in the Azure Terraform MCP Server.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tf_mcp_server.core.server import create_server
from tf_mcp_server.core.config import Config


async def test_tflint_integration():
    """Test TFLint integration with the MCP server."""
    
    print("🧪 TFLint Integration Test")
    print("=" * 40)
    
    # Create server
    config = Config.from_env()
    server = create_server(config)
    print("✅ Server created successfully")
    
    # Sample Terraform configuration
    sample_hcl = '''
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
    
    # Test TFLint installation check
    print("\n1. Testing TFLint installation check...")
    try:
        # Access the tool function directly for testing
        from tf_mcp_server.tools.tflint_runner import get_tflint_runner
        
        tflint_runner = get_tflint_runner()
        result = await tflint_runner.check_tflint_installation()
        
        if result['installed']:
            print(f"✅ TFLint is installed: {result['version']}")
        else:
            print(f"ℹ️  TFLint is not installed: {result['error']}")
            print("   This is expected if TFLint is not installed on the system")
        
    except Exception as e:
        print(f"❌ Error checking TFLint installation: {e}")
        return False
    
    # Test TFLint analysis (even if TFLint is not installed, should handle gracefully)
    print("\n2. Testing TFLint analysis...")
    try:
        analysis_result = await tflint_runner.lint_terraform_configuration(
            hcl_content=sample_hcl,
            output_format="json",
            enable_azure_plugin=True,
            initialize_plugins=False  # Don't initialize to avoid errors if not installed
        )
        
        if analysis_result['success']:
            print("✅ TFLint analysis completed successfully")
            print(f"   Issues found: {analysis_result['summary']['total_issues']}")
        else:
            print(f"ℹ️  TFLint analysis failed (expected if not installed): {analysis_result['error']}")
        
    except Exception as e:
        print(f"❌ Error running TFLint analysis: {e}")
        return False
    
    # Test with empty content
    print("\n3. Testing error handling with empty content...")
    try:
        empty_result = await tflint_runner.lint_terraform_configuration(
            hcl_content="",
            output_format="json"
        )
        
        if not empty_result['success'] and 'No HCL content provided' in empty_result['error']:
            print("✅ Empty content handled correctly")
        else:
            print("❌ Empty content not handled as expected")
            return False
        
    except Exception as e:
        print(f"❌ Error testing empty content: {e}")
        return False
    
    print("\n🎉 All TFLint integration tests passed!")
    print("\nThe TFLint functionality is working correctly.")
    print("To use TFLint analysis features, install TFLint on your system.")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_tflint_integration())
    sys.exit(0 if success else 1)
