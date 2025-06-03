#!/usr/bin/env python3
"""
Standalone Slack MCP test that manages its own container
"""

import asyncio
import json
import subprocess
import sys
import os
from datetime import datetime


class MCPClient:
    def __init__(self, server_command):
        self.server_command = server_command
        self.process = None
        self.request_id = 0
    
    async def start(self):
        print(f"🚀 Starting MCP server...")
        
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy()
        )

        await self.send_initialize()

    async def send_initialize(self):
        init_request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"roots": {"listChanged": True}},
                "clientInfo": {"name": "slack-test-client", "version": "1.0.0"}
            }
        }

        response = await self.send_request(init_request)
        if "error" in response:
            raise Exception(f"Initialize failed: {response['error']}")
        print("✅ MCP connection initialized")
        return response

    async def send_request(self, request):
        if not self.process:
            raise Exception("MCP server not started")

        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        response_line = await self.process.stdout.readline()
        if not response_line:
            stderr_output = await self.process.stderr.read()
            raise Exception(f"No response from server. Stderr: {stderr_output.decode()}")

        return json.loads(response_line.decode().strip())

    def get_next_id(self):
        self.request_id += 1
        return self.request_id

    async def list_tools(self):
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
        request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }

        response = await self.send_request(request)
        if "error" in response:
            raise Exception(f"Tool call failed: {response['error']}")
        return response["result"]

    async def close(self):
        if self.process:
            self.process.stdin.close()
            await self.process.wait()
            print("🔌 MCP connection closed")


async def test_slack_mcp():
    print("🔧 Slack MCP Server Standalone Test")
    print("=" * 50)

    # Stop any running Slack container first
    print("🛑 Stopping any existing Slack MCP containers...")
    subprocess.run([
        "sudo", "docker", "compose", "stop", "slack-mcp"
    ], capture_output=True)

    # Use fresh container for testing
    server_command = [
        "sudo", "docker", "run", "--rm", "-i",
        "--env-file", ".env",
        "node:18-alpine",
        "sh", "-c", "npx -y @modelcontextprotocol/server-slack"
    ]

    client = MCPClient(server_command)

    try:
        await client.start()
        
        # Test 1: List tools
        print("\n📋 Listing available tools...")
        tools = await client.list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

        # Test 2: List channels first
        print("\n📝 Listing available channels...")
        try:
            channels_result = await client.call_tool("slack_list_channels", {"limit": 5})
            print("✅ Channels:")
            for content in channels_result["content"]:
                if content["type"] == "text":
                    print(f"📋 {content['text']}")
        except Exception as e:
            print(f"❌ List channels failed: {e}")
            return False

        # Test 3: Test environment setup
        print("\n🔐 Testing environment variables...")
        env_vars = {}
        try:
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
            
            # Check required variables
            if 'SLACK_BOT_TOKEN' not in env_vars:
                print("❌ SLACK_BOT_TOKEN missing from .env")
                return False
            if 'SLACK_TEAM_ID' not in env_vars:
                print("❌ SLACK_TEAM_ID missing from .env")
                return False

            token = env_vars['SLACK_BOT_TOKEN']
            team_id = env_vars['SLACK_TEAM_ID']
            
            if not token.startswith('xoxb-'):
                print(f"❌ Bot token should start with 'xoxb-', got: {token[:10]}...")
                return False
            if not team_id.startswith('T'):
                print(f"❌ Team ID should start with 'T', got: {team_id}")
                return False

            print(f"✅ Bot token: {token[:15]}...")
            print(f"✅ Team ID: {team_id}")

        except Exception as e:
            print(f"❌ Environment check failed: {e}")
            return False
        
        # Test 4: Try to post a test message
        print("\n🆕 Testing message posting...")
        
        test_message = f"""🧪 **Slack MCP Test Message**

This is an automated test from the MCP Slack server.

**Test Details:**
- Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Server: Slack MCP via stdio transport
- Client: Python test script

**Status:** ✅ Connection working!

This message confirms that the Slack MCP integration is functional.
"""
        
        # Use the channel from your env or default test channel
        test_channel = env_vars.get('SLACK_CHANNEL_IDS', 'C08V5PY7TEZ').split(',')[0].strip()

        try:
            result = await client.call_tool("slack_post_message", {
                "channel_id": test_channel,
                "text": test_message
            })

            print("✅ Message posted successfully!")
            for content in result["content"]:
                if content["type"] == "text":
                    print(f"📝 {content['text']}")

        except Exception as e:
            print(f"❌ Message posting failed: {e}")
            print(f"   Channel used: {test_channel}")
            print("   Check:")
            print("   - Bot is added to the channel")
            print("   - Bot has 'chat:write' permission")
            print("   - Channel ID is correct")
            return False
        
        print("\n🎉 All Slack MCP tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        
        # Debug information
        print("\n🔍 Debug Information:")
        print("1. Check your .env file has:")
        print("   SLACK_BOT_TOKEN=xoxb-...")
        print("   SLACK_TEAM_ID=T...")
        print("   SLACK_CHANNEL_IDS=C...")
        print("")
        print("2. Verify Slack app permissions:")
        print("   - channels:read")
        print("   - chat:write")
        print("   - channels:history")
        print("")
        print("3. Ensure bot is added to test channel")
        
        return False

    finally:
        await client.close()

        # Restart the original container
        print("🔄 Restarting Slack MCP service...")
        subprocess.run([
            "sudo", "docker", "compose", "up", "-d", "slack-mcp"
        ], capture_output=True)


async def main():
    success = await test_slack_mcp()

    if success:
        print("\n🚀 Slack MCP server is working perfectly!")
        print("✅ Ready for full workflow testing")
        return 0
    else:
        print("\n🔧 Slack MCP has issues. Common fixes:")
        print("  1. Check bot token and permissions in Slack")
        print("  2. Verify bot is added to target channels")
        print("  3. Confirm environment variables in .env")
        print("  4. Test manually: https://api.slack.com/methods/chat.postMessage/test")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))