# REST API

Base URL: `/api/v1`

Except for health, login and token-authorised public transactions, endpoints require a bearer JWT.

## Authentication

- `POST /auth/login`
- `GET /auth/me`

## Registry

- `GET /blocks`
- `GET /dashboard`

## Workflows

- `GET /workflows`
- `POST /workflows`
- `GET /workflows/{id}`
- `PUT /workflows/{id}`
- `DELETE /workflows/{id}`
- `POST /workflows/{id}/validate`
- `POST /workflows/{id}/execute`

## Sandboxes

- `GET /sandboxes`
- `POST /sandboxes`
- `GET /sandboxes/{id}`
- `PUT /sandboxes/{id}`
- `GET /sandboxes/{id}/manifest`
- `GET /sandboxes/{id}/developer-kit`
- `GET /sandboxes/{id}/events`
- `POST /sandboxes/{id}/execute`
- `GET /sandboxes/{id}/attachments`
- `POST /sandboxes/{id}/attachments`
- `DELETE /sandboxes/{id}/attachments/{attachment_id}`

## Executions

- `GET /executions`
- `GET /executions/{id}`
- `GET /executions/{id}/events`

## UI transactions

- `GET /ui-transactions`
- `GET /ui-transactions/{id}`
- `POST /ui-transactions/{id}/respond`

## Resources and bookings

- `GET /resources`
- `POST /resources`
- `GET /resources/{id}`
- `PUT /resources/{id}`
- `DELETE /resources/{id}`
- `GET /bookings`
- `POST /bookings`
- `PUT /bookings/{id}`

## Connections and audit

- `GET /credentials`
- `POST /credentials`
- `DELETE /credentials/{id}`
- `GET /audit`
