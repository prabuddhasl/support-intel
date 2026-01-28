# AcmeCloud Support Knowledge Base (Sample)

## 1. Account & Access
### 1.1 Login Issues
#### Symptoms
- "Invalid password" errors
- Login loop after SSO redirect
- 2FA prompt repeatedly fails

#### Troubleshooting Steps
1. Confirm the user is entering the correct email address for the account.
2. If SSO is enabled, check IdP status and recent changes; managed accounts may need resets at the IdP.
3. Ask the user to clear browser cache/cookies and retry.
4. Have the user try an incognito/private window or another browser.
5. Check for content blockers/extensions that might interfere with login flows.

#### Escalation Criteria
- Any report of account takeover or suspicious login activity.
- Multiple users across the same org unable to log in.

### 1.2 Password Reset & Email Delivery
#### Common Causes
- Spam/quarantine rules or corporate filtering
- Incorrect email address or non-existent account
- SSO-managed accounts that don’t support direct resets

#### Troubleshooting Steps
1. Verify the email address is correct and corresponds to an existing account.
2. Ask the user to check spam/junk folders and any corporate quarantine.
3. If applicable, ask an admin to allowlist the sender domain.
4. Resend the reset link and ask the user to open it in a browser directly.
5. If SSO-managed, reset through the identity provider.

### 1.3 User Roles & Permissions
#### Role Definitions
- Viewer: read-only dashboards
- Analyst: can edit dashboards
- Admin: can manage users and exports

#### Common Issues
- "Export failed" often indicates the user is not an Admin.
- "Settings not found" may mean the user is a Viewer.

---

## 2. Billing & Subscriptions
### 2.1 Invoices & Charges
#### Duplicate Charges
- Verify payment processor logs.
- Check for multiple orgs under the same card.
- Escalate to Billing if duplicate charges are confirmed.

### 2.2 Refunds
#### Processing Time (Customer Expectations)
- Refunds typically appear in 5–10 business days, depending on the bank.
- Refunds can sometimes appear as reversals (original charge disappears).
- If the refund isn’t visible after 10 business days, ask the customer to contact their bank and provide transaction details.

---

## 3. Product & Platform
### 3.1 Dashboards
#### Blank Page or Broken UI
- Clear cache and cookies.
- Disable ad blockers or content-filtering extensions.
- Try an incognito/private window or another browser.
- Verify the user has at least Analyst permissions.

#### Slow Performance
- Check data source latency.
- Confirm query caching is enabled.
- Reduce dashboard widgets to under 12 per page.

### 3.2 Data Refresh
#### Missing Data
- Validate data source credentials.
- Run "Reconnect" in Settings.
- Confirm dataset schema matches field mappings.

#### Refresh Schedule
- Standard refresh runs every 60 minutes.
- Enterprise can configure 15-minute refresh.

### 3.3 Exports
#### Export Failures
- Only Admins can export data.
- Check for file size limits and permission errors.

---

## 4. Integrations
### 4.1 Supported Sources
- Salesforce
- HubSpot
- Google Analytics 4
- CSV Uploads

### 4.2 OAuth & API Keys
#### OAuth
- Reconnect after OAuth scope changes.
- If refresh fails, reauthorize the connection.

#### API Keys
- Confirm scope includes read access for reporting.
- If blocked, check IP allowlists.

---

## 5. Notifications & Alerts
### 5.1 Email Alerts
- Alerts are sent within 5 minutes of trigger.
- If delayed >15 minutes, check notification queue status.

### 5.2 Slack Alerts
- Slack workspace must be re-authorized after admin changes.
- Confirm the channel exists and bot has permission.

---

## 6. Security & Compliance
### 6.1 Data Retention
- Customer data is retained for 30 days after cancellation.

### 6.2 GDPR Requests
- Deletions processed within 30 days.
- Provide confirmation to the requestor and log the case.

### 6.3 Incident Response
- Any suspected breach must be escalated immediately.
- If a customer mentions "data loss" or "breach", mark High Risk.

---

## 7. SLA & Escalation
### 7.1 SLA Response Times
- P1 (critical outage): 1 hour
- P2 (major degradation): 4 hours
- P3 (minor issue): 1 business day

### 7.2 Escalation Rules
- Security incidents: page Security on-call immediately.
- Billing disputes: escalate to Billing within 1 business day.
- Enterprise customers: notify the assigned CSM.

---

## 8. Feature Requests
### 8.1 Intake Guidelines
- Categorize as "feature_request".
- Include customer ARR and urgency notes.

### 8.2 Roadmap Communication
- Roadmap updates are shared quarterly.
- Do not commit to delivery dates.

---

## 9. Customer Communication Standards
### 9.1 Tone
- Calm, empathetic, and concise.
- Avoid internal jargon.

### 9.2 Response Templates
- If outage is confirmed, link to the status page and provide ETA if available.
- For billing errors, acknowledge and confirm the invoice ID.
