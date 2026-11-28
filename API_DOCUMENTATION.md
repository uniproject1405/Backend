# Tribe Backend API Documentation

## 1. General Information

**Base URL (Local Development):**

```text
http://127.0.0.1:8000
```

**API Prefix:**

```text
/api/
```

**Content-Type:**

- `application/json` for standard requests and responses.
- `multipart/form-data` for profile image uploads.

**Authentication:**

The API uses Token Authentication.

For authenticated requests, include:

```http
Authorization: Token YOUR_AUTH_TOKEN
```

Replace `YOUR_AUTH_TOKEN` with the token returned by the Register or Login endpoint.

Do not use `Bearer`. The required format is `Token`.

---

## 2. Authentication

### 2.1 Register

**Endpoint:**

```http
POST /api/users/register/
```

**Authentication:** Not required.

**Request Body:**

```json
{
  "email": "user@example.com",
  "username": "john_doe",
  "password": "Password123"
}
```

**Validation:**

- Email is required and must be valid.
- Email uniqueness is case-insensitive.
- Username is required.
- Username must not be blank.
- Leading `@` characters are removed.
- Username uniqueness is case-insensitive.
- Password must contain at least 8 characters.

**Success Response (201 Created):**

```json
{
  "token": "YOUR_AUTH_TOKEN",
  "user": {
    "profile_public_id": null,
    "email": "user@example.com",
    "username": "john_doe"
  }
}
```

Registration creates the user and authentication token. It does not automatically create a profile.

### 2.2 Login

**Endpoint:**

```http
POST /api/users/login/
```

**Authentication:** Not required.

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "Password123"
}
```

Login currently supports email and password authentication. Username login is not supported by this endpoint.

**Success Response (200 OK):**

```json
{
  "token": "YOUR_AUTH_TOKEN",
  "user": {
    "profile_public_id": null,
    "email": "user@example.com",
    "username": "john_doe"
  }
}
```

Invalid credentials return HTTP 400 with a generic error message.

### 2.3 Logout

**Endpoint:**

```http
POST /api/users/logout/
```

**Authentication:** Required.

**Success Response (200 OK):**

```json
{
  "message": "Successfully logged out."
}
```

The current authentication token is deleted.

### 2.4 Google Authentication

**Endpoint:**

```http
POST /api/users/google/
```

**Authentication:** Not required.

The request must provide one of the following:

- `id_token`
- `access_token`
- `code`

`redirect_uri` is optional.

**Example Request:**

```json
{
  "id_token": "GOOGLE_ID_TOKEN"
}
```

**Success Response (200 OK):**

```json
{
  "token": "YOUR_AUTH_TOKEN",
  "user": {
    "profile_public_id": null,
    "email": "user@example.com",
    "username": "john_doe"
  },
  "is_new_user": true
}
```

The `is_new_user` field indicates whether the account was newly created.

### 2.5 Google Login Redirect

**Endpoint:**

```http
GET /api/users/google/login/
```

**Authentication:** Not required.

Redirects the user to Google's authentication page.

To receive the authorization URL as JSON, use:

```http
GET /api/users/google/login/?format=json
```

**JSON Response (200 OK):**

```json
{
  "auth_url": "GOOGLE_AUTHORIZATION_URL"
}
```

An optional `state` query parameter is supported.

### 2.6 Google Callback

**Endpoint:**

```http
GET /api/users/google/callback/
```

**Authentication:** Not required.

Processes Google's callback and redirects the user to the frontend login page.

The redirect may include:

- `token`
- `email`
- `username`

If authentication fails, an `error` parameter is returned.

---

## 3. User and Profile APIs

### 3.1 Get Current User

**Endpoint:**

```http
GET /api/users/me/
```

**Authentication:** Required.

Returns the authenticated user's account and profile information.

If the user has not created a profile yet, the response includes `profile: null`.

**Example Response:**

```json
{
  "profile_public_id": null,
  "email": "user@example.com",
  "username": "john_doe",
  "profile": null,
  "message": "Please complete your profile."
}
```

### 3.2 Update Current Profile

**Endpoint:**

```http
PATCH /api/users/me/
```

**Authentication:** Required.

Updates an existing profile.

If the user does not have a profile, the endpoint returns HTTP 404:

```json
{
  "message": "Please create your profile first."
}
```

### 3.3 Create Profile

**Endpoint:**

```http
POST /api/users/me/profile/
```

**Authentication:** Required.

Creates a profile for the authenticated user.

**Example Request:**

```json
{
  "username": "john_doe",
  "name": "John Doe",
  "job_title": "Software Developer",
  "bio": "Interested in building useful products.",
  "skills": [
    "Python",
    "Django",
    "React"
  ],
  "contact_links": {
    "linkedin": "https://www.linkedin.com/in/john-doe/",
    "github": "https://github.com/john-doe"
  },
  "open_to_collaboration": true,
  "open_to_mentoring": false
}
```

**Required fields:**

- `name`
- `job_title`
- At least one skill

**Optional fields:**

- `bio`
- `avatar`
- `contact_links`
- `open_to_collaboration`
- `open_to_mentoring`

Skills must be English names and are limited to 20 entries.

Contact links support only:

- `email`
- `linkedin`
- `github`

Email and contact links are optional.

**Success Response (201 Created):**

```json
{
  "email": "user@example.com",
  "username": "john_doe",
  "profile": {
    "public_id": "PROFILE_UUID",
    "username": "john_doe",
    "name": "John Doe",
    "bio": "Interested in building useful products.",
    "job_title": "Software Developer",
    "skills": [
      "Python",
      "Django",
      "React"
    ],
    "avatar": null,
    "contact_links": {
      "linkedin": "https://www.linkedin.com/in/john-doe/",
      "github": "https://github.com/john-doe"
    },
    "open_to_collaboration": true,
    "open_to_mentoring": false
  },
  "message": "Profile created successfully."
}
```

If a profile already exists, the endpoint returns HTTP 409.

### 3.4 Get or Update My Profile

**Endpoint:**

```http
GET /api/users/profile/
PATCH /api/users/profile/
PUT /api/users/profile/
```

**Authentication:** Required.

Returns or updates the authenticated user's profile.

Returns HTTP 404 if the user has not created a profile.

### 3.5 Profile Completion

**Endpoint:**

```http
GET /api/users/profile/completion/
```

**Authentication:** Required.

Returns profile completion information.

**Response Structure:**

```json
{
  "completion_percentage": 100,
  "is_complete": true,
  "missing_fields": [],
  "breakdown": {
    "name": true,
    "job_title": true,
    "skills": true
  }
}
```

For Google users, username customization is also included in the completion breakdown.

### 3.6 Explore Partners

**Endpoint:**

```http
GET /api/users/explore/
```

**Authentication:** Not required.

Returns public partner profiles.

**Supported Query Parameters:**

| Parameter | Description |
|---|---|
| `search` | Search by name, job title, bio, username, or skill |
| `skill` | Filter by a skill name |
| `collaboration` | Filter by collaboration availability |
| `open_to_collaboration` | Alternative collaboration filter |
| `mentoring` | Filter by mentoring availability |
| `open_to_mentoring` | Alternative mentoring filter |
| `ordering` | Order by `created_at`, `name`, or `updated_at` |

Use `true`, `1`, or `yes` for a true availability filter. Other non-empty values are interpreted as false.

Prefixing the search value with `@` enables username-oriented searching.

**Example:**

```http
GET /api/users/explore/?skill=Python&collaboration=true
```

Public partner profiles contain:

- `public_id`
- `username`
- `name`
- `bio`
- `job_title`
- `skills`
- `avatar`
- `open_to_collaboration`
- `open_to_mentoring`

Contact links are not included in this public serializer.

### 3.7 Discover Partners

**Endpoint:**

```http
GET /api/users/discover/
```

**Authentication:** Not required.

This route is registered to `PartnerExploreView` and provides the same partner exploration behavior as `/api/users/explore/`.

### 3.8 Get Public User Details

**Endpoint:**

```http
GET /api/users/{public_id}/
```

**Authentication:** Not required.

Returns a public profile using the profile UUID.

### 3.9 Get Public Profile

**Endpoint:**

```http
GET /api/users/{public_id}/profile/
```

**Authentication:** Not required.

Returns the public profile associated with the specified profile UUID.

---

## 4. Project APIs

Project endpoints use UUID public identifiers rather than internal database IDs.

### 4.1 List Projects / Create Project

**Endpoint:**

```http
GET /api/projects/
POST /api/projects/
```

**Authentication:**

- GET: Public read access.
- POST: Authentication and complete profile required.

**Example Create Request:**

```json
{
  "title": "AI Learning Platform",
  "goal": "Build an AI-powered learning platform.",
  "description": "A collaborative project for developers.",
  "capacity": 5,
  "project_type": "startup",
  "custom_project_type": "",
  "skills": [
    "Python",
    "Django",
    "Machine Learning"
  ]
}
```

**Project Types:**

- `startup`
- `learning`
- `research`
- `personal`
- `other`

When `project_type` is `other`, `custom_project_type` is required.

**Skill Validation:**

- At least 1 skill is required.
- Maximum 15 skills.
- Skills must use English names.
- Duplicate skills are rejected case-insensitively.

The project capacity does not include the creator.

### 4.2 List My Projects

**Endpoint:**

```http
GET /api/projects/my/
```

**Authentication:** Required.

Returns projects created by the authenticated user or projects in which the user is a member.

The response includes the user's `role`:

- `creator`
- `member`

### 4.3 Explore Projects

**Endpoint:**

```http
GET /api/projects/explore/
```

**Authentication:** Public read access.

**Supported Query Parameters:**

| Parameter | Description |
|---|---|
| `search` | Search title, description, or skill name |
| `status` | Filter by `open` or `closed` |
| `skill` | Filter by exact skill name |
| `ordering` | Order by `created_at` or `-created_at` |

The default status filter is `open`.

The default ordering is:

```text
-created_at
```

**Example:**

```http
GET /api/projects/explore/?status=open&skill=Python&ordering=-created_at
```

### 4.4 Project Details

**Endpoint:**

```http
GET /api/projects/{public_id}/
PUT /api/projects/{public_id}/
PATCH /api/projects/{public_id}/
DELETE /api/projects/{public_id}/
```

**Authentication:** Read access is available publicly. Write permissions are controlled by project permissions.

Returns, updates, or deletes a project identified by its UUID.

### 4.5 Project Members

**Endpoint:**

```http
GET /api/projects/{public_id}/members/
```

**Authentication:** Public read access.

Returns the members of a project.

Each member includes:

- `user`
  - `public_id`
  - `username`
  - `name`
- `joined_at`

### 4.6 Remove Project Member

**Endpoint:**

```http
DELETE /api/projects/{public_id}/members/{member_public_id}/
```

**Authentication:** Required.

The project creator can remove a member. A member can also remove themselves.

If a project was closed because it reached capacity, removing a member can reopen it when its member count falls below capacity.

---

## 5. Membership Request APIs

Membership request endpoints are under:

```text
/api/applications/
```

### 5.1 Create Membership Request

**Endpoint:**

```http
POST /api/applications/requests/
```

**Authentication:** Required. A complete profile is also required.

**Example Request:**

```json
{
  "project": "PROJECT_UUID",
  "message": "I am interested in joining this project."
}
```

The `project` field uses the project's public UUID.

**Validation Rules:**

- The project must be open.
- Users cannot apply to their own projects.
- Existing project members cannot apply.
- Duplicate pending requests are not allowed.
- Project capacity must not be full.
- The applicant must have a complete profile.

### 5.2 List Incoming Requests

**Endpoint:**

```http
GET /api/applications/requests/incoming/
```

**Authentication:** Required.

Returns membership requests received for projects created by the authenticated user.

**Supported Query Parameters:**

| Parameter | Description |
|---|---|
| `project` | Filter by project UUID |
| `status` | Filter by request status |
| `search` | Search project title, username, email, or message |
| `ordering` | Order results |

Default ordering:

```text
-created_at
```

Pagination is enabled.

### 5.3 Update Membership Request Status

**Endpoint:**

```http
PATCH /api/applications/requests/{public_id}/
```

**Authentication:** Required.

Only the creator of the related project can accept or reject a request.

**Example Accept Request:**

```json
{
  "status": "accepted",
  "response_message": "Welcome to the project!"
}
```

**Example Reject Request:**

```json
{
  "status": "rejected",
  "response_message": "Thank you for your interest."
}
```

Allowed statuses:

- `accepted`
- `rejected`

Only pending requests can be updated.

When a request is accepted:

- A project membership is created.
- If project capacity is reached, the project status changes to `closed`.

### 5.4 Cancel Membership Request

**Endpoint:**

```http
DELETE /api/applications/requests/{public_id}/cancel/
```

**Authentication:** Required.

Users can cancel their own pending membership requests.

Only pending requests can be cancelled.

### 5.5 Membership Statistics

**Endpoint:**

```http
GET /api/applications/requests/stats/
```

**Authentication:** Required.

Returns sent and received membership request statistics.

**Response Structure:**

```json
{
  "sent": {
    "total": 0,
    "pending": 0,
    "accepted": 0,
    "rejected": 0
  },
  "received": {
    "total": 0,
    "pending": 0,
    "accepted": 0,
    "rejected": 0
  },
  "projects_to_review": [
    {
      "project_public_id": "PROJECT_UUID",
      "project_title": "AI Learning Platform",
      "pending_count": 2
    }
  ]
}
```

---

## 6. Chat APIs

Chat endpoints are under:

```text
/api/chat/
```

**Authentication:** Required for all Chat endpoints.

Note: Chat currently uses integer database IDs for conversations and recipient/project identifiers, unlike the UUID-based public identifiers used by Projects and Profiles.

### 6.1 List Conversations

**Endpoint:**

```http
GET /api/chat/conversations/
```

Returns conversations in which the authenticated user is a participant.

Conversations are ordered by most recently updated first.

### 6.2 Create or Retrieve a Conversation

**Endpoint:**

```http
POST /api/chat/conversations/
```

**Request fields:**

- `recipient_id`: Recipient's internal user ID.
- `project_id`: Optional internal project ID.

The endpoint checks whether a conversation already exists between the two users, optionally for the specified project.

- If an existing conversation is found, it returns that conversation with HTTP 200.
- If a new conversation is created, it returns HTTP 201.

### 6.3 Conversation Details

**Endpoint:**

```http
GET /api/chat/conversations/{pk}/
```

Returns conversation metadata.

Only participants can access the conversation.

### 6.4 List Messages

**Endpoint:**

```http
GET /api/chat/conversations/{conversation_id}/messages/
```

Returns messages in chronological order.

Only conversation participants can access the messages.

Incoming unread messages are automatically marked as read when this endpoint is called.

### 6.5 Send Message

**Endpoint:**

```http
POST /api/chat/conversations/{conversation_id}/messages/
```

**Example Request:**

```json
{
  "content": "Hello! I would like to discuss the project."
}
```

The authenticated user is automatically assigned as the sender.

**Success Response:** HTTP 201 Created.

### 6.6 Mark Messages as Read

**Endpoint:**

```http
POST /api/chat/conversations/{conversation_id}/read/
```

Marks all unread incoming messages in the conversation as read.

**Example Response:**

```json
{
  "status": "success",
  "marked_read": 3
}
```

`marked_read` represents the number of messages updated by the request.

### 6.7 Total Unread Message Count

**Endpoint:**

```http
GET /api/chat/unread-count/
```

Returns the total number of unread incoming messages across the authenticated user's conversations.

**Example Response:**

```json
{
  "unread_count": 5
}
```

---

## 7. Password Management

### 7.1 Request Password Reset

**Endpoint:**

```http
POST /api/users/password-reset/
```

**Authentication:** Not required.

**Request Body:**

```json
{
  "email": "user@example.com",
  "redirect_url": "http://localhost:5173/reset-password"
}
```

`redirect_url` is optional.

The endpoint returns a generic success response regardless of whether the email belongs to an existing account. This prevents account enumeration.

### 7.2 Validate Password Reset Token

**Endpoint:**

```http
GET /api/users/password-reset/validate/?uid=UID&token=TOKEN
```

Alternatively, POST with:

```json
{
  "uid": "UID",
  "token": "TOKEN"
}
```

**Authentication:** Not required.

**Success Response:**

```json
{
  "valid": true,
  "uid": "UID",
  "username": "john_doe",
  "message": "Token is valid."
}
```

Invalid or expired tokens return HTTP 400.

### 7.3 Confirm Password Reset

**Endpoint:**

```http
POST /api/users/password-reset/confirm/
```

**Request Body:**

```json
{
  "uid": "UID",
  "token": "TOKEN",
  "new_password": "NewPassword123",
  "confirm_password": "NewPassword123"
}
```

Both password fields must contain at least 8 characters and must match.

### 7.4 Change Password

**Endpoint:**

```http
POST /api/users/password-change/
```

**Authentication:** Required.

**Request Body:**

```json
{
  "old_password": "OldPassword123",
  "new_password": "NewPassword123",
  "confirm_password": "NewPassword123"
}
```

The old password must be correct, and the new password fields must match.

**Success Response:**

```json
{
  "message": "Password changed successfully.",
  "status": "success"
}
```

---

## 8. Common Validation and Error Responses

The API uses standard HTTP status codes.

| Status Code | Meaning |
|---|---|
| 200 OK | Request completed successfully |
| 201 Created | Resource successfully created |
| 204 No Content | Resource successfully deleted |
| 400 Bad Request | Invalid request data or validation error |
| 401 Unauthorized | Authentication required or invalid |
| 403 Forbidden | User does not have permission |
| 404 Not Found | Resource does not exist |
| 409 Conflict | Resource already exists or conflicts with current state |

Validation errors are returned as JSON.

Example:

```json
{
  "email": [
    "Enter a valid email address."
  ]
}
```

---

## 9. Important API Design Notes

1. Token authentication uses the `Token` prefix, not `Bearer`.
2. Registration does not automatically create a profile.
3. Profile completion requires a name, job title, and at least one skill.
4. Project creation and membership request submission require a complete profile.
5. Project skills and profile skills are separate resources.
6. Project and profile identifiers exposed by their APIs are UUIDs.
7. Membership requests use public UUID identifiers.
8. Chat conversation and recipient/project references currently use integer IDs.
9. Project capacity does not include the project creator.
10. Public partner responses do not expose contact links.
11. Password reset requests use a generic response to avoid revealing whether an account exists.

---

## 10. API Endpoint Summary

| Module | Method | Endpoint |
|---|---|---|
| Users | GET | `/api/users/` |
| Users | POST | `/api/users/register/` |
| Users | POST | `/api/users/login/` |
| Users | GET/PATCH | `/api/users/me/` |
| Users | POST | `/api/users/me/profile/` |
| Users | POST | `/api/users/logout/` |
| Users | POST | `/api/users/google/` |
| Users | GET | `/api/users/google/login/` |
| Users | GET | `/api/users/google/callback/` |
| Users | POST | `/api/users/password-reset/` |
| Users | GET/POST | `/api/users/password-reset/validate/` |
| Users | POST | `/api/users/password-reset/confirm/` |
| Users | POST | `/api/users/password-change/` |
| Users | GET | `/api/users/explore/` |
| Users | GET | `/api/users/discover/` |
| Users | GET | `/api/users/profile/` |
| Users | GET/PATCH/PUT | `/api/users/profile/` |
| Users | GET | `/api/users/profile/completion/` |
| Users | GET | `/api/users/{public_id}/` |
| Users | GET | `/api/users/{public_id}/profile/` |
| Projects | GET/POST | `/api/projects/` |
| Projects | GET | `/api/projects/my/` |
| Projects | GET | `/api/projects/explore/` |
| Projects | GET/PUT/PATCH/DELETE | `/api/projects/{public_id}/` |
| Projects | GET | `/api/projects/{public_id}/members/` |
| Projects | DELETE | `/api/projects/{public_id}/members/{member_public_id}/` |
| Applications | POST | `/api/applications/requests/` |
| Applications | GET | `/api/applications/requests/incoming/` |
| Applications | GET | `/api/applications/requests/stats/` |
| Applications | PATCH | `/api/applications/requests/{public_id}/` |
| Applications | DELETE | `/api/applications/requests/{public_id}/cancel/` |
| Chat | GET/POST | `/api/chat/conversations/` |
| Chat | GET | `/api/chat/conversations/{pk}/` |
| Chat | GET/POST | `/api/chat/conversations/{conversation_id}/messages/` |
| Chat | POST | `/api/chat/conversations/{conversation_id}/read/` |
| Chat | GET | `/api/chat/unread-count/` |

**End of Documentation**