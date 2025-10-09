## Xen Genboot

`genboot.py` generates a U-Boot script that boots Xen in dom0-less mode based on a simple YAML configuration. Point it at the YAML and an output directory, and it will assemble the `fatload` commands and domain configuration you need.

### Prerequisites
- Python 3.8 or newer
- `pyyaml` installed (`pip install pyyaml`)

### Usage
```bash
python genboot.py example.yaml ./out
```
The command reads the YAML file, resolves files from the output directory, and emits the U-Boot script to standard output. Capture it to a file or pipe it directly into your U-Boot tooling.

### Configuration
Inspect `example.yaml` for a minimal setup. The file describes media, Xen binary, device tree, and domU domains. Addresses accept both hex (e.g. `0x4000000`) and size suffixes (`512MiB`).
