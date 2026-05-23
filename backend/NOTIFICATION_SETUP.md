# Notification System Setup and Testing

## Overview
This document provides instructions for setting up and testing the notification system.

## Changes Made

### 1. Updated Notification Model
- **File**: `app/models/notification.py`
- **Changes**:
  - Renamed `notification_type` to `type` (matches frontend API)
  - Renamed `is_read` to `status` (matches frontend API)
  - Added `NotificationStatus` enum (unread, read)
  - Added new notification types: email, profile, password, device, warning, success
  - Added `related_id` and `related_type` for flexible entity linking
  - Added `metadata` JSONB field for additional data
  - Changed `created_at` to use timezone-aware datetime
  - Added CASCADE delete on user_id

### 2. Updated Notifications Router
- **File**: `app/routers/notifications.py`
- **Changes**:
  - Added filtering by type, status, from_date, to_date
  - Added pagination (page, per_page)
  - Added `POST /api/notifications/mark-all-read` endpoint
  - Changed `PUT /{notification_id}/read` to `POST /{notification_id}/mark-read`
  - Added `DELETE /{notification_id}` endpoint
  - Updated response format to match frontend expectations

### 3. Updated Transfer Notifications
- **File**: `app/routers/transfers.py`
- **Changes**:
  - Updated `create_notification` function to use new fields
  - Added metadata to notifications (amount, recipient/sender, reference)
  - Updated both local and international transfer notifications

### 4. Created Notification Service
- **File**: `app/services/notification_service.py`
- **Purpose**: Centralized notification creation logic
- **Features**:
  - `create_notification()` - Generic notification creation
  - `create_transfer_notification()` - Creates sender and recipient notifications
  - `create_security_notification()` - Security-specific notifications
  - `create_system_notification()` - System-specific notifications

### 5. Created Migration
- **File**: `alembic/versions/update_notifications_model.py`
- **Purpose**: Update database schema for notifications table

### 6. Created Test Suite
- **File**: `test_notifications.py`
- **Purpose**: Test notification endpoints and functionality

## Setup Instructions

### Step 1: Run Database Migration

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
alembic upgrade head
```

Or if using auto-create (development):
```bash
# The table will be auto-created on server restart
# But migration is recommended for production
```

### Step 2: Restart Backend Server

```bash
# Stop the server if running
# Then restart:
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3: Run Test Suite

```bash
cd backend
python test_notifications.py
```

**Note**: Update the test credentials in `test_notifications.py` before running:
```python
TEST_USER_EMAIL = "your_test_email@example.com"
TEST_USER_PASSWORD = "YourPassword123!"
TEST_PIN = "1234"
```

## Manual Testing Steps

### 1. Test Transfer Notifications
1. Login to the frontend application
2. Navigate to Transfer page
3. Make a local transfer to another user
4. Check the Notifications dashboard
5. Verify:
   - Notification appears with "Transfer Sent" title
   - Notification badge shows correct count
   - Time is displayed in your local timezone
   - Clicking notification shows details

### 2. Test Notification Badge
1. Make multiple transfers
2. Observe the notification badge on the topbar
3. Badge should show the number of unread notifications
4. Badge should show "99+" if count exceeds 99
5. Badge should hide when all notifications are read

### 3. Test Filtering
1. Navigate to Notifications dashboard
2. Use filter dropdown to filter by type (transaction, system, security)
3. Use filter dropdown to filter by status (unread, read)
4. Use date range filters
5. Verify results update correctly

### 4. Test Mark All as Read
1. Make sure you have unread notifications
2. Click "Mark All Read" button
3. Verify all notifications are marked as read
4. Verify notification badge disappears

### 5. Test Timezone Display
1. Change your browser/system timezone
2. Refresh the page
3. Verify notification times display in your local timezone
4. Test with different timezones (US Eastern, South Africa, etc.)

## API Endpoints

### GET /api/notifications
Get user's notifications with filtering and pagination

**Query Parameters:**
- `type` (optional): Filter by notification type
- `status` (optional): Filter by status (unread, read)
- `from_date` (optional): Filter from date (ISO format)
- `to_date` (optional): Filter to date (ISO format)
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 20, max: 100)

**Response:**
```json
{
  "notifications": [
    {
      "id": "uuid",
      "title": "Transfer Sent",
      "type": "transaction",
      "status": "unread",
      "created_at": "2026-05-23T14:30:00Z",
      "related_id": "uuid",
      "related_type": "transaction",
      "metadata": {
        "amount": 1000,
        "recipient": "John Doe",
        "reference": "REF123456"
      }
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20
}
```

### GET /api/notifications/unread-count
Get count of unread notifications

**Response:**
```json
{
  "count": 5
}
```

### POST /api/notifications/mark-all-read
Mark all notifications as read

**Response:**
```json
{
  "success": true,
  "updated_count": 5
}
```

### POST /api/notifications/{notification_id}/mark-read
Mark single notification as read

**Response:**
```json
{
  "success": true
}
```

### DELETE /api/notifications/{notification_id}
Delete a notification

**Response:**
```json
{
  "success": true
}
```

## Notification Types

| Type | Icon | Color | Use Case |
|------|------|-------|----------|
| transaction | ↓ | Green | Money transfers, deposits, withdrawals |
| system | ℹ | Blue | System updates, email verification, profile changes |
| security | 🔒 | Orange | Account blocking, PIN changes, security alerts |
| email | ✉ | Blue | Email verification, email updates |
| profile | 👤 | Purple | Profile updates |
| password | 🔑 | Orange | Password changes |
| device | 📱 | Red | New device login, security alerts |
| warning | ⚠ | Orange | Warnings, alerts |
| success | ✓ | Green | Success confirmations |

## Future Notification Triggers

To add notifications for other events, use the `NotificationService`:

```python
from app.services.notification_service import NotificationService
from app.models.notification import NotificationType

# Example: Email verification notification
NotificationService.create_system_notification(
    db, user_id,
    "Email Verified",
    "Your email has been successfully verified.",
    metadata={"email": user.email}
)

# Example: Account blocked notification
NotificationService.create_security_notification(
    db, user_id,
    "Account Blocked",
    "Your account has been blocked by an administrator.",
    metadata={"reason": "Suspicious activity", "blocked_by": admin_id}
)

# Example: PIN set notification
NotificationService.create_security_notification(
    db, user_id,
    "PIN Set Successfully",
    "Your transaction PIN has been set successfully."
)
```

## Troubleshooting

### Notifications not appearing after transfer
1. Check backend logs for errors
2. Verify database migration was run
3. Check that notification creation code is being called
4. Verify user_id is correct
5. Check browser console for API errors

### Notification badge not updating
1. Check that `/api/notifications/unread-count` is being called
2. Verify the response format matches expectations
3. Check browser console for JavaScript errors

### Time not displaying correctly
1. Verify backend returns timestamps in ISO 8601 format with 'Z' suffix
2. Check browser timezone settings
3. Verify TimeUtils.js is loaded correctly

### Migration errors
1. Drop existing notifications table manually if needed:
   ```sql
   DROP TABLE IF EXISTS notifications CASCADE;
   ```
2. Run migration again
3. Restart server

## Summary

✅ **Completed:**
- Updated notification model to match frontend API
- Updated notifications router with filtering and pagination
- Updated transfer notifications with metadata
- Created notification service for centralized logic
- Created database migration
- Created test suite

✅ **Ready for Testing:**
- Transfer notifications will appear automatically
- Notification badge will show unread count
- Time will display in user's local timezone
- Filtering and pagination work correctly

⏳ **Future Enhancements** (Optional):
- Add notification triggers for email verification
- Add notification triggers for account blocking/unblocking
- Add notification triggers for PIN changes
- Add notification triggers for profile updates
- Add real-time updates via WebSocket (Phase 5)
