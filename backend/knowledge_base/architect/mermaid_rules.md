# ApexSoft Solutions - Mermaid Diagram Guidelines

To ensure that flowcharts and sequence diagrams render perfectly on the ApexSoft agile dashboard, the Architect Agent must follow these syntax rules:

## 1. Flowchart Syntax
*   Use the format `graph TD` (top-down) or `graph LR` (left-to-right).
*   Always quote node labels that contain spaces or special characters.
    *   **Correct**: `A["Initialize DB"] --> B["Start API Server"]`
    *   **Incorrect**: `A[Initialize DB] --> B[Start API Server]`

## 2. Sequence Diagram Syntax
*   Use the format `sequenceLine` or `sequenceDiagram`.
*   Specify participants clearly.
*   Keep messages short to prevent rendering overlaps.
*   Example format:
    ```mermaid
    sequenceDiagram
        User->>API: POST /login (username, password)
        API->>Database: Query user record
        Database-->>API: Return user hash
        API-->>User: 200 OK (Token)
    ```
