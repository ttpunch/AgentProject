import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

class MCPManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPManager, cls).__new__(cls)
            cls._instance.servers = {}
            cls._instance.sessions = {}
            cls._instance.exit_stack = AsyncExitStack()
            cls._instance.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_config.json")
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        """Loads MCP server configuration from JSON file."""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                config = json.load(f)
                self.servers = config.get("mcpServers", {})
        else:
            print(f"Warning: MCP config file not found at {self.config_path}")

    async def connect_to_server(self, server_name: str):
        """Connects to a specific MCP server."""
        if server_name in self.sessions:
            return self.sessions[server_name]

        server_config = self.servers.get(server_name)
        if not server_config:
            raise ValueError(f"Server {server_name} not found in config")

        command = server_config["command"]
        args = server_config["args"]
        env = os.environ.copy()
        
        # Create server parameters
        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env
        )

        try:
            # We need to keep the client context alive
            # Using AsyncExitStack to manage the context managers
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            
            await session.initialize()
            self.sessions[server_name] = session
            print(f"Connected to MCP server: {server_name}")
            return session
        except Exception as e:
            print(f"Failed to connect to {server_name}: {e}")
            return None

    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Lists available tools from a connected server."""
        session = await self.connect_to_server(server_name)
        if not session:
            return []
        
        try:
            result = await session.list_tools()
            return result.tools
        except Exception as e:
            print(f"Error listing tools for {server_name}: {e}")
            return []

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Calls a tool on a specific server."""
        session = await self.connect_to_server(server_name)
        if not session:
            return "Error: Server not connected"
        
        try:
            result = await session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            return f"Error calling tool {tool_name}: {e}"

    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """Aggregates tools from all configured servers."""
        all_tools = []
        for server_name in self.servers:
            tools = await self.list_tools(server_name)
            for tool in tools:
                # Add server_name to tool metadata for routing
                tool_dict = tool.model_dump() if hasattr(tool, 'model_dump') else tool.__dict__
                tool_dict["server_name"] = server_name
                all_tools.append(tool_dict)
        return all_tools

    async def cleanup(self):
        """Closes all sessions."""
        await self.exit_stack.aclose()
        self.sessions.clear()

# Global instance
mcp_manager = MCPManager()
