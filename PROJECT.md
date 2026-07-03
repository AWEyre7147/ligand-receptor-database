# Project

## Objective

Develop a reproducible, version-controlled reference database of ligand-receptor interactions for computational biology.

Rather than maintaining a static spreadsheet, this repository aims to create a complete data engineering pipeline capable of reproducing each database release from publicly available sources.

## Long-Term Goals

- Retrieve source databases automatically where possible.
- Import and standardize each database.
- Curate ligand-receptor interactions.
- Validate interaction integrity.
- Record database provenance.
- Produce reproducible versioned releases.
- Support downstream computational biology workflows.

## Initial Milestones

- [x] Create repository
- [ ] Establish repository structure
- [ ] Import initial Excel workbook
- [ ] Prepare analysis-ready datasets
- [ ] Develop reusable preparation scripts
- [ ] Build validation framework
- [ ] Investigate automated database updates

## Notes

The original source databases are preserved in `data/received/` and are intentionally excluded from version control.

Processed datasets should always be reproducible from the source data using the scripts contained in this repository.