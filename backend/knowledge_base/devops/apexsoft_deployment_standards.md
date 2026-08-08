# ApexSoft Solutions - DevOps and Deployment Standards

All deployment templates and workflows must follow these security and packaging requirements:

## 1. Docker Standards
*   Always use official, lightweight base images (e.g. `python:3.11-slim`, `node:20-alpine`).
*   **Security Requirement**: Containers must run as a non-root user. Always add a user (e.g., `appuser`) and group, and use the `USER` command.
    ```dockerfile
    RUN groupadd -r appgroup && useradd -r -g appgroup appuser
    USER appuser
    ```
*   Expose only required ports (e.g. port `8000` or `3000`).

## 2. CI/CD Standards
*   We use **GitHub Actions** for our workflow execution.
*   Every repository must have a `.github/workflows/pipeline.yml` pipeline that triggers on code pushes.
*   The pipeline must check out code, install dependencies, run pytest, and output test results.
