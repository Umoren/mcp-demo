#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import express from 'express';
import cors from 'cors';

// Logging helper - MCP servers must use stderr for logs, stdout for JSON-RPC
function log(message) {
    console.error(message);
}

function logError(message) {
    console.error(message);
}

// Environment variables
const MERGE_API_KEY = process.env.MERGE_API_KEY;
const MERGE_ACCOUNT_TOKEN = process.env.MERGE_ACCOUNT_TOKEN;
const PORT = process.env.PORT || 8002;
const LOG_LEVEL = process.env.LOG_LEVEL || 'info';

if (!MERGE_API_KEY) {
    logError('MERGE_API_KEY environment variable is required');
    logError('Get your API key from: https://app.merge.dev/keys');
    process.exit(1);
}

if (!MERGE_ACCOUNT_TOKEN) {
    logError('MERGE_ACCOUNT_TOKEN environment variable is required');
    logError('This connects to your specific CRM integration (Salesforce, HubSpot, etc.)');
    process.exit(1);
}

// Merge API client
class MergeAPIClient {
    constructor(apiKey, accountToken) {
        this.apiKey = apiKey;
        this.accountToken = accountToken;
        this.baseURL = 'https://api.merge.dev/api';
    }

    async makeRequest(endpoint, method = 'GET', data = null) {
        const url = `${this.baseURL}${endpoint}`;

        const headers = {
            'Authorization': `Bearer ${this.apiKey}`,
            'X-Account-Token': this.accountToken,
            'Content-Type': 'application/json',
            'User-Agent': 'MCP-Demo/1.0.0'
        };

        const options = {
            method,
            headers
        };

        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(url, options);

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Merge API error ${response.status}: ${errorText}`);
            }

            return await response.json();
        } catch (error) {
            logError(`Merge API request failed: ${error.message}`);
            throw error;
        }
    }

    // CRM Contacts
    async getContacts(cursor = null, pageSize = 20) {
        let endpoint = `/crm/v1/contacts?page_size=${pageSize}`;
        if (cursor) {
            endpoint += `&cursor=${cursor}`;
        }
        return await this.makeRequest(endpoint);
    }

    async createContact(contactData) {
        return await this.makeRequest('/crm/v1/contacts', 'POST', {
            model: contactData
        });
    }

    async getContact(contactId) {
        return await this.makeRequest(`/crm/v1/contacts/${contactId}`);
    }

    async updateContact(contactId, updates) {
        return await this.makeRequest(`/crm/v1/contacts/${contactId}`, 'PATCH', {
            model: updates
        });
    }

    // CRM Opportunities (Deals)
    async getOpportunities(cursor = null, pageSize = 20) {
        let endpoint = `/crm/v1/opportunities?page_size=${pageSize}`;
        if (cursor) {
            endpoint += `&cursor=${cursor}`;
        }
        return await this.makeRequest(endpoint);
    }

    async createOpportunity(opportunityData) {
        return await this.makeRequest('/crm/v1/opportunities', 'POST', {
            model: opportunityData
        });
    }

    // CRM Accounts (Companies)
    async getAccounts(cursor = null, pageSize = 20) {
        let endpoint = `/crm/v1/accounts?page_size=${pageSize}`;
        if (cursor) {
            endpoint += `&cursor=${cursor}`;
        }
        return await this.makeRequest(endpoint);
    }

    async createAccount(accountData) {
        return await this.makeRequest('/crm/v1/accounts', 'POST', {
            model: accountData
        });
    }

    // Get integration info
    async getAccountDetails() {
        return await this.makeRequest('/crm/v1/account-details');
    }

    // Search across CRM
    async searchCRM(query) {
        return await this.makeRequest('/crm/v1/contacts', 'GET').then(response => {
            // Simple client-side filtering for demo
            // In production, use Merge's search endpoints when available
            if (!query) return response;

            const searchTerm = query.toLowerCase();
            const filteredResults = response.results?.filter(contact =>
                contact.first_name?.toLowerCase().includes(searchTerm) ||
                contact.last_name?.toLowerCase().includes(searchTerm) ||
                contact.email_addresses?.some(email =>
                    email.email_address?.toLowerCase().includes(searchTerm)
                )
            ) || [];

            return { ...response, results: filteredResults };
        });
    }
}

// Initialize Merge client
const mergeClient = new MergeAPIClient(MERGE_API_KEY, MERGE_ACCOUNT_TOKEN);

// Verify Merge connection
async function verifyMergeConnection() {
    try {
        const accountDetails = await mergeClient.getAccountDetails();
        log(`✅ Connected to Merge CRM integration`);
        log(`🏢 Provider: ${accountDetails.integration?.name || 'Unknown'}`);
        log(`📋 Account: ${accountDetails.id}`);
        return true;
    } catch (error) {
        logError('❌ Failed to connect to Merge:', error.message);
        logError('💡 Check your MERGE_API_KEY and MERGE_ACCOUNT_TOKEN');
        logError('🔗 Get tokens from: https://app.merge.dev/');
        return false;
    }
}

// MCP Server setup
const server = new Server(
    {
        name: 'merge-mcp-server',
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
                name: 'create_crm_contact',
                description: 'Create a new contact in your CRM via Merge unified API',
                inputSchema: {
                    type: 'object',
                    properties: {
                        first_name: {
                            type: 'string',
                            description: 'First name',
                        },
                        last_name: {
                            type: 'string',
                            description: 'Last name',
                        },
                        email_addresses: {
                            type: 'array',
                            items: {
                                type: 'object',
                                properties: {
                                    email_address: { type: 'string' },
                                    email_address_type: {
                                        type: 'string',
                                        enum: ['PERSONAL', 'WORK', 'OTHER'],
                                        default: 'WORK'
                                    }
                                }
                            },
                            description: 'Email addresses'
                        },
                        phone_numbers: {
                            type: 'array',
                            items: {
                                type: 'object',
                                properties: {
                                    phone_number: { type: 'string' },
                                    phone_number_type: {
                                        type: 'string',
                                        enum: ['HOME', 'WORK', 'MOBILE', 'OTHER'],
                                        default: 'WORK'
                                    }
                                }
                            },
                            description: 'Phone numbers'
                        },
                        account: {
                            type: 'string',
                            description: 'Company/Account ID to associate with'
                        }
                    },
                    required: ['first_name', 'last_name'],
                },
            },
            {
                name: 'search_crm_contacts',
                description: 'Search for contacts in your CRM via Merge',
                inputSchema: {
                    type: 'object',
                    properties: {
                        query: {
                            type: 'string',
                            description: 'Search term (name or email)',
                        },
                        limit: {
                            type: 'number',
                            description: 'Maximum number of results',
                            default: 10,
                            maximum: 100,
                        },
                    },
                },
            },
            {
                name: 'get_crm_contact',
                description: 'Get detailed information about a specific CRM contact',
                inputSchema: {
                    type: 'object',
                    properties: {
                        contact_id: {
                            type: 'string',
                            description: 'The Merge contact ID',
                        },
                    },
                    required: ['contact_id'],
                },
            },
            {
                name: 'create_crm_opportunity',
                description: 'Create a new sales opportunity/deal in your CRM via Merge',
                inputSchema: {
                    type: 'object',
                    properties: {
                        name: {
                            type: 'string',
                            description: 'Opportunity name',
                        },
                        description: {
                            type: 'string',
                            description: 'Opportunity description',
                        },
                        amount: {
                            type: 'number',
                            description: 'Deal amount/value',
                        },
                        contact: {
                            type: 'string',
                            description: 'Contact ID to associate with this opportunity',
                        },
                        account: {
                            type: 'string',
                            description: 'Account/Company ID',
                        },
                        stage: {
                            type: 'string',
                            description: 'Sales stage/status',
                        },
                    },
                    required: ['name'],
                },
            },
            {
                name: 'list_crm_opportunities',
                description: 'List recent opportunities/deals from your CRM',
                inputSchema: {
                    type: 'object',
                    properties: {
                        limit: {
                            type: 'number',
                            description: 'Maximum number of results',
                            default: 10,
                            maximum: 100,
                        },
                    },
                },
            },
            {
                name: 'get_crm_accounts',
                description: 'List companies/accounts from your CRM via Merge',
                inputSchema: {
                    type: 'object',
                    properties: {
                        limit: {
                            type: 'number',
                            description: 'Maximum number of results',
                            default: 10,
                            maximum: 100,
                        },
                    },
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
            case 'create_crm_contact': {
                const result = await mergeClient.createContact(args);

                return {
                    content: [
                        {
                            type: 'text',
                            text: `Successfully created CRM contact via Merge!\n` +
                                `ID: ${result.model?.id || 'N/A'}\n` +
                                `Name: ${result.model?.first_name} ${result.model?.last_name}\n` +
                                `Email: ${result.model?.email_addresses?.[0]?.email_address || 'N/A'}\n` +
                                `Status: ${result.model ? 'Created' : 'Pending sync'}\n` +
                                `Remote ID: ${result.model?.remote_id || 'Will be assigned'}`,
                        },
                    ],
                };
            }

            case 'search_crm_contacts': {
                const { query, limit = 10 } = args;
                const result = await mergeClient.searchCRM(query);
                const contacts = result.results?.slice(0, limit) || [];

                if (contacts.length === 0) {
                    return {
                        content: [
                            {
                                type: 'text',
                                text: `No contacts found${query ? ` for "${query}"` : ''}`,
                            },
                        ],
                    };
                }

                const contactList = contacts.map(contact => {
                    const email = contact.email_addresses?.[0]?.email_address || 'No email';
                    const name = `${contact.first_name || ''} ${contact.last_name || ''}`.trim();
                    return `${name} (${email}) - ID: ${contact.id}`;
                }).join('\n');

                return {
                    content: [
                        {
                            type: 'text',
                            text: `Found ${contacts.length} contact(s):\n\n${contactList}`,
                        },
                    ],
                };
            }

            case 'get_crm_contact': {
                const { contact_id } = args;
                const contact = await mergeClient.getContact(contact_id);

                const email = contact.email_addresses?.[0]?.email_address || 'No email';
                const phone = contact.phone_numbers?.[0]?.phone_number || 'No phone';
                const name = `${contact.first_name || ''} ${contact.last_name || ''}`.trim();

                return {
                    content: [
                        {
                            type: 'text',
                            text: `Contact Details:\n` +
                                `Name: ${name}\n` +
                                `Email: ${email}\n` +
                                `Phone: ${phone}\n` +
                                `ID: ${contact.id}\n` +
                                `Remote ID: ${contact.remote_id || 'N/A'}\n` +
                                `Created: ${contact.created_at || 'Unknown'}\n` +
                                `Modified: ${contact.modified_at || 'Unknown'}`,
                        },
                    ],
                };
            }

            case 'create_crm_opportunity': {
                const result = await mergeClient.createOpportunity(args);

                return {
                    content: [
                        {
                            type: 'text',
                            text: `Successfully created CRM opportunity via Merge!\n` +
                                `ID: ${result.model?.id || 'N/A'}\n` +
                                `Name: ${result.model?.name || args.name}\n` +
                                `Amount: ${result.model?.amount || args.amount || 0}\n` +
                                `Stage: ${result.model?.stage || args.stage || 'Not set'}\n` +
                                `Status: ${result.model ? 'Created' : 'Pending sync'}\n` +
                                `Remote ID: ${result.model?.remote_id || 'Will be assigned'}`,
                        },
                    ],
                };
            }

            case 'list_crm_opportunities': {
                const { limit = 10 } = args;
                const result = await mergeClient.getOpportunities(null, limit);
                const opportunities = result.results || [];

                if (opportunities.length === 0) {
                    return {
                        content: [
                            {
                                type: 'text',
                                text: 'No opportunities found in your CRM',
                            },
                        ],
                    };
                }

                const oppList = opportunities.map(opp => {
                    const amount = opp.amount ? `${opp.amount}` : 'No amount';
                    return `${opp.name || 'Unnamed'} - ${amount} (${opp.stage || 'No stage'}) - ID: ${opp.id}`;
                }).join('\n');

                return {
                    content: [
                        {
                            type: 'text',
                            text: `Found ${opportunities.length} opportunit${opportunities.length === 1 ? 'y' : 'ies'}:\n\n${oppList}`,
                        },
                    ],
                };
            }

            case 'get_crm_accounts': {
                const { limit = 10 } = args;
                const result = await mergeClient.getAccounts(null, limit);
                const accounts = result.results || [];

                if (accounts.length === 0) {
                    return {
                        content: [
                            {
                                type: 'text',
                                text: 'No accounts/companies found in your CRM',
                            },
                        ],
                    };
                }

                const accountList = accounts.map(account => {
                    return `${account.name || 'Unnamed Company'} - ID: ${account.id}${account.industry ? ` (${account.industry})` : ''}`;
                }).join('\n');

                return {
                    content: [
                        {
                            type: 'text',
                            text: `Found ${accounts.length} account(s):\n\n${accountList}`,
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

// Health check HTTP server
const app = express();
app.use(cors());

app.get('/health', async (req, res) => {
    try {
        const accountDetails = await mergeClient.getAccountDetails();

        res.json({
            status: 'healthy',
            service: 'merge-mcp-server',
            integration: accountDetails.integration?.name || 'Unknown',
            account_id: accountDetails.id,
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
        service: 'merge-mcp-server',
        version: '1.0.0',
        api_provider: 'Merge.dev',
        mcp_protocol: '2024-11-05',
        note: 'This server communicates via stdio, not HTTP. Use a proper MCP client.'
    });
});

// Start servers
async function start() {
    log('🚀 Starting Merge MCP Server...');
    log('🔄 Connecting to Merge unified API...');

    // Verify Merge connection first
    const connected = await verifyMergeConnection();
    if (!connected) {
        logError('Failed to connect to Merge. Check your API credentials.');
        process.exit(1);
    }

    // Start HTTP server for health checks
    app.listen(PORT, () => {
        log(`🌐 Health check server running on port ${PORT}`);
        log(`🔧 Available at: http://localhost:${PORT}/health`);
    });

    // Start MCP server on stdio
    const transport = new StdioServerTransport();
    await server.connect(transport);
    log('📡 Merge MCP Server connected via stdio');
}

// Error handling
process.on('SIGINT', async () => {
    log('\n🛑 Shutting down Merge MCP Server...');
    await server.close();
    process.exit(0);
});

process.on('unhandledRejection', (reason, promise) => {
    logError('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Start the server
start().catch(logError);