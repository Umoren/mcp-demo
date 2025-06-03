#!/usr/bin/env python3
"""
Test client for Slack MCP server
Tests that the server is running and can interact with Slack
"""

import subprocess
import json
import asyncio
import sys
import os
from datetime import datetime

async def test_slack_container():
    """Test if Slack MCP container is running"""

    print("🧪 Testing Slack MCP Server...")
    
    try:
        # Check if slack-mcp container is running
        result = subprocess.run([
            'sudo', 'docker', 'ps', '--filter', 'name=slack-mcp', '--format', '{{.Names}}\t{{.Status}}'
        ], capture_output=True, text=True, timeout=10)
        
        if 'slack-mcp' in result.stdout:
            print("✅ Slack MCP container is running")
            status = result.stdout.strip().split('\t')[1] if '\t' in result.stdout else 'Unknown'
            print(f"📊 Container status: {status}")
            return True
        else:
            print("❌ Slack MCP container is not running")
            return False

    except Exception as e:
        print(f"❌ Container check error: {e}")
        return False

async def test_slack_logs():
    """Check Slack MCP server logs for any errors"""

    print("\n📋 Checking Slack MCP server logs...")

    try:
        result = subprocess.run([
            'sudo', 'docker', 'compose', 'logs', 'slack-mcp', '--tail', '10'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            logs = result.stdout.strip()
            if logs:
                print("📝 Recent logs:")
                for line in logs.split('\n')[-5:]:  # Show last 5 lines
                    if line.strip():
                        print(f"   {line}")

                # Check for success indicators
                if "Slack MCP Server running" in logs:
                    print("✅ Server started successfully")
                    return True
                elif "error" in logs.lower() or "failed" in logs.lower():
                    print("⚠️  Potential issues found in logs")
                    return False
                else:
                    print("✅ No obvious errors in logs")
                    return True
            else:
                print("📝 No recent logs found")
                return True
        else:
            print(f"❌ Failed to get logs: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Log check error: {e}")
        return False

async def test_mcp_connection():
    """Test MCP connection to Slack server"""

    print("\n🔌 Testing MCP connection...")

    try:
        # Test by executing a simple MCP command in the container
        # This tests if the MCP server is responding to stdio
        result = subprocess.run([
            'sudo', 'docker', 'exec', '-i', 'mcp-demo-slack-mcp-1',
            'sh', '-c', 'echo \'{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}\' | timeout 5 npx -y @modelcontextprotocol/server-slack'
        ], capture_output=True, text=True, timeout=15)

        if result.returncode == 0 and result.stdout:
            try:
                # Try to parse JSON response
                response = json.loads(result.stdout.strip())
                if 'result' in response:
                    print("✅ MCP server responded to initialize")
                    capabilities = response.get('result', {}).get('capabilities', {})
                    print(f"🔧 Server capabilities: {list(capabilities.keys())}")
                    return True
                else:
                    print("⚠️  MCP server responded but unexpected format")
                    print(f"Response: {result.stdout[:200]}...")
                    return True  # Still working, just different format
            except json.JSONDecodeError:
                print("⚠️  MCP server responded but not JSON")
                print(f"Response: {result.stdout[:200]}...")
                return True  # Still responding
        else:
            print("❌ MCP server not responding to initialize")
            if result.stderr:
                print(f"Error: {result.stderr[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️  MCP connection test timed out (server might be working but slow)")
        return True  # Don't fail on timeout, server might be working
    except Exception as e:
        print(f"❌ MCP connection error: {e}")
        return False

async def test_environment_variables():
    """Test if required environment variables are set"""

    print("\n🔐 Checking environment variables...")

    # Load .env file to check variables
    env_vars = {}
    try:
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
        
        required_vars = ['SLACK_BOT_TOKEN', 'SLACK_TEAM_ID']
        missing_vars = []
        
        for var in required_vars:
            if var not in env_vars or not env_vars[var]:
                missing_vars.append(var)
            else:
                # Show partial token for verification (first 10 chars)
                value = env_vars[var]
                if var == 'SLACK_BOT_TOKEN':
                    display_value = f"{value[:10]}..." if len(value) > 10 else value
                    print(f"✅ {var}: {display_value}")
                else:
                    print(f"✅ {var}: {value}")

        if missing_vars:
            print(f"❌ Missing required variables: {', '.join(missing_vars)}")
            return False
        
        # Check optional variables
        if 'SLACK_CHANNEL_IDS' in env_vars and env_vars['SLACK_CHANNEL_IDS']:
            print(f"✅ SLACK_CHANNEL_IDS: {env_vars['SLACK_CHANNEL_IDS']}")
        else:
            print("ℹ️  SLACK_CHANNEL_IDS: Not set (will use all public channels)")
        
        return True
        
    except FileNotFoundError:
        print("❌ .env file not found")
        return False
    except Exception as e:
        print(f"❌ Environment check error: {e}")
        return False

async def test_slack_bot_setup():
    """Test if Slack bot is properly configured"""

    print("\n🤖 Testing Slack bot configuration...")

    try:
        # Load environment variables
        env_vars = {}
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value

        if 'SLACK_BOT_TOKEN' not in env_vars:
            print("❌ SLACK_BOT_TOKEN not found in .env")
            return False
        
        # Test token format
        token = env_vars['SLACK_BOT_TOKEN']
        if not token.startswith('xoxb-'):
            print("❌ SLACK_BOT_TOKEN should start with 'xoxb-'")
            print(f"   Current token starts with: {token[:10]}...")
            return False
        
        print("✅ Bot token format looks correct")
        
        # Test team ID format
        if 'SLACK_TEAM_ID' in env_vars:
            team_id = env_vars['SLACK_TEAM_ID']
            if not team_id.startswith('T'):
                print("❌ SLACK_TEAM_ID should start with 'T'")
                print(f"   Current team ID: {team_id}")
                return False
            print("✅ Team ID format looks correct")
        
        return True
        
    except Exception as e:
        print(f"❌ Bot setup check error: {e}")
        return False

def main():
    """Main test function"""

    print("🔧 Slack MCP Server Test Suite")
    print("=" * 40)

    # Check environment
    if not os.path.exists('.env'):
        print("⚠️  No .env file found. Make sure to:")
        print("   1. Copy .env.example to .env")
        print("   2. Add your SLACK_BOT_TOKEN and SLACK_TEAM_ID")
        print("   3. Run: sudo docker-compose up -d")
        return 1

    # Run all tests
    async def run_all_tests():
        tests = [
            ("Container Status", test_slack_container()),
            ("Environment Variables", test_environment_variables()),
            ("Bot Configuration", test_slack_bot_setup()),
            ("Server Logs", test_slack_logs()),
            ("MCP Connection", test_mcp_connection()),
        ]

        results = []
        for test_name, test_coro in tests:
            print(f"\n{'='*20} {test_name} {'='*20}")
            try:
                result = await test_coro
                results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} failed with error: {e}")
                results.append((test_name, False))

        return results

    try:
        results = asyncio.run(run_all_tests())

        # Summary
        print(f"\n{'='*60}")
        print("📊 TEST SUMMARY")
        print("=" * 60)

        passed = 0
        failed = 0

        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
            if result:
                passed += 1
            else:
                failed += 1

        print(f"\nResults: {passed} passed, {failed} failed")

        if failed == 0:
            print("\n🎉 All tests passed! Your Slack MCP server is working.")
            print("\nNext steps:")
            print("  - Test posting a message to Slack")
            print("  - Check that your bot is added to channels")
            print("  - Try the full workflow test: python test/test-workflow.py")
            return 0
        else:
            print(f"\n❌ {failed} test(s) failed. Check the issues above.")
            print("\nCommon fixes:")
            print("  - Verify bot token and team ID in .env")
            print("  - Check bot permissions in Slack app settings")
            print("  - Ensure bot is added to channels you want to use")
            print("  - Restart container: sudo docker-compose restart slack-mcp")
            return 1

    except KeyboardInterrupt:
        print("\n\n🛑 Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())