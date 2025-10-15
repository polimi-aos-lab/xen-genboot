#!/usr/bin/env python3
"""
genboot.py - Generate U-Boot script from YAML configuration for Xen dom0-less boot

Usage:
    python genboot.py <yaml_file> <directory>
    python genboot.py <directory>  # YAML is read from stdin

This script generates a U-Boot script for booting Xen with dom0-less domains
based on a YAML configuration file. It loads the necessary files and configures
the device tree for the domains.
"""

import yaml
import os
import sys
import re

def parse_address_or_size(addr_str):
    """Convert address/size string to integer, supporting both hex and KiB/MiB/GiB suffixes"""
    if isinstance(addr_str, int):
        return addr_str

    addr_str = str(addr_str).strip()

    # Check if it's a hex number
    if addr_str.startswith('0x') or addr_str.startswith('0X'):
        return int(addr_str, 16)

    # Check for size suffixes
    multipliers = {
        'KiB': 1024,
        'MiB': 1024 * 1024,
        'GiB': 1024 * 1024 * 1024
    }

    for suffix, multiplier in multipliers.items():
        if addr_str.endswith(suffix):
            number = addr_str[:-len(suffix)].strip()
            return int(float(number) * multiplier)

    # If no suffix and not hex, treat as decimal number
    return int(addr_str)

def format_hex(value):
    """Format value as hexadecimal string"""
    if isinstance(value, str) and (value.startswith('0x') or value.startswith('0X')):
        return value
    return f"0x{value:08x}"

def get_file_size(directory, filename):
    """Get file size in bytes"""
    if not filename:
        return 0x100000

    filepath = os.path.join(directory, filename)
    if not os.path.exists(filepath):
        print(f"Warning: File {filepath} not found, using default size 0x100000", file=sys.stderr)
        return 0x100000
    return os.path.getsize(filepath)

def generate_uboot_script(config, directory):
    """Generate U-Boot script from YAML configuration"""
    script_lines = []

    # Load media configuration
    media = config.get('media', {})
    media_type = media.get('type', 'mmc')
    media_number = media.get('number', 0)

    # Load Xen binary
    xen = config.get('xen', {})
    xen_file = xen.get('file')
    xen_addr = format_hex(parse_address_or_size(xen.get('addr', '0x01000000')))

    if xen_file:
        script_lines.append(f"fatload {media_type} {media_number} {xen_addr} {xen_file}")

    # Load device tree
    dt = config.get('dt', {})
    dt_file = dt.get('file')
    dt_addr = format_hex(parse_address_or_size(dt.get('addr', '0x02000000')))

    if dt_file:
        script_lines.append(f"fatload {media_type} {media_number} {dt_addr} {dt_file}")

    # Determine which domains to boot
    domains_config = config.get('domains', {})
    bootonly = xen.get('bootonly')
    if bootonly is None:
        bootonly = list(domains_config.keys())

    # Load domain files
    for domain_name in bootonly:
        if domain_name not in domains_config:
            continue

        domain = domains_config[domain_name]

        # Load kernel
        kernel = domain.get('kernel', {})
        kernel_file = kernel.get('file')
        kernel_addr = format_hex(parse_address_or_size(kernel.get('addr', '0x03000000')))

        if kernel_file:
            script_lines.append(f"fatload {media_type} {media_number} {kernel_addr} {kernel_file}")

        # Load domain device tree
        domain_dt = domain.get('dt', {})
        domain_dt_file = domain_dt.get('file')
        domain_dt_addr = format_hex(parse_address_or_size(domain_dt.get('addr', '0x04000000')))

        if domain_dt_file:
            script_lines.append(f"fatload {media_type} {media_number} {domain_dt_addr} {domain_dt_file}")

        # Load domain ramdisk
        ramdisk = domain.get('ramdisk', {})
        ramdisk_file = ramdisk.get('file')
        ramdisk_addr = format_hex(parse_address_or_size(ramdisk.get('addr', '0x05000000')))

        if ramdisk_file:
            script_lines.append(f"fatload {media_type} {media_number} {ramdisk_addr} {ramdisk_file}")

    # FDT operations
    script_lines.append(f"fdt addr {dt_addr}")
    script_lines.append("fdt resize 2048")
    script_lines.append("")

    # Set Xen boot arguments
    xen_bootargs = xen.get('bootargs', '')
    xen_colors = xen.get('colors')

    # Build bootargs string
    bootargs_parts = []
    if xen_bootargs:
        bootargs_parts.append(xen_bootargs)

    # Handle LLC coloring logic:
    # - If colors is not present: no LLC configuration
    # - If colors[0] is "none": enable llc-coloring=on but no xen-llc-colors
    # - If colors[0] is valid: enable llc-coloring=on and set xen-llc-colors
    if xen_colors:
        bootargs_parts.append("llc-coloring=on")
        # Only add xen-llc-colors if first element is not "none"
        if len(xen_colors) > 0 and xen_colors[0] != "none":
            bootargs_parts.append(f"xen-llc-colors={xen_colors[0]}")

    if bootargs_parts:
        full_bootargs = " ".join(bootargs_parts)
        script_lines.append(f'fdt set /chosen xen,xen-bootargs "{full_bootargs}"')

    script_lines.append("")
    script_lines.append("")

    # Configure domains
    for i, domain_name in enumerate(bootonly, 1):
        if domain_name not in domains_config:
            continue

        domain = domains_config[domain_name]
        params = domain.get('params', {})

        # Create domain node
        script_lines.append(f"fdt mknode /chosen domU{i}")
        script_lines.append(f'fdt set /chosen/domU{i} compatible "xen,domain"')

        # Set CPUs
        cpus = params.get('cpus', 1)
        script_lines.append(f"fdt set /chosen/domU{i} cpus <0x{cpus:x}>")
        script_lines.append(f"fdt set /chosen/domU{i} \\#address-cells <0x1>")
        script_lines.append(f"fdt set /chosen/domU{i} \\#size-cells <0x1>")

        # Set memory
        memory = params.get('memory', '64MiB')
        memory_bytes = int(parse_address_or_size(memory) / 1024)
        script_lines.append(f"fdt set /chosen/domU{i} memory <0x0 0x{memory_bytes:x}>")
        script_lines.append("")

        # Set vpl011 if enabled
        if params.get('vpl011', False):
            script_lines.append(f"fdt set /chosen/domU{i} vpl011")

        # Create kernel module
        kernel = domain.get('kernel', {})
        kernel_addr = parse_address_or_size(kernel.get('addr', '0x03000000'))
        kernel_addr_hex = f"0x{kernel_addr:08x}"
        kernel_file = kernel.get('file')

        script_lines.append(f"fdt mknode /chosen/domU{i} module@{kernel_addr_hex}")

        # Set LLC colors for domain if available in xen config
        # Use colors starting from index 1 (skip first element which might be "none")
        if xen_colors and len(xen_colors) > 1:
            # Find first valid color range after index 0
            for color_idx in range(1, len(xen_colors)):
                if xen_colors[color_idx] != "none":
                    domain_colors = xen_colors[color_idx]
                    script_lines.append(f'fdt set /chosen/domU{i} llc-colors "{domain_colors}"')
                    break

        script_lines.append(f'fdt set /chosen/domU{i}/module@{kernel_addr_hex} compatible "multiboot,kernel" "multiboot,module"')

        # Calculate kernel size
        kernel_size = get_file_size(directory, kernel_file) if kernel_file else 0x100000
        script_lines.append(f"fdt set /chosen/domU{i}/module@{kernel_addr_hex} reg <{kernel_addr_hex} 0x{kernel_size:x}>")
        script_lines.append("")

        # Set kernel boot arguments
        kernel_bootargs = kernel.get('bootargs', '')
        if kernel_bootargs:
            script_lines.append(f'fdt set /chosen/domU{i}/module@{kernel_addr_hex} bootargs "{kernel_bootargs}"')
            script_lines.append("")

        # Create device tree module
        domain_dt = domain.get('dt', {})
        domain_dt_addr = parse_address_or_size(domain_dt.get('addr', '0x04000000'))
        domain_dt_addr_hex = f"0x{domain_dt_addr:08x}"
        domain_dt_file = domain_dt.get('file')

        if domain_dt_file:
            script_lines.append(f"fdt mknode /chosen/domU{i} module@{domain_dt_addr_hex}")
            script_lines.append(f'fdt set /chosen/domU{i}/module@{domain_dt_addr_hex} compatible "multiboot,device-tree" "multiboot,module"')

            # Calculate device tree size
            dt_size = get_file_size(directory, domain_dt_file)
            script_lines.append(f"fdt set /chosen/domU{i}/module@{domain_dt_addr_hex} reg <{domain_dt_addr_hex} {dt_size}>")
            script_lines.append("")
            script_lines.append("")

        # Create ramdisk module
        ramdisk = domain.get('ramdisk', {})
        ramdisk_addr_value = parse_address_or_size(ramdisk.get('addr', '0x05000000'))
        ramdisk_addr_hex = f"0x{ramdisk_addr_value:08x}"
        ramdisk_file = ramdisk.get('file')

        if ramdisk_file:
            script_lines.append(f"fdt mknode /chosen/domU{i} module@{ramdisk_addr_hex}")
            script_lines.append(f'fdt set /chosen/domU{i}/module@{ramdisk_addr_hex} compatible "multiboot,ramdisk" "multiboot,module"')

            ramdisk_size = get_file_size(directory, ramdisk_file)
            script_lines.append(f"fdt set /chosen/domU{i}/module@{ramdisk_addr_hex} reg <{ramdisk_addr_hex} 0x{ramdisk_size:x}>")
            script_lines.append("")

    # Final commands
    script_lines.append("fdt print /chosen")
    script_lines.append(f"booti {xen_addr} - {dt_addr}")

    return "\n".join(script_lines)

def main():
    args = sys.argv[1:]

    usage_msg = (
        "Usage:\n"
        "  python genboot.py <yaml_file> <directory>\n"
        "  python genboot.py <directory>  # YAML is read from stdin"
    )

    if len(args) == 2:
        yaml_file, directory = args
        if not os.path.exists(yaml_file):
            print(f"Error: YAML file {yaml_file} not found", file=sys.stderr)
            sys.exit(1)

        with open(yaml_file, "r", encoding="utf-8") as yaml_stream:
            config = yaml.safe_load(yaml_stream)

    elif len(args) == 1:
        directory = args[0]
        if sys.stdin.isatty():
            print("Error: No YAML input provided on stdin", file=sys.stderr)
            sys.exit(1)

        config = yaml.safe_load(sys.stdin)
    else:
        print(usage_msg, file=sys.stderr)
        sys.exit(1)

    if config is None:
        print("Error: YAML configuration is empty", file=sys.stderr)
        sys.exit(1)

    if not os.path.isdir(directory):
        print(f"Error: Directory {directory} not found", file=sys.stderr)
        sys.exit(1)

    try:
        script_content = generate_uboot_script(config, directory)
        print(script_content)
    except Exception as e:
        print(f"Error generating script: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
