# Branching Strategy

## Default Branch
- `main`: production-ready, stable branch.

## Integration Branch
- `develop`: integration branch for completed feature merges.

## Feature Branches
Each major capability has its own branch:
- `feature/auth-rbac`
- `feature/doctor-approval`
- `feature/patient-workspace`
- `feature/documents-ocr`
- `feature/signature-workflow`
- `feature/frontend-executive-ui`
- `feature/api-hardening`

## Supporting Branches
- `devops/docker-ci`: deployment and CI/CD work
- `docs/pitch-deck`: documentation and presentation assets
- `release/v1.0.0`: release stabilization branch
- `hotfix/critical-fixes`: urgent production fixes

## Branch Flow
1. Create feature branch from `develop`
2. Open PR to `develop`
3. Run CI checks and peer review
4. Merge `develop` into `release/*` for release prep
5. Merge release to `main` after sign-off
6. Hotfixes branch from `main` and merge back to both `main` and `develop`

## Naming Convention
- `feature/<domain-capability>`
- `hotfix/<incident-or-ticket>`
- `release/v<semantic-version>`
- `docs/<artifact>`
- `devops/<scope>`
