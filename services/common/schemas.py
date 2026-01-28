TICKET_EVENT_SCHEMA = {
    "type": "object",
    "required": ["event_id", "ticket_id", "ts", "subject", "body", "channel", "priority"],
    "properties": {
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
