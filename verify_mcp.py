import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.mcp_manager import mcp_manager

async def main():
    print("--- Verifying MCP Integration ---")
    
    # 1. Load Config
    print("Loading config...")
    mcp_manager.load_config()
    print(f"Configured servers: {list(mcp_manager.servers.keys())}")
    
    # 2. List Tools
    print("\nListing tools...")
    tools = await mcp_manager.get_all_tools()
    
    if not tools:
        print("No tools found. Check connection or config.")
    else:
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"- {tool['name']} (Server: {tool['server_name']})")
            
    # 3. Cleanup
    await mcp_manager.cleanup()
    print("\nVerification Complete.")

if __name__ == "__main__":
    asyncio.run(main())
