# UI Payload and HITL Contract

UI payload blocks are ordinary workflow nodes. They expose selected block transactions without embedding React code into the workflow.

## Directions

### Inbound

Creates a transaction and pauses until a client supplies values. Typical uses: resource request forms, onboarding input and maintenance parameters.

### Outbound

Emits a persistent payload and continues immediately. Typical uses: progress, result cards, tables, errors and booking confirmation.

### Bidirectional

Emits context and pauses until a client returns one of the allowed actions. Typical uses: confirmation, modification, policy review and agent decisions.

### Human approval

A specialised bidirectional transaction with `approve` and `reject` branches and optional SMTP notification.

## Field schema

Supported reference-renderer field types:

- `text`
- `email`
- `number`
- `datetime`
- `textarea`
- `select`
- `boolean`
- `resource`

A customer frontend can ignore presentation hints and consume only keys, values and intent.

```json
{
  "fields": [
    {
      "key": "resource_id",
      "label": "Resource",
      "type": "resource",
      "required": true
    },
    {
      "key": "driver_policy",
      "label": "Driver target",
      "type": "select",
      "options": ["latest_compatible", "security_update_only"]
    }
  ]
}
```

## Template resolution

Block settings can reference runtime context:

```text
{{input.requested_by}}
{{nodes.request.resource_id}}
{{nodes.approval.approved}}
{{last.status}}
```

An exact token preserves the source JSON type. A token inside a longer string is converted to text.

## Transaction lifecycle

```text
open -> responded
open -> expired
outbound -> emitted
```

A response is single-use. Resubmission returns HTTP `409`.

## Client integration

A custom frontend should:

1. read the sandbox manifest;
2. subscribe to the sandbox event stream;
3. render schemas using its own design system;
4. submit the action and values to the transaction response endpoint;
5. reconnect with `Last-Event-ID` after network interruption.

AI agents use the same contract, but their attachment should receive only the scopes required for the assigned role.
