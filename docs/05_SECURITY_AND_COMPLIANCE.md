# Security and Compliance Posture

## Current Security Controls
- Role-based access control across UI and API
- Object-level checks on patient data access
- Tokenized signature URLs with expiration
- CSRF protection enabled
- Password hashing via Django auth
- Signed artifact integrity hash (SHA-256)
- Action-level audit logs

## Data Protection Practices
- Secrets via environment variables
- No hard-coded credentials in source
- Segregated media storage with metadata in DB

## Compliance Readiness Notes
This project demonstrates key technical controls for auditability and integrity. For production healthcare compliance, add:
- at-rest encryption strategy
- key management policy
- audit retention and immutability policy
- strict access review cycles
- SIEM/SOC integration

## Recommended Hardening Next
1. Add 2FA for admin users
2. Add signed URL nonce replay protection
3. Add malware scanning on uploads
4. Add PII masking policy for logs
5. Add periodic permission recertification workflows
