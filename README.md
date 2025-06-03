# MCP Integration Demo

A production-ready demonstration of the Model Context Protocol (MCP) implementing a multi-service workflow architecture. This repository showcases standardized AI-tool integration patterns using GitHub, Slack, and CRM systems.

## Overview

The Model Context Protocol (MCP) is an open standard for connecting AI systems to external tools and data sources. This demo implements a realistic development workflow where bug reports trigger automated actions across multiple business systems:

**Workflow:** Bug Report → GitHub Issue → CRM Deal → Slack Notification

## Architecture

The demo consists of three MCP servers running in Docker containers, each exposing standardized tools via JSON-RPC:

- **GitHub MCP Server** - Issue creation and repository management
- **Slack MCP Server** - Team notifications and channel management
- **Merge MCP Server** - CRM integration with 220+ business systems

Each server implements the MCP specification, providing tools, resources, and prompts that AI clients can discover and invoke programmatically.

## Components

### GitHub Integration
Provides repository management capabilities including issue creation, listing, and retrieval. Implements OAuth token authentication with granular scope controls.

**Available Tools:**
- `create_github_issue` - Create new repository issues
- `list_github_issues` - Retrieve existing issues with filtering
- `get_github_issue` - Fetch detailed issue information

### Slack Integration
Enables team communication through the official Slack MCP server implementation. Supports channel management, message posting, and user directory access.

**Available Tools:**
- `slack_post_message` - Send messages to channels
- `slack_list_channels` - Enumerate workspace channels
- `slack_get_users` - Access user directory
- `slack_add_reaction` - React to messages
- `slack_get_channel_history` - Retrieve message history

### CRM Integration
Utilizes Merge's unified API platform to provide standardized access to customer relationship management systems through a single MCP interface.

**Available Tools:**
- `create_deal` - Generate sales opportunities
- `create_contact` - Add customer records
- `list_deals` - Query existing opportunities
- `get_deal` - Retrieve deal details

## Installation

### Prerequisites
- Docker and Docker Compose
- Python 3.8+ (for testing clients)
- Access tokens for GitHub, Slack, and Merge services

### Environment Setup

1. Clone the repository and configure environment variables:

```bash
git clone <repository-url>
cd mcp-demo
cp .env.example .env
```

2. Configure service credentials in `.env`:

```bash
# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REPO=username/repository-name

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
SLACK_TEAM_ID=T0XXXXXXXXX
SLACK_CHANNEL_IDS=C0XXXXXXXXX,C0YYYYYYYYY

# Merge Configuration
MERGE_API_KEY=your_merge_api_key
MERGE_ACCOUNT_TOKEN=your_account_token
```

### Service Deployment

Deploy all MCP servers using Docker Compose:

```bash
docker-compose up -d
```

Verify deployment status:

```bash
# Check container status
docker-compose ps

# Verify health endpoints
curl http://localhost:8001/health  # GitHub MCP
curl http://localhost:8002/health  # Slack MCP
curl http://localhost:8003/health  # Merge MCP
```

## Testing

### Individual Server Testing

Test each MCP server independently:

```bash
# GitHub MCP Server
python test/test-github.py

# Slack MCP Server
python test/test-slack.py

# Merge MCP Server
python test/test-merge.py
```

### End-to-End Workflow

Execute the complete multi-service workflow:

```bash
python test/test-workflow.py
```

This demonstrates:
1. Creating a GitHub issue from a bug report
2. Generating a CRM deal linked to the issue
3. Sending team notification via Slack
4. Performance metrics collection

## Configuration

### GitHub Setup
1. Generate a personal access token at https://github.com/settings/tokens
2. Grant `repo` scope for full repository access
3. Ensure token has access to the target repository

### Slack Setup
1. Create a Slack app at https://api.slack.com/apps
2. Configure bot token scopes: `channels:read`, `channels:history`, `chat:write`, `users:read`
3. Install app to workspace and copy bot token
4. Add bot to required channels using `/invite @botname`

### Merge Setup
1. Register at https://merge.dev and obtain API credentials
2. Configure account tokens for target CRM systems
3. Map required data fields through Merge dashboard

## Development

### Adding New Tools

Extend MCP servers by implementing additional tools:

```javascript
// Example: Add new GitHub tool
server.setRequestHandler(ListToolsRequestSchema, async (request) => {
  return {
    tools: [
      // Existing tools...
      {
        name: "create_github_pr",
        description: "Create a pull request",
        inputSchema: {
          type: "object",
          properties: {
            title: { type: "string" },
            body: { type: "string" },
            head: { type: "string" },
            base: { type: "string" }
          }
        }
      }
    ]
  };
});
```

### Performance Monitoring

The demo includes benchmarking capabilities to measure:
- Tool invocation latency
- Memory usage patterns
- Network request overhead
- Token consumption rates

## File Structure

```
mcp-demo/
├── docker-compose.yml           # Container orchestration
├── .env.example                # Environment template
├── servers/
│   ├── github-mcp/             # GitHub MCP server
│   │   ├── Dockerfile
│   │   ├── package.json
│   │   └── src/index.js
│   ├── slack-mcp/              # Slack MCP server config
│   └── merge-mcp/              # Merge MCP server config
├── test/
│   ├── test-github.py          # GitHub integration tests
│   ├── test-slack.py           # Slack integration tests
│   ├── test-merge.py           # Merge integration tests
│   └── test-workflow.py        # End-to-end workflow tests
└── docs/
    ├── api-reference.md        # MCP API documentation
    ├── security.md             # Security considerations
    └── performance.md          # Performance benchmarks
```

## Security Considerations

- All service tokens are managed through environment variables
- MCP servers run in isolated Docker containers
- Network communications use TLS encryption
- Scope-limited API tokens minimize attack surface
- Input validation implemented across all tool endpoints

## Contributing

This repository demonstrates MCP integration patterns for educational and development purposes. Contributions should focus on:

- Additional MCP server implementations
- Performance optimization examples
- Security best practices
- Documentation improvements

## License

MIT License - see LICENSE file for details.