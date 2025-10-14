## Xen Genboot

`genboot.py` generates a U-Boot script that boots Xen in dom0-less mode based on a simple YAML configuration. Point it at the YAML and an output directory, and it will assemble the `fatload` commands and domain configuration you need.

### Prerequisites

- Python 3.8 or newer
- `pyyaml` installed (`pip install pyyaml`)

### Usage

```bash
python genboot.py example.yaml ./out
# or read the YAML from stdin
python genboot.py ./out < example.yaml
```

Each command reads the YAML configuration, resolves files from the output directory, and emits the U-Boot script to standard output. Ensure the output directory already contains the artifacts referenced by the configuration (e.g. Xen binary, device trees, kernels, ramdisks), then capture the generated script to a file or pipe it directly into your U-Boot tooling.

### Configuration

Inspect `example.yaml` for a minimal setup. The file describes media, Xen binary, device tree, and domU domains. Addresses accept both hex (e.g. `0x4000000`) and size suffixes (`512MiB`).

Key fields in `example.yaml`:

- `media`: physical boot device target (type/number) for all `fatload` commands.
- `dt`: device tree blob to load and its target address.
- `xen`: Xen binary path, boot arguments, load address, and optional dom0-less extras such as `colors` (first value applies to Xen, additional values to other domains; use `none` as the first value to skip Xen coloring) and `bootonly` (limit generated boot commands to selected domains instead of all).
- `domains`: per-domain entries with memory/CPU params plus kernel/device tree artifacts and load addresses.

### Test

To run tests, run:

```
pytest
```
