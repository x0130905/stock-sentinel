# Security Policy

Stock Sentinel deliberately has no bank, broker, order-entry, or credential-storage integration.

## Secret handling

- Keep API keys and mail authorization codes in environment variables or GitHub Secrets.
- Never commit `.env`; only `.env.example` belongs in the repository.
- Use SMTP authorization codes or app passwords, never a webmail login password.
- Logs redact values from the documented sensitive environment variables.
- The static PWA never receives backend secrets.

If a secret may have leaked, disable the monitoring workflow, revoke the credential at its provider, create a replacement, and update GitHub Secrets. Do not post secrets in a public issue.

## Scope

This software produces rule-based research signals only. It does not guarantee accurate, timely, or complete market data and it does not guarantee investment performance.
