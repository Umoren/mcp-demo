import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { Octokit } from '@octokit/rest';
import express from 'express';
import cors from 'cors';

// Logging helper - MCP servers must use stderr for logs, stdout for JSON-RPC
function log(message) {
    console.error(message);
}

function logError(message) {
    console.error(message);
}
const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const GITHUB_REPO = process.env.GITHUB_REPO;
const PORT = process.env.PORT || 8001;
const LOG_LEVEL = process.env.LOG_LEVEL || 'info';

if (!GITHUB_TOKEN) {
    console.error('GITHUB_TOKEN environment variable is required');
    process.exit(1);
}

if (!GITHUB_REPO) {
    console.error('GITHUB_REPO environment variable is required (format: owner/repo)');
    process.exit(1);
}

// Parse repo owner and name
const [owner, repo] = GITHUB_REPO.split('/');
if (!owner || !repo) {
    logError('GITHUB_REPO must be in format "owner/repo"');
    process.exit(1);
}

// Initialize GitHub client
const octokit = new Octokit({
    auth: GITHUB_TOKEN,
});

// Verify GitHub connection
async function verifyGitHubConnection() {
    try {
        const { data } = await octokit.rest.repos.get({ owner, repo });
        log(`✅ Connected to GitHub repo: ${data.full_name}`);
        return true;
    } catch (error) {
        logError('❌ Failed to connect to GitHub:', error.message);
        return false;
    }
}

// MCP Server setup
const server = new Server(
    {
        name: 'github-mcp-server',
        version: '1.0.0',
    },
    {
        capabilities: {
            tools: {},
        },
    }
);

// Define available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: 'create_github_issue',
                description: 'Create a new GitHub issue in the configured repository',
                inputSchema: {
                    type: 'object',
                    properties: {
                        title: {
                            type: 'string',
                            description: 'The title of the issue',
                        },
                        body: {
                            type: 'string',
                            description: 'The body/description of the issue',
                        },
                        labels: {
                            type: 'array',
                            items: { type: 'string' },
                            description: 'Optional array of label names to apply',
                        },
                        assignees: {
                            type: 'array',
                            items: { type: 'string' },
                            description: 'Optional array of usernames to assign',
                        },
                    },
                    required: ['title'],
                },
            },
            {
                name: 'list_github_issues',
                description: 'List issues from the GitHub repository',
                inputSchema: {
                    type: 'object',
                    properties: {
                        state: {
                            type: 'string',
                            enum: ['open', 'closed', 'all'],
                            description: 'Filter issues by state',
                            default: 'open',
                        },
                        labels: {
                            type: 'string',
                            description: 'Comma-separated list of label names to filter by',
                        },
                        limit: {
                            type: 'number',
                            description: 'Maximum number of issues to return',
                            default: 10,
                            maximum: 100,
                        },
                    },
                },
            },
            {
                name: 'get_github_issue',
                description: 'Get details of a specific GitHub issue',
                inputSchema: {
                    type: 'object',
                    properties: {
                        issue_number: {
                            type: 'number',
                            description: 'The issue number',
                        },
                    },
                    required: ['issue_number'],
                },
            },
        ],
    };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    try {
        switch (name) {
            case 'create_github_issue': {
                const { title, body, labels, assignees } = args;

                const issueData = {
                    owner,
                    repo,
                    title,
                    body: body || '',
                };

                if (labels && labels.length > 0) {
                    issueData.labels = labels;
                }

                if (assignees && assignees.length > 0) {
                    issueData.assignees = assignees;
                }

                const { data: issue } = await octokit.rest.issues.create(issueData);

                return {
                    content: [
                        {
                            type: 'text',
                            text: `Successfully created GitHub issue #${issue.number}: "${issue.title}"\nURL: ${issue.html_url}\nState: ${issue.state}`,
                        },
                    ],
                };
            }

            case 'list_github_issues': {
                const { state = 'open', labels, limit = 10 } = args;

                const params = {
                    owner,
                    repo,
                    state,
                    per_page: Math.min(limit, 100),
                };

                if (labels) {
                    params.labels = labels;
                }

                const { data: issues } = await octokit.rest.issues.list(params);

                const issueList = issues.map(issue => ({
                    number: issue.number,
                    title: issue.title,
                    state: issue.state,
                    url: issue.html_url,
                    created_at: issue.created_at,
                    labels: issue.labels.map(label => label.name),
                }));

                return {
                    content: [
                        {
                            type: 'text',
                            text: `Found ${issues.length} issues:\n\n` +
                                issueList.map(issue =>
                                    `#${issue.number}: ${issue.title} (${issue.state})\n  ${issue.url}`
                                ).join('\n\n'),
                        },
                    ],
                };
            }

            case 'get_github_issue': {
                const { issue_number } = args;

                const { data: issue } = await octokit.rest.issues.get({
                    owner,
                    repo,
                    issue_number,
                });

                return {
                    content: [
                        {
                            type: 'text',
                            text: `Issue #${issue.number}: ${issue.title}\n\n` +
                                `State: ${issue.state}\n` +
                                `Created: ${issue.created_at}\n` +
                                `Updated: ${issue.updated_at}\n` +
                                `URL: ${issue.html_url}\n\n` +
                                `Body:\n${issue.body || 'No description provided.'}`,
                        },
                    ],
                };
            }

            default:
                throw new Error(`Unknown tool: ${name}`);
        }
    } catch (error) {
        logError(`Error executing tool ${name}:`, error);

        return {
            content: [
                {
                    type: 'text',
                    text: `Error: ${error.message}`,
                },
            ],
            isError: true,
        };
    }
});

// Health check HTTP server (for Docker healthcheck)
const app = express();
app.use(cors());

app.get('/health', async (req, res) => {
    try {
        // Quick GitHub API test
        await octokit.rest.repos.get({ owner, repo });
        res.json({
            status: 'healthy',
            service: 'github-mcp-server',
            repo: `${owner}/${repo}`,
            timestamp: new Date().toISOString()
        });
    } catch (error) {
        res.status(503).json({
            status: 'unhealthy',
            error: error.message,
            timestamp: new Date().toISOString()
        });
    }
});

app.get('/info', (req, res) => {
    res.json({
        service: 'github-mcp-server',
        version: '1.0.0',
        repo: `${owner}/${repo}`,
        mcp_protocol: '2024-11-05',
        note: 'This server communicates via stdio, not HTTP. Use a proper MCP client.'
    });
});

// Start servers
async function start() {
    log('🚀 Starting GitHub MCP Server...');

    // Verify GitHub connection first
    const connected = await verifyGitHubConnection();
    if (!connected) {
        logError('Failed to connect to GitHub. Check your token and repo settings.');
        process.exit(1);
    }

    // Start HTTP server for health checks
    app.listen(PORT, () => {
        log(`🌐 Health check server running on port ${PORT}`);
        log(`📋 Repository: ${owner}/${repo}`);
        log(`🔧 Available at: http://localhost:${PORT}/health`);
    });

    // Start MCP server on stdio
    const transport = new StdioServerTransport();
    await server.connect(transport);
    log('📡 MCP Server connected via stdio');
}

// Error handling
process.on('SIGINT', async () => {
    log('\n🛑 Shutting down GitHub MCP Server...');
    await server.close();
    process.exit(0);
});

process.on('unhandledRejection', (reason, promise) => {
    logError('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Start the server
start().catch(logError);