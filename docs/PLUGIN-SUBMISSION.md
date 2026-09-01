# Reflow — Community Plugin Submission Guide

This document outlines how community developers can submit custom plugins to the Reflow Ecosystem Catalog.

---

## 1. Submission Requirements

Before submitting your plugin to `registry/registry.json`:
1. **Valid Manifest (`plugin.json`)**: Ensure all required manifest fields are specified (`id`, `name`, `version`, `plugin_type`, `api_version`, `capabilities`, `permissions`, `checksum`).
2. **Contract Compliance**: Implement the appropriate contract (`BasePlatformConnectorPlugin`, `BaseAIProviderPlugin`, `BaseStorageProviderPlugin`, `BaseMediaProcessorPlugin`, or `BaseWorkflowActionPlugin`).
3. **Unit Tests**: Provide a passing `test_plugin.py` verifying `health_check()` and plugin actions.
4. **Documentation**: Include a complete `README.md` with overview, installation, configuration, declared permissions, and development guide.
5. **Open Source License**: Provide an open-source license (e.g. MIT, Apache-2.0).

---

## 2. Pull Request Submission Workflow

1. Fork the official Reflow repository: `https://github.com/JayantOlhyan/Reflow`.
2. Add your plugin folder under `examples/plugins/your-plugin/` or point your catalog entry to your public GitHub repository.
3. Add a new entry to `registry/registry.json` with `source_type: "COMMUNITY"`.
4. Run local schema validation:
   ```bash
   python scripts/validate-registry.py
   ```
5. Submit a GitHub Pull Request. Automated CI (`.github/workflows/validate-registry.yml`) will validate your entry schema, semantic version, and checksum.
