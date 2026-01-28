import json

from anthropic import Anthropic

client = Anthropic()
MODEL = "claude-sonnet-4-5-20250929"

system = (
    "You are a support operations assistant. "
    "Return ONLY valid JSON with keys: summary, category, sentiment, risk, suggested_reply. "
    "risk must be a number 0 to 1."
)

user = {
    "ticket_id": "TEST-123",
    "subject": "Payment failed",
    "body": "Payment error 5001",
    "channel": "email",
    "priority": "high",
}

try:
    print("Making API call...")
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": json.dumps(user)}],
    )

    print(f"Response received: {resp}")
    print(f"Content blocks: {len(resp.content)}")

    text = ""
    for block in resp.content:
        print(f"Block type: {getattr(block, 'type', None)}")
        if getattr(block, "type", None) == "text":
            text += block.text

    print(f"Text extracted: {text[:500]}")
    print(f"Text length: {len(text)}")

    if text:
        result = json.loads(text)
        print("Parsed successfully!")
        print(json.dumps(result, indent=2))
    else:
        print("ERROR: No text extracted from response")

except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback

    traceback.print_exc()
