#!/usr/bin/env python3
"""
Test client for Merge MCP server (CRM/Linear integration)
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


async def test_merge_mcp():
    """Test the Merge MCP server"""
    
    print("🏢 Testing Merge MCP Server (Real Merge.dev Integration)")
    print("=" * 60)
    
    # Server command (run inside Docker container)
    server_command = [
        "sudo", "docker", "exec", "-i", "mcp-demo-merge-mcp-1", 
        "node", "src/index.js"
    ]
    
    client = MCPClient(server_command)
    
    try:
        # Start MCP connection
        await client.start()
        
        # Test 1: List available tools
        print("\n📋 Listing available Merge tools...")
        tools = await client.list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # Test 2: Check CRM accounts/companies
        print("\n🏢 Listing CRM accounts/companies...")
        result = await client.call_tool("get_crm_accounts", {
            "limit": 5
        })
        
        print("✅ CRM accounts:")
        for content in result["content"]:
            if content["type"] == "text":
                print(f"📋 {content['text']}")
        
        # Test 3: Search existing contacts
        print("\n👥 Searching existing CRM contacts...")
        result = await client.call_tool("search_crm_contacts", {
            "query": "",  # Get all contacts
            "limit": 5
        })
        
        print("✅ Existing contacts:")
        for content in result["content"]:
            if content["type"] == "text":
                print(f"📋 {content['text']}")
        
        # Test 4: Create a new contact (using Merge unified API)
        print("\n👤 Creating a new CRM contact via Merge...")
        
        contact_name = f"MCP Test User {datetime.now().strftime('%H%M%S')}"
        contact_email = f"mcptest{datetime.now().strftime('%H%M%S')}@example.com"
        
        result = await client.call_tool("create_crm_contact", {
            "first_name": "MCP Test",
            "last_name": f"User {datetime.now().strftime('%H%M%S')}",
            "email_addresses": [
                {
                    "email_address": contact_email,
                    "email_address_type": "WORK"
                }
            ]
        })
        
        print("✅ Contact created via Merge unified API!")
        contact_info = None
        for content in result["content"]:
            if content["type"] == "text":
                print(f"📝 {content['text']}")
                # Extract contact ID for next test
                lines = content['text'].split('\n')
                for line in lines:
                    if line.startswith('ID: '):
                        contact_id = line.replace('ID: ', '').strip()
                        contact_info = contact_id
        
        # Test 5: Create opportunity/deal
        if contact_info:
            print("\n💰 Creating a sales opportunity via Merge...")
            
            result = await client.call_tool("create_crm_opportunity", {
                "name": f"MCP Integration Opportunity - {datetime.now().strftime('%Y-%m-%d')}",
                "description": "Potential project for MCP and Merge integration services",
                "amount": 75000,
                "contact": contact_info,
                "stage": "Prospecting"
            })
            
            print("✅ Sales opportunity created via Merge!")
            for content in result["content"]:
                if content["type"] == "text":
                    print(f"💰 {content['text']}")
        
        # Test 6: List recent opportunities
        print("\n📊 Listing recent opportunities...")
        
        result = await client.call_tool("list_crm_opportunities", {
            "limit": 5
        })
        
        print("✅ Recent opportunities:")
        for content in result["content"]:
            if content["type"] == "text":
                print(f"📊 {content['text']}")
        
        print(f"\n🎉 All Merge MCP tests passed!")
        print("🔄 Merge unified API integration working correctly")
        print("🏢 Real CRM operations via Merge.dev")
        print("💰 Opportunity management functional")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        if "MERGE_API_KEY" in str(e) or "MERGE_ACCOUNT_TOKEN" in str(e):
            print("\n💡 Setup required:")
            print("1. Go to https://app.merge.dev/")
            print("2. Create an account and get API keys")
            print("3. Connect a CRM integration (Salesforce, HubSpot, etc.)")
            print("4. Add MERGE_API_KEY and MERGE_ACCOUNT_TOKEN to .env")
        return False
    
    finally:
        await client.close()
    
    return True


async def main():
    """Main test function"""
    
    # Check if container is running
    try:
        result = subprocess.run([
            "sudo", "docker", "ps", "--filter", "name=merge-mcp", "--format", "{{.Names}}"
        ], capture_output=True, text=True, timeout=10)
        
        if "merge-mcp" not in result.stdout:
            print("❌ Merge MCP container is not running")
            print("   Run: sudo docker compose up -d merge-mcp")
            return 1
        
        print("✅ Merge MCP container is running")
        
    except Exception as e:
        print(f"❌ Error checking container status: {e}")
        return 1
    
    # Test health endpoint first
    try:
        result = subprocess.run([
            'curl', '-f', 'http://localhost:8002/health'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            health_data = json.loads(result.stdout)
            print(f"✅ Merge server health: {health_data['status']}")
            print(f"🔄 Merge integration: {health_data.get('integration', 'Unknown')}")
            print(f"🏢 Account ID: {health_data.get('account_id', 'N/A')}")
        else:
            print("❌ Merge server health check failed")
            return 1
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return 1
    
    # Run MCP tests
    success = await test_merge_mcp()
    
    if success:
        print("\n🚀 Next steps:")
        print("  - Merge unified API integration is working correctly")
        print("  - Real CRM operations via Merge.dev functional")
        print("  - Ready to add Slack server")
        print("  - Then build the multi-service orchestrator")
        return 0
    else:
        print("\n🔧 Troubleshooting:")
        print("  - Check container logs: sudo docker logs mcp-demo-merge-mcp-1")
        print("  - Verify MERGE_API_KEY and MERGE_ACCOUNT_TOKEN in .env")
        print("  - Ensure you have a connected CRM integration in Merge")
        print("  - Visit https://app.merge.dev/integrations to set up")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))