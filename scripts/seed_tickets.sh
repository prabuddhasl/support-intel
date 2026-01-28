#!/usr/bin/env bash
set -euo pipefail

curl -sS -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Invalid password after reset",
    "body": "I reset my password twice but still get an invalid password error. I also never received the first reset email.",
    "channel": "email",
    "priority": "high",
    "customer_id": "CUST-1010"
  }'

curl -sS -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Lost my office keys",
    "body": "I lost my keys and think my dog ate them. Is there any way your team can help?",
    "channel": "email",
    "priority": "low",
    "customer_id": "CUST-9090"
  }'
