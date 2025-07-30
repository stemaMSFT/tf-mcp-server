#!/usr/bin/env python3
"""
Main entry point for Azure Terraform MCP Server.
"""

import asyncio
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import Config
from core.server import run_server


async def main():
    """Main entry point."""
    # Load environment variables from .env.local file
    env_file = Path(__file__).parent / ".env.local"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    else:
        print(f"Environment file {env_file} not found, using system environment variables")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('tf-mcp-server.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration from environment
        config = Config.from_env()
        
        logger.info("Starting Azure Terraform MCP Server")
        logger.info(f"Configuration: Host={config.server.host}, Port={config.server.port}")
        
        # Run the server
        await run_server(config)
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
