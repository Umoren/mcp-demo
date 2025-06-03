# Merge API Setup Guide

To use the Merge MCP server with real CRM integrations, you need Merge API credentials.

## Step 1: Create Merge Account

1. Go to [https://app.merge.dev/](https://app.merge.dev/)
2. Sign up for a free account
3. Complete the onboarding process

## Step 2: Get API Keys

1. Navigate to **API Keys** section
2. Copy your **API Key** (starts with `live_` for production)
3. Keep this secure - it's your authentication token

## Step 3: Connect a CRM Integration

1. Go to **Integrations** → **CRM**
2. Choose a CRM provider:
   - **HubSpot** (recommended for testing - free tier available)
   - **Salesforce** 
   - **Pipedrive**
   - **Airtable** (good for demos)
   - Many others...

3. Follow the OAuth flow to connect your CRM account
4. Copy the **Account Token** (UUID format)

## Step 4: Add to Environment

Add these to your `.env` file:

```bash
# Merge API Configuration
MERGE_API_KEY=live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MERGE_ACCOUNT_TOKEN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

## Step 5: Test the Connection

```bash
# Check if Merge server can connect
curl http://localhost:8002/health

# Run the full test suite
python test/test-merge.py
```

## For Demo/Testing Only

If you just want to test MCP without setting up real CRM accounts:

1. Use HubSpot's free tier
2. Or Airtable (works great for demos)
3. Create a few test contacts manually
4. The MCP server will use Merge's unified API to interact with them

## API Rate Limits

- **Development**: 100 requests/minute
- **Production**: Higher limits available
- The MCP demo stays well within these limits

## Troubleshooting

**"Failed to connect to Merge"**: Check your API key and account token

**"Integration not found"**: Ensure you've connected a CRM in the Merge dashboard

**"Unauthorized"**: Your API key might be incorrect or expired

**Need help?**: Check [Merge's documentation](https://docs.merge.dev/) or their support
