# Contributing to CFO Dashboard

**Thank you for considering contributing!**  
To keep our public repo professional and collaborative, please follow these rules:

## Branch Naming

- Use the following formats:
    - `feature/<short-description>` for new features
    - `fix/<short-description>` for bug fixes
    - `docs/<short-description>` for documentation
    - `hotfix/<short-description>` for urgent demo fixes
- Use lowercase, hyphens or underscores, and concise descriptions.
    - Examples: `feature/forecast-api`, `fix/rag-import-bug`

## Pull Requests

- **Title:** Must be clear, specific, and reference JIRA/issue if possible.
- **Complete the PR template:**  
  All items must be checked and fill in all info relevant to testing/demo.
- **Checklist includes:**
    - Functionality tested and works as described
    - Demo/screenshot or video attached (linked in JIRA task if possible)
    - All logic/commented for non-trivial code
    - All related JIRA/issues updated with this change
    - No secrets, credentials, or sensitive info present

## Code Style and Linting

- Function, class, and variable names must be Pythonic.
- Every function/class must have a Google-style docstring explaining arguments and logic.
- No unused variables/arguments/imports.
- These rules are enforced via CI.

## Recommended VS Code Editor Settings

Copy the following into your `.vscode/settings.json` in your project folder:

```json
{
    "editor.formatOnSave": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": [
        "--line-length=88"
    ],
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": false,
    "python.linting.pycodestyleEnabled": false,
    "ruff.args": [
        "--config=pyproject.toml"
    ]
}
```

## General Process

- PRs only; **never** commit directly to `main`.
- Keep PRs focused: one feature/fix per PR when possible.
- Pull from `main` before creating your PR branch.
- Assign a teammate as a PR reviewer.

## Security

- Never commit secrets, API keys, or proprietary business info.
- If you find a leak, alert a maintainer ASAP.

---

**PRs not following these guidelines require revision.
