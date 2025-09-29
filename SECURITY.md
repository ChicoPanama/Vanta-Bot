# Security Policy

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.1.x   | :white_check_mark: |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Reporting a Vulnerability

**Please do not open public issues for security vulnerabilities.**

If you discover a security vulnerability, please report it privately:

### Email Security Team
Send an email to: **security@avantis.trading**

Include the following information:
- Description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact assessment
- Any suggested fixes (optional)

### What to Report

Please report:
- Private key exposure or hardcoded secrets
- SQL injection vulnerabilities
- Authentication/authorization bypasses
- Remote code execution
- Data exposure or leakage
- Denial of service vulnerabilities
- Any other security-related issues

### What NOT to Report

Please do not report:
- Issues that require physical access to the server
- Social engineering attacks
- Issues in third-party dependencies (report to their maintainers)
- Issues that require admin/root access

## Security Measures

### Code Security
- All secrets are stored in environment variables
- No hardcoded API keys or private keys
- Input validation and sanitization
- SQL injection prevention
- Rate limiting on all endpoints

### Infrastructure Security
- Docker containers with minimal attack surface
- Non-root user execution
- Regular dependency updates
- Security scanning in CI/CD pipeline

### Key Management
- Private keys encrypted with AES-256
- KMS integration for production
- Key rotation capabilities
- Secure key storage

## Response Timeline

- **Initial Response**: Within 24 hours
- **Status Update**: Within 72 hours
- **Resolution**: Depends on severity (1-30 days)

## Recognition

We appreciate security researchers who help keep Vanta Bot secure. Contributors who report valid security issues will be acknowledged in our security advisories (with permission).

## Security Updates

Security updates are released as soon as possible after vulnerability confirmation. Critical issues may result in immediate patch releases.

## Contact

For security-related questions:
- Email: security@avantis.trading
- Discord: [Development Server](https://discord.gg/avantis-trading) (private channel)