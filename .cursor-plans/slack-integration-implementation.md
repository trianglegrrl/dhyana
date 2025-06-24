# Slack Integration Implementation Plan

## Overview
Implement comprehensive Slack integration with webhook support, message posting capabilities, and DM functionality. The basic Slack webhook endpoints and models already exist but need complete implementation and enhancement.

## Current State Analysis
- ✅ Slack webhook endpoints exist in `backend/routes/webhooks.py` (`/slack/events`, `/slack/interactions`, `/slack/commands`)
- ✅ Slack models (`SlackTeam`, `SlackUser`, `SlackChannel`, `SlackMessage`) are complete
- ✅ Configuration structure in place (`SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`)
- ✅ Slack SDK already installed (`slack-sdk==3.26.1`)
- ✅ Slack API client utilities complete in `backend/utils/slack_client.py`
- ❌ Slack webhook handlers implemented but need comprehensive testing
- ❌ No comprehensive Slack webhook tests exist
- ❌ Test coverage for interactive components and slash commands missing
- ❌ Integration tests between Jobber and Slack systems missing

## Implementation Tasks

### 1. Slack API Client Implementation
- [x] Create `backend/utils/slack_client.py` for API interactions
- [x] Implement WebClient wrapper with error handling and retry logic
- [x] Add functions for posting messages to channels
- [x] Add functions for sending direct messages
- [x] Implement user and channel lookup utilities
- [x] Add rate limiting and retry logic
- [x] Add support for rich message formatting (blocks, attachments)

### 2. Enhanced Webhook Event Handling
- [x] Complete `handle_slack_message(event, team_id)` - sync message data to database
- [x] Complete `handle_slack_mention(event, team_id)` - process app mentions with intelligent responses
- [x] Complete `handle_slack_channel_created(event, team_id)` - sync channel data
- [x] Complete `handle_slack_user_joined(event, team_id)` - sync user data
- [x] Add `handle_slack_channel_rename(event, team_id)` - update channel info
- [x] Add `handle_slack_channel_archive(event, team_id)` - mark channel as archived
- [x] Add `handle_slack_user_change(event, team_id)` - update user profile changes
- [x] Add proper error handling and logging for all handlers

### 3. Interactive Components Implementation
- [x] Complete `handle_slack_block_actions(payload)` - process button clicks and interactions
- [x] Complete `handle_slack_modal_submission(payload)` - handle modal form submissions
- [x] Complete `handle_slack_shortcut(payload)` - handle global and message shortcuts
- [x] Add support for select menus and multi-select interactions
- [x] Implement interactive Jobber data views (job details, client info)

### 4. Slash Commands Enhancement
- [x] Enhance existing `/jobber` command with rich interactive responses
- [x] Add `/slack` command for Slack-specific operations
- [x] Add `/help` command with usage instructions
- [x] Implement command argument parsing and validation
- [x] Add permission checks for sensitive commands
- [x] Create rich formatted responses using Block Kit

### 5. Database Integration & Synchronization
- [x] Implement upsert logic for all Slack entities (teams, users, channels, messages)
- [x] Add database indexes for frequently queried fields
- [x] Implement data cleanup for archived channels and deactivated users
- [x] Add relationship management between entities
- [x] Implement message threading support

### 6. Slack App Installation Flow
- [ ] Add OAuth callback handling in `backend/routes/auth.py`
- [ ] Implement team installation and token management
- [ ] Add support for workspace app installation
- [ ] Handle token rotation and refresh
- [ ] Store team configuration and preferences

### 7. Message & DM Posting Capabilities
- [x] Create high-level functions for posting formatted messages
- [x] Implement template system for common message types
- [x] Add support for ephemeral messages (only visible to specific users)
- [x] Implement message scheduling capabilities
- [x] Add attachment and file sharing support
- [x] Create notification system for Jobber events → Slack channels

### 8. Advanced Slack Features
- [x] Implement Block Kit message builders
- [x] Add support for modal dialogs for complex forms
- [x] Create interactive workflows for Jobber operations
- [ ] Add support for Slack workflows and triggers
- [x] Implement message threading for related notifications

### 9. Setup Documentation
- [ ] Create `docs/SLACK_SETUP.md` with comprehensive setup instructions
- [ ] Document required environment variables and scopes
- [ ] Provide Slack app creation and configuration steps
- [ ] Add webhook URL configuration instructions
- [ ] Include OAuth setup and installation process
- [ ] Add testing and verification steps

### 10. **CURRENT PRIORITY: Testing & Validation**
- [x] **Create comprehensive Slack webhook test suite (`backend/tests/test_slack_webhooks.py`)**
- [x] **Add test fixtures and mock data for Slack events**
- [x] **Test signature verification for all Slack webhook types**
- [x] **Test all Slack event handlers (messages, mentions, channel events, user events)**
- [x] **Test interactive components (buttons, modals, shortcuts)**
- [x] **Test slash commands with various arguments and scenarios**
- [x] **Test message posting and DM functionality**
- [x] **Test rate limiting and retry logic**
- [x] **Add integration tests between Jobber and Slack systems**
- [x] **Test error scenarios and edge cases**
- [x] **Add performance and load testing for webhook endpoints**
- [x] **FIXED: Resolve SQLAlchemy context issues in tests**
- [x] **FIXED: Fix malformed JSON handling in webhooks**
- [x] **FIXED: Improve exception handling in webhook endpoints**
- [x] **ALL 28 SLACK WEBHOOK TESTS PASSING** ✅
- [ ] **Create test runner script for all webhook tests**
- [ ] **Add continuous integration test configuration**

### 11. **Test Implementation Details**
- [ ] **Unit Tests:**
  - Slack signature verification
  - Individual event handlers
  - SlackAPIClient methods
  - SlackMessageBuilder utilities
  - Database synchronization logic
- [ ] **Integration Tests:**
  - End-to-end webhook flow
  - Slack API interactions (mocked)
  - Database persistence
  - Error handling and recovery
- [ ] **Performance Tests:**
  - High-volume webhook processing
  - Rate limiting behavior
  - Memory usage during batch operations
- [ ] **Security Tests:**
  - Invalid signature handling
  - Malformed request handling
  - Authentication edge cases

## File Changes Required

### New Files
- [x] `backend/utils/slack_client.py` - Slack API client utilities
- [ ] `docs/SLACK_SETUP.md` - Setup and configuration documentation
- [ ] **`backend/tests/test_slack_webhooks.py` - Comprehensive Slack webhook tests**
- [ ] **`backend/tests/test_slack_client.py` - Slack API client tests**
- [ ] **`backend/tests/test_slack_integration.py` - Integration tests**
- [ ] **`backend/tests/conftest.py` - Shared test fixtures and configuration**
- [ ] **`scripts/run_tests.py` - Test runner script**

### Modified Files
- [x] `backend/routes/webhooks.py` - Complete all Slack webhook handlers
- [ ] `backend/routes/auth.py` - Add OAuth callback handling
- [ ] `backend/config.py` - Add additional Slack configuration if needed
- [ ] `backend/models/slack_models.py` - Add missing fields if discovered during testing
- [ ] **`backend/requirements.txt` - Add testing dependencies**

## Technical Considerations

### Webhook Security
- Use Slack's signature verification (already partially implemented)
- Implement proper timestamp validation to prevent replay attacks
- Log failed verification attempts for security monitoring

### Data Synchronization
- Use upsert pattern: update if exists, create if not
- Handle partial data updates gracefully
- Maintain referential integrity between teams, users, channels, and messages
- Implement soft delete for archived/deactivated entities

### Error Handling
- Return 200 OK even for handled errors (webhook best practice)
- Log all errors with appropriate context for debugging
- Implement graceful degradation for API failures
- Add circuit breaker pattern for external API calls

### Performance
- Use database transactions for multi-record updates
- Implement async processing for heavy webhook loads (using existing Celery)
- Add database indexes for webhook lookup performance
- Cache frequently accessed Slack data (user info, channel info)

### Rate Limiting
- Respect Slack API rate limits (1+ requests per second per workspace)
- Implement exponential backoff for rate limit errors
- Use Slack SDK built-in rate limiting features
- Queue messages during rate limit periods

### Testing Strategy
- **Mock external API calls** to avoid rate limits during testing
- **Use test fixtures** for consistent webhook payloads
- **Test both success and failure scenarios**
- **Validate database state** after webhook processing
- **Test concurrent webhook processing**
- **Verify Slack API client behavior under various conditions**

## Environment Variables Required
```bash
# Slack API Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
SLACK_CLIENT_ID=your-client-id-here
SLACK_CLIENT_SECRET=your-client-secret-here

# Optional: Advanced Features
SLACK_APP_TOKEN=xapp-your-app-token-here  # For Socket Mode (development)

# Testing Configuration
TESTING=True
TEST_DATABASE_URL=postgresql://user:pass@localhost/test_db
```

## Slack App Scopes Required
- `app_mentions:read` - Receive mentions
- `channels:history` - Read messages from public channels
- `channels:read` - View basic channel information
- `chat:write` - Send messages as the app
- `commands` - Add slash commands
- `groups:history` - Read messages from private channels (if needed)
- `im:history` - Read messages from direct messages
- `im:write` - Send direct messages
- `team:read` - View workspace information
- `users:read` - View user information
- `files:write` - Upload files (if needed)

## Integration with Existing Jobber System
- [x] Create Slack notifications for Jobber webhook events
- [x] Add Slack commands to query Jobber data
- [x] Implement interactive Jobber workflows in Slack
- [ ] Add Slack user mapping to Jobber client relationships
- [ ] Create daily/weekly Jobber reports posted to designated channels

## Testing Implementation Plan

### Phase 1: Test Infrastructure
1. **Add testing dependencies** to requirements.txt
2. **Create test configuration** and fixtures
3. **Set up test database** and mock services
4. **Create test runner** with proper setup/teardown

### Phase 2: Unit Tests
1. **Slack webhook signature verification**
2. **Individual event handlers** with mocked database
3. **SlackAPIClient methods** with mocked Slack SDK
4. **Message builders and formatters**

### Phase 3: Integration Tests
1. **End-to-end webhook processing**
2. **Database synchronization verification**
3. **Slack API integration** (mocked)
4. **Error handling and recovery**

### Phase 4: Performance & Load Tests
1. **High-volume webhook processing**
2. **Rate limiting verification**
3. **Memory usage monitoring**
4. **Concurrent request handling**

## Validation Steps
1. Configure Slack app in workspace
2. Set up webhook URLs (Events API, Interactive Components, Slash Commands)
3. **Run comprehensive test suite**
4. Test OAuth installation flow
5. Test each webhook event type
6. Verify data synchronization in database
7. Test interactive components and slash commands
8. Test message posting and DM functionality
9. Validate error handling scenarios
10. **Performance testing under load**
11. Test integration with Jobber system

## Success Criteria
- [ ] All Slack webhook events properly handled and stored
- [ ] Secure webhook signature verification working
- [ ] Complete OAuth installation flow
- [ ] Rich interactive slash commands working
- [ ] Message posting and DM capabilities functional
- [ ] Interactive components (buttons, modals) working
- [ ] Integration with Jobber system for notifications
- [ ] Complete setup documentation
- [ ] **Comprehensive test coverage (>95%)**
- [ ] **All tests passing in CI/CD pipeline**
- [ ] **Performance benchmarks met**
- [ ] Production-ready error handling and logging
- [ ] Rate limiting and performance optimization