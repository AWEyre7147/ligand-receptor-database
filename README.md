# Ligand-Receptor Reference Database

A curated, reproducible reference database of ligand-receptor interactions for computational biology research.

## Purpose

This repository serves as a centralized resource for collecting, curating, validating, and distributing ligand-receptor interaction databases from multiple published sources.

The long-term goal is to provide a transparent and reproducible pipeline that:

- Retrieves publicly available ligand-receptor databases.
- Standardizes gene identifiers and interaction formats.
- Merges multiple databases into a unified reference.
- Validates and documents all processing steps.
- Produces versioned releases suitable for downstream analysis.

## Current Status

This repository is currently in the initialization phase.

Current functionality includes:

- Storage of source databases
- Preparation of analysis-ready datasets
- Development of reproducible processing scripts

Future work will include automated database updates, validation, curation, and release generation.

## Repository Structure

```
data/
    received/      Original source files (not tracked by Git)
    raw/           Imported datasets
    processed/     Analysis-ready datasets
    releases/      Versioned database releases

scripts/           Data preparation and update scripts

src/               Reusable Python modules

docs/              Documentation

notebooks/         Development notebooks
```

## License

This project is released under the MIT License.