# Security Policy

## Supported Versions

We actively support the following versions of the Liquid-Hive-Upgrade project:

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | :white_check_mark: |
| 1.x.x   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you believe you have found a security vulnerability in our project, please report it to us as described below.

### How to Report

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **security@liquid-hive.dev**

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

### What to Include

Please include the requested information listed below (as much as you can provide) to help us better understand the nature and scope of the possible issue:

- Type of issue (e.g. buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

### Our Response Process

1. **Acknowledge receipt** of your vulnerability report within 48 hours
2. **Confirm the problem** and determine the affected versions
3. **Audit code** to find any potential similar problems
4. **Prepare fixes** for all affected versions
5. **Release patched versions** and announce the security advisory

## Security Features

This project implements several security measures:

### Authentication & Authorization

- JWT token-based authentication
- API key authentication for service-to-service communication
- Role-based access control for admin endpoints
- Rate limiting per tenant

### Data Protection

- Input sanitization and validation
- PII detection and redaction
- Prompt injection detection
- Output safety filtering

### Infrastructure Security

- Container security with non-root user execution
- Secret management via environment variables or external secret stores
- HTTPS enforcement in production
- Security scanning via Trivy in CI/CD

### Monitoring & Auditing

- Comprehensive logging with structured format
- Security event monitoring via Prometheus metrics
- Audit trails for sensitive operations
- Circuit breakers for external service calls

## Security Best Practices for Contributors

### Code Security

- All dependencies are regularly updated via Dependabot
- Security linting is enforced via pre-commit hooks
- Code is scanned for vulnerabilities in CI/CD pipeline
- Secrets are never committed to the repository

### Access Control

- All admin endpoints require authentication
- Sensitive operations are logged and monitored
- API keys are rotated regularly
- Environment-specific configurations are isolated

### Testing

- Security test cases are included in the test suite
- Penetration testing is performed periodically
- Dependency vulnerabilities are tracked and addressed

## Disclosure Policy

When we receive a security bug report, we will:

1. Confirm the problem and determine the affected versions
2. Audit code to find any potential similar problems
3. Prepare fixes for all affected versions
4. Release new versions as soon as possible
5. Prominently feature the problem in the release notes

## Security Hall of Fame

We would like to thank the following individuals for responsibly disclosing security vulnerabilities:

- _No reports yet - be the first!_

## Additional Resources

- [OWASP Top Ten](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CIS Controls](https://www.cisecurity.org/controls/)

---

**Note**: This security policy is subject to change. Please check this page regularly for updates.
