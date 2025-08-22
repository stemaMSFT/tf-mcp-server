#!/usr/bin/env python3
"""
Example script demonstrating TFLint integration with the Azure Terraform MCP Server.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tf_mcp_server.tools.tflint_runner import get_tflint_runner


async def main():
    """Main example function."""
    
    # Sample Terraform configuration with potential issues
    sample_hcl = '''
# Example Azure resources with some best practice violations
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
  
  # Missing: min_tls_version, enable_https_traffic_only, etc.
}

resource "azurerm_virtual_network" "example" {
  name                = "example-network"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
}

resource "azurerm_subnet" "example" {
  name                 = "internal"
  resource_group_name  = azurerm_resource_group.example.name
  virtual_network_name = azurerm_virtual_network.example.name
  address_prefixes     = ["10.0.2.0/24"]
}
'''
    
    print("🔍 TFLint Integration Example")
    print("=" * 50)
    
    # Get TFLint runner instance
    tflint_runner = get_tflint_runner()
    
    # Check if TFLint is installed
    print("\n1. Checking TFLint installation...")
    installation_status = await tflint_runner.check_tflint_installation()
    
    if installation_status['installed']:
        print(f"✅ TFLint is installed: {installation_status['version']}")
        print(f"   Executable path: {installation_status['executable_path']}")
    else:
        print(f"❌ TFLint is not installed: {installation_status['error']}")
        print("\n📥 Installation methods:")
        for method, command in installation_status.get('installation_help', {}).get('install_methods', {}).items():
            print(f"   {method}: {command}")
        print("\nPlease install TFLint to continue with the analysis.")
        return
    
    # Run TFLint analysis with Azure plugin
    print("\n2. Running TFLint analysis with Azure plugin...")
    result = await tflint_runner.lint_terraform_configuration(
        hcl_content=sample_hcl,
        output_format="json",
        enable_azure_plugin=True,
        initialize_plugins=True
    )
    
    if result['success']:
        print("✅ TFLint analysis completed successfully")
        
        # Display summary
        summary = result['summary']
        print(f"\n📊 Analysis Summary:")
        print(f"   Total issues: {summary['total_issues']}")
        print(f"   Errors: {summary['errors']}")
        print(f"   Warnings: {summary['warnings']}")
        print(f"   Notices: {summary['notices']}")
        
        # Display issues if any
        if result['issues']:
            print(f"\n🔍 Issues Found ({len(result['issues'])}):")
            for i, issue in enumerate(result['issues'], 1):
                rule = issue.get('rule', {})
                severity = rule.get('severity', 'unknown').upper()
                rule_name = rule.get('name', 'unknown')
                message = issue.get('message', 'No message')
                
                print(f"\n   {i}. [{severity}] {rule_name}")
                print(f"      Message: {message}")
                
                # Location information
                range_info = issue.get('range', {})
                if range_info:
                    filename = range_info.get('filename', 'unknown')
                    start = range_info.get('start', {})
                    line = start.get('line', 'unknown')
                    column = start.get('column', 'unknown')
                    print(f"      Location: {filename}:{line}:{column}")
        else:
            print("\n✅ No issues found in the configuration!")
    
    else:
        print(f"❌ TFLint analysis failed: {result['error']}")
    
    # Run analysis with different output format
    print("\n3. Running analysis with compact output format...")
    compact_result = await tflint_runner.lint_terraform_configuration(
        hcl_content=sample_hcl,
        output_format="compact",
        enable_azure_plugin=True,
        initialize_plugins=False  # Don't reinitialize plugins
    )
    
    if compact_result['success']:
        print("✅ Compact format analysis completed")
        if compact_result.get('raw_output'):
            print("Raw output:")
            print(compact_result['raw_output'])
    
    # Example with specific rules
    print("\n4. Running analysis with specific rule configuration...")
    specific_rules_result = await tflint_runner.lint_terraform_configuration(
        hcl_content=sample_hcl,
        output_format="json",
        enable_azure_plugin=True,
        disable_rules=["terraform_unused_declarations"],
        initialize_plugins=False
    )
    
    if specific_rules_result['success']:
        print(f"✅ Analysis with rule configuration completed")
        print(f"   Issues found: {specific_rules_result['summary']['total_issues']}")
    
    print("\n🎉 TFLint integration example completed!")
    print("\nNext steps:")
    print("- Integrate TFLint analysis into your CI/CD pipeline")
    print("- Configure custom rules based on your organization's standards")
    print("- Use different output formats for different use cases")
    print("- Combine with other tools like terraform validate and security scanning")


if __name__ == "__main__":
    asyncio.run(main())
