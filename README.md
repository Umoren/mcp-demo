# MCP Demo - Basic GitHub Integration

A working example of MCP (Model Context Protocol) with GitHub integration.

## Quick Start

### 1. Setup Environment

```bash
# Clone or create the project directory
mkdir mcp-demo && cd mcp-demo

# Copy the .env.example to .env
cp .env.example .env
```

### 2. Configure GitHub

Edit `.env` and add:
- **GITHUB_TOKEN**: Personal access token with `repo` scope
- **GITHUB_REPO**: Repository in format `username/repo-name`

```bash
# Get GitHub token: https://github.com/settings/tokens
# Create a test repo or use existing one

# Example .env:
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REPO=yourusername/test-repo
```

### 3. Start the Server

```bash
# Build and start the GitHub MCP server
docker-compose up -d

# Check if it's running
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "github-mcp-server",
  "repo": "yourusername/test-repo",
  "timestamp": "2025-01-XX..."
}
```

### 4. Test the Integration

```bash
# Run the test suite
python test/test-github.py
```

Expected output:
```
🧪 Testing GitHub MCP Server...
✅ Server health check passed: healthy
📁 Connected to repo: yourusername/test-repo
✅ Found 3 available tools
  - create_github_issue: Create a new GitHub issue
  - list_github_issues: List issues from the repository
  - get_github_issue: Get details of a specific issue

🎯 All tests passed! GitHub MCP server is working correctly.
```

## What's Working

- ✅ GitHub MCP server running in Docker
- ✅ Health check endpoint
- ✅ Three GitHub tools available via MCP
- ✅ Connection to your GitHub repository verified

## Available Tools

1. **create_github_issue** - Create new issues
2. **list_github_issues** - List existing issues
3. **get_github_issue** - Get issue details

## Troubleshooting

### Server won't start
```bash
# Check logs
docker-compose logs github-mcp

# Common issues:
# - Invalid GITHUB_TOKEN
# - Repository doesn't exist or no access
# - Port 8001 already in use
```

### Health check fails
```bash
# Test manually
curl -v http://localhost:8001/health

# Check if container is running
docker-compose ps
```

### GitHub API errors
```bash
# Test your token manually
curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/repos/yourusername/test-repo
```

## Next Steps

Once this is working, we'll add:
- [ ] Merge MCP server (for CRM/Linear integration)
- [ ] Slack MCP server (for notifications)
- [ ] Python client that uses all three
- [ ] LangChain comparison implementation
- [ ] Performance benchmarks

## File Structure

```
mcp-demo/
├── docker-compose.yml          # Docker setup
├── .env.example               # Environment template
├── servers/github-mcp/        # GitHub MCP server code
│   ├── Dockerfile
│   ├── package.json
│   └── src/index.js
└── test/test-github.py        # Test client
```