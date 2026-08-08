# ApexSoft Solutions - Python Coding Standards

All code written by developers must strictly adhere to these conventions:

## 1. PEP8 & Style
*   Use 4 spaces for indentation. Do not use tabs.
*   Functions, classes, and variables should have clear, readable snake_case names.
*   Classes must use PascalCase (e.g. `DatabaseConnection`).

## 2. Docstrings and Type Hinting
*   All functions, methods, and classes must have descriptive docstrings explaining their purpose, parameters, and return values.
*   Strict Python type hints are required for all function arguments and return types.
    *   **Correct**:
        ```python
        def calculate_sum(a: int, b: int) -> int:
            """Calculates the sum of two integers."""
            return a + b
        ```

## 3. Modular Programming
*   Keep functions short. Any function exceeding 50 lines must be split into sub-functions.
*   Always use structured logging (`import logging`) instead of `print` statements for tracking application events or warnings.
