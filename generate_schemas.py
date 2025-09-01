#!/usr/bin/env python3
"""
Manual AzAPI Schema Generator

This script can be used to manually generate AzAPI schemas for testing or maintenance.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add src to path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tf_mcp_server.core.azapi_schema_generator import AzAPISchemaGenerator


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Generate AzAPI schemas")
    parser.add_argument(
        "--tag", 
        default="latest", 
        help="GitHub release tag to use (default: latest)"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force regeneration even if schemas exist"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger.info("Verbose logging enabled")
    
    if args.force:
        logger.info("Force regeneration requested")
    
    try:
        generator = AzAPISchemaGenerator()
        
        if args.force:
            # Force regeneration
            schemas = await generator.generate_schemas(args.tag)
        else:
            # Use smart loading/generation with version checking
            schemas = await generator.load_or_generate_schemas()
        
        logger.info(f"Successfully processed {len(schemas)} schemas")
        
        # Print a sample schema if verbose
        if args.verbose and schemas:
            sample_key = next(iter(schemas.keys()))
            sample_schema = schemas[sample_key]
            logger.info(f"Sample schema for {sample_key}:")
            print("=" * 50)
            print(sample_schema[:1000] + "..." if len(sample_schema) > 1000 else sample_schema)
            print("=" * 50)
        
    except Exception as e:
        logger.error(f"Failed to generate schemas: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    sys.exit(asyncio.run(main()))
