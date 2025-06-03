#!/usr/bin/env python3
"""
Proper MCP client that communicates with GitHub MCP server via stdio
"""

import asyncio
import json
import subprocess
import sys
import os
from datetime import datetime


class MCPClient:
    def __init__(self, server_command):
        """Initialize MCP client with server command"""
        self.server_command = server_command
        self.process = None
        self.request_id = 0
    
    async def start(self):
        """Start the MCP server process"""
        print(f"🚀 Starting MCP server: {' '.join(self.server_command)}")
        
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy()
        )
        
        # Initialize the connection
        await self.send_initialize()
        
    async def send_initialize(self):
        """Send MCP initialize request"""
        init_request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    }
                },
                "clientInfo": {
                    "name": "mcp-demo-client",
                    "version": "1.0.0"
                }
            }
        }
        
        response = await self.send_request(init_request)
        
        if "error" in response:
            raise Exception(f"Initialize failed: {response['error']}")
            
        print("✅ MCP connection initialized")
        return response
    
    async def send_request(self, request):
        """Send a JSON-RPC request and get response"""
        if not self.process:
            raise Exception("MCP server not started")
        
        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            stderr_output = await self.process.stderr.read()
            raise Exception(f"No response from server. Stderr: {stderr_output.decode()}")
        
        try:
            response = json.loads(response_line.decode().strip())
            return response
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response: {response_line.decode()}")
            raise e
    
    def get_next_id(self):
        """Get next request ID"""
        self.request_id += 1
        return self.request_id
    
    async def list_tools(self):
        """List available tools"""
        request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": "tools/list"
        }
        
        response = await self.send_request(request)
        
        if "error" in response:
            raise Exception(f"List tools failed: {response['error']}")
        
        return response["result"]["tools"]
    
    async def call_tool(self, tool_name, arguments):
        """Call a specific tool"""
        request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = await self.send_request(request)
        
        if "error" in response:
            raise Exception(f"Tool call failed: {response['error']}")
        
        return response["result"]
    
    async def close(self):
        """Close the MCP connection"""
        if self.process:
            self.process.stdin.close()
            await self.process.wait()
            print("🔌 MCP connection closed")


async def test_github_mcp():
    """Test the GitHub MCP server"""
    
    print("🧪 Testing GitHub MCP Server via stdio")
    print("=" * 50)
    
    # Server command (run inside Docker container)
    server_command = [
        "sudo", "docker", "exec", "-i", "mcp-demo-github-mcp-1", 
        "node", "src/index.js"
    ]
    
    client = MCPClient(server_command)
    
    try:
        # Start MCP connection
        await client.start()
        
        # Test 1: List available tools
        print("\n📋 Listing available tools...")
        tools = await client.list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Test 2: Create a test GitHub issue
        print("\n🐛 Creating a test GitHub issue...")
        
        issue_title = f"MCP Test Issue - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        issue_body = """This is a test issue created by the MCP demo client.

**What this tests:**
- MCP client ↔ GitHub MCP server communication
- GitHub API integration via MCP
- Tool calling through Model Context Protocol

**Expected behavior:**
- This issue should appear in the GitHub repository
- The MCP server should return the issue URL
- No errors should occur during creation

If you see this issue, the MCP integration is working correctly! 🎉"""

        result = await client.call_tool("create_github_issue", {
            "title": issue_title,
            "body": issue_body,
            "labels": ["mcp-test", "demo"]
        })
        
        print("✅ GitHub issue created successfully!")
        for content in result["content"]:
            if content["type"] == "text":
                print(f"📝 Result: {content['text']}")
        
        # Test 3: List recent issues
        print("\n📚 Listing recent issues...")
        
        result = await client.call_tool("list_github_issues", {
            "state": "open",
            "limit": 5
        })
        
        print("✅ Recent issues retrieved:")
        for content in result["content"]:
            if content["type"] == "text":
                print(f"📋 {content['text']}")
        
        print(f"\n🎉 All tests passed! Check your repo: https://github.com/Umoren/test-repo/issues")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False
    
    finally:
        await client.close()
    
    return True


async def main():
    """Main test function"""
    
    # Check if container is running
    try:
        result = subprocess.run([
            "sudo", "docker", "ps", "--filter", "name=github-mcp", "--format", "{{.Names}}"
        ], capture_output=True, text=True, timeout=10)
        
        if "github-mcp" not in result.stdout:
            print("❌ GitHub MCP container is not running")
            print("   Run: sudo docker compose up -d")
            return 1
        
        print("✅ GitHub MCP container is running")
        
    except Exception as e:
        print(f"❌ Error checking container status: {e}")
        return 1
    
    # Run MCP tests
    success = await test_github_mcp()
    
    if success:
        print("\n🚀 Next steps:")
        print("  - Check your GitHub repo for the new test issue")
        print("  - The MCP integration is working correctly")
        print("  - Ready to add more servers (Merge, Slack)")
        return 0
    else:
        print("\n🔧 Troubleshooting:")
        print("  - Check container logs: sudo docker logs mcp-demo-github-mcp-1")
        print("  - Verify .env file has correct GITHUB_TOKEN and GITHUB_REPO")
        print("  - Ensure your GitHub token has 'repo' scope")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))