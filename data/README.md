---
configs:
- config_name: inputs
- config_name: truths

tira_configs:
    resolve_inputs_to: "."
    resolve_truths_to: "."
    baseline:
---

# Sample Datasets

This directory contains **synthetic datasets** for development and testing purposes only.

## kiddie/

A small fake dataset with 5 topics and 4 runs of varying quality. Useful for:
- Testing judge implementations
- Validating workflow configurations
- Quick iteration during development

## Real Datasets

For actual evaluation, obtain the official TREC datasets separately. See the main repository documentation for dataset sources and formats.