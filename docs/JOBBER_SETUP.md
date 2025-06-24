# Jobber Integration Setup Guide

This guide walks you through setting up the Jobber integration for the Dhyana Test application, including API access, webhook configuration, and testing.

## Overview

The Jobber integration provides:
- Real-time synchronization of clients, jobs, and invoices via webhooks
- Slack notifications for important Jobber events
- API access to Jobber data through slash commands
- Automated data backup and redundancy

## Prerequisites

1. **Jobber Developer Account**: You need access to the Jobber Developer Center
2. **Jobber Business Account**: A Jobber account with API access (trial or paid)
3. **Running Application**: The backend application running and accessible from the internet

## Step 1: Create Jobber Developer Account

1. Visit the [Jobber Developer Center](https://developers.getjobber.com/)
2. Sign up for a developer account (separate from your regular Jobber account)
3. Verify your email address

## Step 2: Set Up Testing Jobber Account

1. **Option A**: Use the developer testing signup link from the Developer Center
   - This provides a 90-day trial account specifically for development
   - Can be extended by contacting Jobber API support

2. **Option B**: Convert existing trial account
   - If you have a regular 14-day trial, contact `api-support@getjobber.com`
   - Request conversion to a developer testing account

## Step 3: Create Your Jobber App

1. Sign in to your Developer Center account
2. Navigate to the 'Apps' page
3. Click 'NEW' to create your first app
4. Fill in the required information:

   ```
   App Name: Dhyana Test Integration
   Developer Name: [Your Name/Company]
   App Description: Slack-Jobber integration for automated workflow management
   OAuth Callback URL: https://yourdomain.com/auth/jobber/callback
   Manage App URL: https://yourdomain.com/admin/jobber
   ```

5. **Set Required Scopes**:
   - `clients:read` - Read client information
   - `clients:write` - Create and update clients
   - `jobs:read` - Read job information
   - `jobs:write` - Create and update jobs
   - `invoices:read` - Read invoice information
   - `invoices:write` - Create and update invoices
   - `webhooks:read` - Access webhook data

6. **Configure Webhooks**:
   - Webhook URL: `https://yourdomain.com/webhooks/jobber/webhooks`
   - Select events:
     - `CLIENT_CREATE` - New client created
     - `CLIENT_UPDATE` - Client updated
     - `JOB_CREATE` - New job created
     - `JOB_UPDATE` - Job updated
     - `JOB_COMPLETE` - Job completed
     - `INVOICE_CREATE` - New invoice created
     - `INVOICE_UPDATE` - Invoice updated
     - `QUOTE_CREATE` - New quote created
     - `QUOTE_APPROVAL` - Quote approved

7. Save your app and note the **Client ID** and **Client Secret**

## Step 4: Generate API Credentials

### OAuth Access Token (Recommended)
1. In the Developer Center, click the three dots next to your app
2. Click "Test in Playground"
3. Complete the OAuth 2.0 flow
4. Save the generated access token

### API Key (Alternative)
1. In your Jobber business account, go to Settings → Integrations
2. Find your app and generate an API key
3. Note both the API Key and API Secret

## Step 5: Configure Environment Variables

Add the following environment variables to your application:

```bash
# Jobber API Configuration
JOBBER_API_KEY=your_access_token_here
JOBBER_API_SECRET=your_api_secret_here
JOBBER_WEBHOOK_SECRET=your_webhook_secret_here
JOBBER_BASE_URL=https://api.getjobber.com

# Optional: For development/testing
JOBBER_ENVIRONMENT=development
```

### Environment Variable Details

- **JOBBER_API_KEY**: OAuth access token or API key for authenticating API requests
- **JOBBER_API_SECRET**: API secret (if using API key method)
- **JOBBER_WEBHOOK_SECRET**: Secret for verifying webhook signatures (generate a random string)
- **JOBBER_BASE_URL**: Jobber API base URL (should remain as shown)

## Step 6: Configure Webhook Secret

1. Generate a secure random string for webhook verification:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

2. Set this as your `JOBBER_WEBHOOK_SECRET` environment variable

3. In the Jobber Developer Center, configure this same secret for your webhook endpoint

## Step 7: Update Docker Configuration

If using Docker, add the environment variables to your `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      # ... existing environment variables ...
      JOBBER_API_KEY: ${JOBBER_API_KEY}
      JOBBER_API_SECRET: ${JOBBER_API_SECRET}
      JOBBER_WEBHOOK_SECRET: ${JOBBER_WEBHOOK_SECRET}
      JOBBER_BASE_URL: https://api.getjobber.com
```

Create a `.env` file in your project root:

```bash
# .env file
JOBBER_API_KEY=your_access_token_here
JOBBER_API_SECRET=your_api_secret_here
JOBBER_WEBHOOK_SECRET=your_webhook_secret_here
```

## Step 8: Verify Installation

### Test API Connection

1. Start your application:
   ```bash
   docker-compose --profile dev up -d
   ```

2. Check the logs for successful startup:
   ```bash
   docker-compose logs backend
   ```

3. Test API connectivity by creating a test client in Jobber and checking if it appears in your database

### Test Webhook Endpoint

1. Use a tool like ngrok to expose your local development server:
   ```bash
   ngrok http 8000
   ```

2. Update your Jobber app webhook URL to the ngrok URL:
   ```
   https://your-ngrok-url.ngrok.io/webhooks/jobber/webhooks
   ```

3. Create a test client in Jobber and verify the webhook is received

### Test Slack Integration

1. In your Slack workspace, use the `/jobber` command:
   ```
   /jobber clients
   /jobber jobs
   /jobber invoices
   ```

2. Verify that data is returned from your Jobber integration

## Step 9: Production Deployment

### SSL Certificate
Ensure your production server has a valid SSL certificate - Jobber requires HTTPS for webhooks.

### Domain Configuration
1. Update your Jobber app configuration with your production domain
2. Set webhook URL to: `https://yourdomain.com/webhooks/jobber/webhooks`
3. Update OAuth callback URL if using OAuth flow

### Environment Variables
Set production environment variables securely:
- Use your hosting platform's environment variable management
- Never commit secrets to version control
- Consider using a secret management service

### Monitoring
Monitor the following:
- Webhook endpoint response times and success rates
- API rate limit usage (2500 requests per 5 minutes)
- Database synchronization accuracy
- Slack notification delivery

## Testing Checklist

- [ ] Jobber developer account created
- [ ] Testing Jobber account set up
- [ ] App created in Developer Center with correct scopes
- [ ] API credentials generated and configured
- [ ] Webhook secret generated and configured
- [ ] Environment variables set correctly
- [ ] Application starts without errors
- [ ] Webhook endpoint responds with 200 OK
- [ ] Test client creation triggers webhook
- [ ] Client data synchronized to database
- [ ] Slack notification sent for new client
- [ ] `/jobber` slash commands work
- [ ] Job and invoice webhooks function correctly

## Troubleshooting

### Common Issues

**401 Unauthorized**
- Check that JOBBER_API_KEY is set correctly
- Verify the access token hasn't expired
- Ensure proper scopes are configured

**Webhook Signature Verification Failed**
- Verify JOBBER_WEBHOOK_SECRET matches Jobber configuration
- Check that webhook URL is accessible from internet
- Ensure HTTPS is configured properly

**Rate Limit Exceeded**
- Implement exponential backoff in API calls
- Consider caching frequently accessed data
- Monitor API usage patterns

**Missing Data**
- Check that all required scopes are enabled
- Verify GraphQL queries include all needed fields
- Test with Jobber's GraphQL Playground

### Debug Mode

Enable debug logging by setting:
```bash
FLASK_ENV=development
LOG_LEVEL=DEBUG
```

### API Testing

Use the GraphQL Playground to test queries:
1. In Developer Center, click "Test in Playground" next to your app
2. Test queries before implementing in code
3. Verify data structure and field availability

## Support

- **Jobber API Documentation**: https://developer.getjobber.com/docs/
- **Jobber Developer Support**: api-support@getjobber.com
- **GraphQL Playground**: Available through Developer Center
- **Rate Limits**: 2500 requests per 5 minutes per app/account

## API Version

This integration uses Jobber API version `2023-11-15`. Check for updates regularly and plan upgrades accordingly. API versions are supported for a minimum of 12 months.

## Security Notes

- Store API credentials securely
- Use HTTPS for all webhook endpoints
- Implement proper signature verification for webhooks
- Monitor for unusual API activity
- Rotate webhook secrets periodically
