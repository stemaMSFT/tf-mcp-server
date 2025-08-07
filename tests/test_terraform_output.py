#!/usr/bin/env python3
"""
Test script to demonstrate the improved Terraform output formatting.
"""

import asyncio
import sys
import os

# Add the source directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from tf_mcp_server.core.terraform_executor import TerraformExecutor

async def test_terraform_formatting():
    """Test the new Terraform output formatting."""
    
    # Sample HCL content for testing
    sample_hcl = """
# Simple Azure Resource Group example
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "example" {
  name     = "rg-example"
  location = "East US"
}

output "resource_group_id" {
  value = azurerm_resource_group.example.id
}

output "resource_group_name" {
  value = azurerm_resource_group.example.name
}
"""

    executor = TerraformExecutor()
    
    try:
        # Test HCL formatting
        print("🔧 Testing HCL Formatting...")
        print("=" * 50)
        formatted_result = await executor.format_hcl_with_error_handling(sample_hcl)
        print(formatted_result)
        print("\n")
        
        # Test validation formatting
        print("🔍 Testing Terraform Validation...")
        print("=" * 50)
        validation_result = await executor.validate_hcl(sample_hcl)
        if validation_result.is_valid:
            print("✅ **Terraform validation successful!**")
            print(f"📁 File: {validation_result.file_path}")
        else:
            print("❌ **Terraform validation failed:**")
            for error in validation_result.errors:
                print(f"   • {error}")
        print("\n")
        
        # Test init formatting
        print("🚀 Testing Terraform Init...")
        print("=" * 50)
        init_result = await executor.init_with_formatting(sample_hcl)
        print(init_result)
        print("\n")
        
        # Test plan formatting
        print("📋 Testing Terraform Plan...")
        print("=" * 50)
        plan_result = await executor.plan_with_formatting(sample_hcl)
        print(plan_result)
        print("\n")
        
    except Exception as e:
        print(f"❌ **Error during testing:** {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        executor.clean_up()

if __name__ == "__main__":
    print("🧪 **Testing Enhanced Terraform Output Formatting**")
    print("=" * 60)
    print("This test demonstrates the improved output formatting")
    print("based on the AWS Labs MCP reference implementation.")
    print("=" * 60)
    print()
    
    # Run the test
    asyncio.run(test_terraform_formatting())
    
    print("✅ **Testing completed!**")
