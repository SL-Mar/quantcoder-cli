# Security Policy

## Supported Versions

This is a legacy version of QuantCoder. While we aim to address critical security vulnerabilities, this branch is no longer actively maintained for new features.

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x (Legacy)   | :white_check_mark: Security fixes only |

## Recent Security Updates

### 2025-11-10 - Dependency Security Update

Updated all dependencies to address known vulnerabilities:

**Critical Fixes:**
- `cryptography` → 44.0.2+ (Multiple CVEs)
- `certifi` → 2025.1.31+ (Certificate bundle updates)

**High Priority:**
- `Pillow` → 11.1.0+ (Image processing vulnerabilities)
- `urllib3` → 2.3.0+ (HTTP security issues)

**Moderate Priority:**
- `Jinja2` → 3.1.6+ (Template injection fixes)
- `requests` → 2.32.3+ (General security improvements)
- `pydantic` → 2.10.6+ (Validation vulnerabilities)

**Note:** OpenAI SDK remains at v0.28 for compatibility. Newer versions (>=1.0) have breaking API changes.

## Reporting a Vulnerability

To report a security vulnerability, please:

1. **Do NOT** open a public issue
2. Email: smr.laignel@gmail.com with subject "QuantCoder Security"
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

We aim to respond within 5 business days.

## Security Best Practices

When using QuantCoder:

1. **API Keys**: Never commit `.env` files containing OpenAI API keys
2. **PDF Processing**: Only process PDFs from trusted sources
3. **Code Generation**: Review all generated code before deploying to QuantConnect
4. **Dependencies**: Regularly update to the latest secure versions
5. **Python Version**: Use Python 3.8 or later

## Known Limitations

- Uses legacy OpenAI SDK v0.28 (required for compatibility)
- PDF processing may have memory limitations on large files
- No sandboxing for generated code execution

## Migration Recommendation

For new projects, consider using the maintained version of QuantCoder instead of this legacy branch.
