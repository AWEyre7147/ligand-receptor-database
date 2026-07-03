# AGENTS.md

## Repository Philosophy

This repository is intended to produce a high-quality, reproducible ligand-receptor reference database.

The emphasis is on transparency, reproducibility, and maintainability rather than simply generating a final dataset.

## Coding Principles

- Explain scientific reasoning whenever possible.
- Explain why code exists rather than simply what it does.
- Keep functions focused on a single responsibility.
- Prefer readable code over clever code.
- Avoid unnecessary abstraction.
- Use NumPy-style docstrings.
- Use type hints where practical.

## Documentation

Every public function should include:

- Purpose
- Parameters
- Returns
- Raises (when appropriate)

Major sections of scripts should use standardized section headers:

```python
# =============================================================================
# Section Title
# =============================================================================
```

## Data Principles

Never modify source data.

All processed datasets should be reproducible from the contents of `data/received/`.

Processing scripts should be deterministic whenever possible.

## Development Philosophy

Prefer building reusable tools over project-specific scripts.

When introducing new functionality:

1. Explain the scientific motivation.
2. Explain the implementation.
3. Keep the implementation as simple as practical.
4. Preserve reproducibility.