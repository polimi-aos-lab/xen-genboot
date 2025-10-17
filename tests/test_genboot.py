import subprocess
import sys
from pathlib import Path


def test_genboot_produces_expected_script(tmp_path):
    """Ensure the generator processes example.yaml and produces the expected U-Boot script."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    # Create dummy binaries with known sizes so reg entries can be checked deterministically.
    for filename, size in {
        "xen.bin": 0x200,
        "bcm2712-rpi-5-b.dtb": 0x300,
        "guest1.bin": 0x400,
        "guest1.dtb": 0x180,
        "guest1.cpio.gz": 0x280,
    }.items():
        (artifacts_dir / filename).write_bytes(b"\0" * size)

    repo_root = Path(__file__).resolve().parent.parent
    yaml_path = repo_root / "example.yaml"
    script_path = repo_root / "genboot.py"

    result = subprocess.run(
        [sys.executable, str(script_path), str(yaml_path), str(artifacts_dir)],
        check=True,
        capture_output=True,
        text=True,
    )

    expected_lines = [
        "fatload mmc 0 0x01000000 xen.bin",
        "fatload mmc 0 0x02000000 bcm2712-rpi-5-b.dtb",
        "fatload mmc 0 0x03000000 guest1.bin",
        "fatload mmc 0 0x04000000 guest1.dtb",
        "fatload mmc 0 0x04800000 guest1.cpio.gz",
        "fatload mmc 0 0x05000000 guest1.bin",
        "fatload mmc 0 0x06000000 guest1.dtb",
        "fatload mmc 0 0x06800000 guest1.cpio.gz",
        "fdt addr 0x02000000",
        "fdt resize 2048",
        "",
        'fdt set /chosen stdout-path "serial0"',
        'fdt set /chosen xen,xen-bootargs "bootscrub=0 llc-coloring=on xen-llc-colors=0-1"',
        "",
        "",
        "fdt mknode /chosen domU1",
        'fdt set /chosen/domU1 compatible "xen,domain"',
        "fdt set /chosen/domU1 cpus <0x1>",
        "fdt set /chosen/domU1 \\#address-cells <0x1>",
        "fdt set /chosen/domU1 \\#size-cells <0x1>",
        "fdt set /chosen/domU1 memory <0x0 0xa>",
        "",
        "fdt set /chosen/domU1 vpl011",
        "fdt mknode /chosen/domU1 module@0x03000000",
        'fdt set /chosen/domU1 llc-colors "2-5"',
        'fdt set /chosen/domU1/module@0x03000000 compatible "multiboot,kernel" "multiboot,module"',
        "fdt set /chosen/domU1/module@0x03000000 reg <0x03000000 0x400>",
        "",
        'fdt set /chosen/domU1/module@0x03000000 bootargs "console=ttyAMA0"',
        "",
        "fdt mknode /chosen/domU1 module@0x04000000",
        'fdt set /chosen/domU1/module@0x04000000 compatible "multiboot,device-tree" "multiboot,module"',
        "fdt set /chosen/domU1/module@0x04000000 reg <0x04000000 384>",
        "",
        "",
        "fdt mknode /chosen/domU1 module@0x04800000",
        'fdt set /chosen/domU1/module@0x04800000 compatible "multiboot,ramdisk" "multiboot,module"',
        "fdt set /chosen/domU1/module@0x04800000 reg <0x04800000 0x280>",
        "",
        "fdt mknode /chosen domU2",
        'fdt set /chosen/domU2 compatible "xen,domain"',
        "fdt set /chosen/domU2 cpus <0x1>",
        "fdt set /chosen/domU2 \\#address-cells <0x1>",
        "fdt set /chosen/domU2 \\#size-cells <0x1>",
        "fdt set /chosen/domU2 memory <0x0 0xa>",
        "",
        "fdt set /chosen/domU2 vpl011",
        "fdt mknode /chosen/domU2 module@0x05000000",
        'fdt set /chosen/domU2 llc-colors "2-5"',
        'fdt set /chosen/domU2/module@0x05000000 compatible "multiboot,kernel" "multiboot,module"',
        "fdt set /chosen/domU2/module@0x05000000 reg <0x05000000 0x400>",
        "",
        'fdt set /chosen/domU2/module@0x05000000 bootargs "console=ttyAMA0"',
        "",
        "fdt mknode /chosen/domU2 module@0x06000000",
        'fdt set /chosen/domU2/module@0x06000000 compatible "multiboot,device-tree" "multiboot,module"',
        "fdt set /chosen/domU2/module@0x06000000 reg <0x06000000 384>",
        "",
        "",
        "fdt mknode /chosen/domU2 module@0x06800000",
        'fdt set /chosen/domU2/module@0x06800000 compatible "multiboot,ramdisk" "multiboot,module"',
        "fdt set /chosen/domU2/module@0x06800000 reg <0x06800000 0x280>",
        "",
        "fdt print /chosen",
        "booti 0x01000000 - 0x02000000",
    ]

    assert result.stdout.splitlines() == expected_lines


def test_genboot_includes_ramdisk_module(tmp_path):
    """Ensure ramdisk modules are emitted with the expected compatible and reg properties."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    files_and_sizes = {
        "xen.bin": 0x500,
        "board.dtb": 0x220,
        "guest_kernel.bin": 0x600,
        "guest.dtb": 0x180,
        "guest.cpio.gz": 0x700,
    }

    for filename, size in files_and_sizes.items():
        (artifacts_dir / filename).write_bytes(b"\0" * size)

    repo_root = Path(__file__).resolve().parent.parent
    yaml_path = repo_root / "tests" / "data" / "ramdisk_domain.yaml"
    script_path = repo_root / "genboot.py"

    result = subprocess.run(
        [sys.executable, str(script_path), str(yaml_path), str(artifacts_dir)],
        check=True,
        capture_output=True,
        text=True,
    )

    expected_lines = [
        "fatload mmc 2 0x01000000 xen.bin",
        "fatload mmc 2 0x01800000 board.dtb",
        "fatload mmc 2 0x02000000 guest_kernel.bin",
        "fatload mmc 2 0x02800000 guest.dtb",
        "fatload mmc 2 0x03000000 guest.cpio.gz",
        "fdt addr 0x01800000",
        "fdt resize 2048",
        "",
        "",
        "",
        "fdt mknode /chosen domU1",
        'fdt set /chosen/domU1 compatible "xen,domain"',
        "fdt set /chosen/domU1 cpus <0x2>",
        "fdt set /chosen/domU1 \\#address-cells <0x1>",
        "fdt set /chosen/domU1 \\#size-cells <0x1>",
        "fdt set /chosen/domU1 memory <0x0 0x8000>",
        "",
        "fdt mknode /chosen/domU1 module@0x02000000",
        'fdt set /chosen/domU1/module@0x02000000 compatible "multiboot,kernel" "multiboot,module"',
        "fdt set /chosen/domU1/module@0x02000000 reg <0x02000000 0x600>",
        "",
        "fdt mknode /chosen/domU1 module@0x02800000",
        'fdt set /chosen/domU1/module@0x02800000 compatible "multiboot,device-tree" "multiboot,module"',
        "fdt set /chosen/domU1/module@0x02800000 reg <0x02800000 384>",
        "",
        "",
        "fdt mknode /chosen/domU1 module@0x03000000",
        'fdt set /chosen/domU1/module@0x03000000 compatible "multiboot,ramdisk" "multiboot,module"',
        "fdt set /chosen/domU1/module@0x03000000 reg <0x03000000 0x700>",
        "",
        "fdt print /chosen",
        "booti 0x01000000 - 0x01800000",
    ]

    assert result.stdout.splitlines() == expected_lines


def test_genboot_generates_all_domains_with_unique_params(tmp_path):
    """Ensure the generator handles a multi-domain configuration with distinct parameters."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    files_and_sizes = {
        "xen-custom.bin": 0x500,
        "board-custom.dtb": 0x3a0,
        "console.bin": 0x600,
        "console.dtb": 448,
        "storage.bin": 0x700,
        "storage.dtb": 512,
        "network.bin": 0x800,
        "network.dtb": 576,
        "compute.bin": 0x900,
        "compute.dtb": 640,
    }

    for filename, size in files_and_sizes.items():
        (artifacts_dir / filename).write_bytes(b"\0" * size)

    repo_root = Path(__file__).resolve().parent.parent
    yaml_path = repo_root / "tests" / "data" / "all_domains.yaml"
    script_path = repo_root / "genboot.py"

    result = subprocess.run(
        [sys.executable, str(script_path), str(yaml_path), str(artifacts_dir)],
        check=True,
        capture_output=True,
        text=True,
    )

    expected_lines = [
        "fatload mmc 1 0x01000000 xen-custom.bin",
        "fatload mmc 1 0x02800000 board-custom.dtb",
        "fatload mmc 1 0x03800000 console.bin",
        "fatload mmc 1 0x04800000 console.dtb",
        "fatload mmc 1 0x05000000 storage.bin",
        "fatload mmc 1 0x06000000 storage.dtb",
        "fatload mmc 1 0x06800000 network.bin",
        "fatload mmc 1 0x07800000 network.dtb",
        "fatload mmc 1 0x08000000 compute.bin",
        "fatload mmc 1 0x09000000 compute.dtb",
        "fdt addr 0x02800000",
        "fdt resize 2048",
        "",
        'fdt set /chosen xen,xen-bootargs "bootscrub=0 iommu=on llc-coloring=on xen-llc-colors=0-3"',
        "",
        "",
        "fdt mknode /chosen domU1",
        'fdt set /chosen/domU1 compatible "xen,domain"',
        "fdt set /chosen/domU1 cpus <0x1>",
        "fdt set /chosen/domU1 \\#address-cells <0x1>",
        "fdt set /chosen/domU1 \\#size-cells <0x1>",
        "fdt set /chosen/domU1 memory <0x0 0x3000>",
        "",
        "fdt set /chosen/domU1 vpl011",
        "fdt mknode /chosen/domU1 module@0x03800000",
        'fdt set /chosen/domU1 llc-colors "4-5"',
        'fdt set /chosen/domU1/module@0x03800000 compatible "multiboot,kernel" "multiboot,module"',
        "fdt set /chosen/domU1/module@0x03800000 reg <0x03800000 0x600>",
        "",
        'fdt set /chosen/domU1/module@0x03800000 bootargs "console=ttyAMA0 root=/dev/vda"',
        "",
        "fdt mknode /chosen/domU1 module@0x04800000",
        'fdt set /chosen/domU1/module@0x04800000 compatible "multiboot,device-tree" "multiboot,module"',
        "fdt set /chosen/domU1/module@0x04800000 reg <0x04800000 448>",
        "",
        "",
        "fdt mknode /chosen domU2",
        'fdt set /chosen/domU2 compatible "xen,domain"',
        "fdt set /chosen/domU2 cpus <0x2>",
        "fdt set /chosen/domU2 \\#address-cells <0x1>",
        "fdt set /chosen/domU2 \\#size-cells <0x1>",
        "fdt set /chosen/domU2 memory <0x0 0x10000>",
        "",
        "fdt mknode /chosen/domU2 module@0x05000000",
        'fdt set /chosen/domU2 llc-colors "4-5"',
        'fdt set /chosen/domU2/module@0x05000000 compatible "multiboot,kernel" "multiboot,module"',
        "fdt set /chosen/domU2/module@0x05000000 reg <0x05000000 0x700>",
        "",
        'fdt set /chosen/domU2/module@0x05000000 bootargs "console=ttyS0 rdinit=/bin/sh"',
        "",
        "fdt mknode /chosen/domU2 module@0x06000000",
        'fdt set /chosen/domU2/module@0x06000000 compatible "multiboot,device-tree" "multiboot,module"',
        "fdt set /chosen/domU2/module@0x06000000 reg <0x06000000 512>",
        "",
        "",
        "fdt mknode /chosen domU3",
        'fdt set /chosen/domU3 compatible "xen,domain"',
        "fdt set /chosen/domU3 cpus <0x3>",
        "fdt set /chosen/domU3 \\#address-cells <0x1>",
        "fdt set /chosen/domU3 \\#size-cells <0x1>",
        "fdt set /chosen/domU3 memory <0x0 0xc000>",
        "",
        "fdt set /chosen/domU3 vpl011",
        "fdt mknode /chosen/domU3 module@0x06800000",
        'fdt set /chosen/domU3 llc-colors "4-5"',
        'fdt set /chosen/domU3/module@0x06800000 compatible "multiboot,kernel" "multiboot,module"',
        "fdt set /chosen/domU3/module@0x06800000 reg <0x06800000 0x800>",
        "",
        'fdt set /chosen/domU3/module@0x06800000 bootargs "console=ttyAMA1 ip=dhcp"',
        "",
        "fdt mknode /chosen/domU3 module@0x07800000",
        'fdt set /chosen/domU3/module@0x07800000 compatible "multiboot,device-tree" "multiboot,module"',
        "fdt set /chosen/domU3/module@0x07800000 reg <0x07800000 576>",
        "",
        "",
        "fdt mknode /chosen domU4",
        'fdt set /chosen/domU4 compatible "xen,domain"',
        "fdt set /chosen/domU4 cpus <0x4>",
        "fdt set /chosen/domU4 \\#address-cells <0x1>",
        "fdt set /chosen/domU4 \\#size-cells <0x1>",
        "fdt set /chosen/domU4 memory <0x0 0x20000>",
        "",
        "fdt mknode /chosen/domU4 module@0x08000000",
        'fdt set /chosen/domU4 llc-colors "4-5"',
        'fdt set /chosen/domU4/module@0x08000000 compatible "multiboot,kernel" "multiboot,module"',
        "fdt set /chosen/domU4/module@0x08000000 reg <0x08000000 0x900>",
        "",
        'fdt set /chosen/domU4/module@0x08000000 bootargs "console=ttyAMA2 isolcpus=2-3"',
        "",
        "fdt mknode /chosen/domU4 module@0x09000000",
        'fdt set /chosen/domU4/module@0x09000000 compatible "multiboot,device-tree" "multiboot,module"',
        "fdt set /chosen/domU4/module@0x09000000 reg <0x09000000 640>",
        "",
        "",
        "fdt print /chosen",
        "booti 0x01000000 - 0x02800000",
    ]

    assert result.stdout.splitlines() == expected_lines
