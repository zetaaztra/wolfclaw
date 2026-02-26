# Contributing to Wolfclaw

First off, thank you for considering contributing to **Wolfclaw**! It is a project built for the mission of digital sovereignty, and community involvement is vital to its evolution.

## Code of Conduct
By participating in this project, you are expected to uphold our [Code of Conduct](CODE_OF_CONDUCT.md).

## How Can I Contribute?

### Reporting Bugs
- Use the GitHub Issue Tracker.
- Provide a clear title and description.
- Include steps to reproduce and your environment details (OS, Python version).

### Suggesting Enhancements
- Open an issue with the tag `enhancement`.
- Describe the "why" — how does this feature empower the user?

### Pull Requests
1.  **Fork the repo** and create your branch from `main`.
2.  **Follow the style guide**: We use PEP 8 for Python.
3.  **Write Tests**: Ensure your changes don't break existing E2E flows (use `audit_runner.py`).
4.  **Update Docs**: If you change the API or core logic, update `guide.md`.

## Development Setup
1.  Install dev dependencies: `pip install -r requirements-dev.txt` (if exists).
2.  Set up a local Ollama instance for testing without API costs.
3.  Run the audit suite: `python audit_runner.py`.

## Attribution
Contributors who make significant impact may be invited to the "Sovereign Pack" listed in the `README.md`.

---
*Build with intent.* 🐺
