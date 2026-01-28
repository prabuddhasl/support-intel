TICKET_EVENT_SCHEMA_VERSION = 1

TICKET_EVENT_SCHEMA = {
    "type": "object",
    "required": [
        "schema_version",
        "event_id",
        "ticket_id",
        "ts",
        "subject",
        "body",
        "channel",
        "priority",
    ],
    "properties": {
        "schema_version": {"type": "integer", "enum": [TICKET_EVENT_SCHEMA_VERSION]},
        "event_id": {"type": "string", "minLength": 8},
        "ticket_id": {"type": "string", "minLength": 1},
        "ts": {"type": "string"},
        "subject": {"type": "string"},
        "body": {"type": "string"},
        "channel": {"type": "string"},
        "priority": {"type": "string"},
        "customer_id": {"type": "string"},
    },
    "additionalProperties": True,
}

ENRICHED_EVENT_SCHEMA_VERSION = 1

CATEGORY_ENUM = [
    "account_access",
    "billing",
    "security_incident",
    "data_refresh",
    "exports",
    "feature_request",
    "integration",
    "notifications",
    "general",
]

SENTIMENT_ENUM = ["positive", "neutral", "negative"]

ENRICHED_EVENT_SCHEMA = {
    "type": "object",
    "required": [
        "schema_version",
        "event_id",
        "ticket_id",
        "ts",
        "summary",
        "category",
        "sentiment",
        "risk",
        "suggested_reply",
    ],
    "properties": {
        "schema_version": {"type": "integer", "enum": [ENRICHED_EVENT_SCHEMA_VERSION]},
        "event_id": {"type": "string", "minLength": 8},
        "ticket_id": {"type": "string", "minLength": 1},
        "ts": {"type": "string"},
        "summary": {"type": "string"},
        "category": {"type": "string", "enum": CATEGORY_ENUM},
        "sentiment": {"type": "string", "enum": SENTIMENT_ENUM},
        "risk": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "suggested_reply": {"type": "string"},
    },
    "additionalProperties": True,
}
