#!/usr/bin/env python3
"""Verify and stage a public HF-M10 flash bundle from explicit build outputs.

No device access or device backups; GPT remains generated per unit, offline.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CONTRIB = ROOT / 'contrib/hf-m10'


def sha(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def one_image(directory, pattern):
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1 or not matches[0].is_file() or matches[0].is_symlink():
        raise ValueError('expected one regular image: ' + pattern)
    return matches[0]


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('images', 'uboot', 'config', 'seed', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--include-userdata', action='store_true')
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error('refusing to overwrite output')
    boot = one_image(args.images, '*-boot.img')
    rootfs = one_image(args.images, '*-rootfs.squashfs')
    specification = importlib.util.spec_from_file_location('uboot_builder', CONTRIB / 'build-uboot-no-recovery.py')
    builder = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(builder)
    uboot = args.uboot / builder.IMAGE_NAME
    expected_uboot = builder.build((ROOT / 'vendor/hf-m10/uboot-stock.img').read_bytes())
    if uboot.read_bytes() != expected_uboot:
        raise ValueError('U-Boot is not the pinned volume-up/no-Recovery derivative')
    uboot_report = json.loads((args.uboot / 'verification.json').read_text())
    if uboot_report['sha256'] != builder.OUTPUT_SHA256 or uboot_report['source_sha256'] != builder.STOCK_SHA256:
        raise ValueError('U-Boot provenance mismatch')
    boot_manifest = Path(str(boot) + '.manifest.json')
    pairing = json.loads(boot_manifest.read_text())
    if pairing['boot_sha256'] != sha(boot) or pairing['rootfs_padded_sha256'] != sha(rootfs):
        raise ValueError('Boot build manifest does not match the images')
    provenance = json.loads((ROOT / 'docs/hf-m10/provenance.json').read_text())
    feed_commits = {feed: git('-C', str(ROOT / 'feeds' / feed), 'rev-parse', 'HEAD')
                    for feed in ('packages', 'luci')}
    for feed, actual in feed_commits.items():
        if actual != provenance[feed + '_commit']:
            raise ValueError('unexpected feed revision: ' + feed)
    with tempfile.TemporaryDirectory(prefix='hf-m10-verify-') as temporary:
        verification = Path(temporary) / 'verification.json'
        subprocess.run([sys.executable, str(ROOT / 'scripts/cmcc-lotus-hf-m10/verify_images.py'),
                        '--boot', str(boot), '--rootfs', str(rootfs), '--output', str(verification)], check=True)
        # Only explicitly selected public files are staged, never the build tree
        # or private-backups/. The firmware artifact is uploaded only on success.
        args.output.mkdir(parents=True)
        for name in ('upgrade', 'maintenance/uboot', 'tools', 'metadata'):
            (args.output / name).mkdir(parents=True)

        def copy(source, destination):
            shutil.copyfile(source, args.output / destination)

        copy(boot, 'upgrade/boot.img')
        copy(rootfs, 'upgrade/rootfs.squashfs')
        copy(boot_manifest, 'upgrade/boot.img.manifest.json')
        copy(uboot, 'maintenance/uboot/uboot.img')
        copy(args.uboot / 'verification.json', 'maintenance/uboot/verification.json')
        copy(verification, 'metadata/firmware-verification.json')
        copy(args.config, 'metadata/build.config')
        copy(args.seed, 'metadata/config.seed')
        copy(ROOT / 'docs/hf-m10/FLASHING.md', 'README.md')
        for name in ('gpt-layout.py', 'serial-terminal.py', 'prepare-userdata-image.py'):
            copy(CONTRIB / name, 'tools/' + name)
        for name in ('profiles.json', 'config.buildinfo', 'feeds.buildinfo', 'version.buildinfo'):
            if (args.images / name).is_file():
                copy(args.images / name, 'metadata/' + name)

    images = []

    def record(role, filename, lba):
        path = args.output / filename
        images.append({'role': role, 'file': filename, 'start_lba': lba,
                       'bytes': path.stat().st_size, 'sha256': sha(path)})

    record('paired-boot', 'upgrade/boot.img', 0x4800)
    record('paired-rootfs', 'upgrade/rootfs.squashfs', 0xd000)
    record('uboot-maintenance-only', 'maintenance/uboot/uboot.img', 0x2000)
    if args.include_userdata:
        (args.output / 'first-install').mkdir()
        for sectors in (94175, 95711):
            filename = f'first-install/userdata-{sectors}-sectors.img'
            subprocess.run([sys.executable, str(CONTRIB / 'prepare-userdata-image.py'),
                            '--sectors', str(sectors), '--output', str(args.output / filename)], check=True)
            record('empty-userdata-first-install-only', filename, 0x1e800)
    manifest = {
        'device': 'cmcc-lotus-hf-m10', 'release': '25.12.5', 'kernel': provenance['kernel'],
        'source_commit': git('rev-parse', 'HEAD'), 'source_dirty': bool(git('status', '--porcelain', '--untracked-files=no')),
        'feeds': feed_commits, 'layout': 'no-recovery-17m', 'sector_size': 512,
        'usb_console': {'function': 'CDC ACM', 'baud': 115200, 'login': 'root password'},
        'gpt': 'Generate from this unit full offline NAND backup with tools/gpt-layout.py; no universal GPT included.',
        'upgrade_writes': ['paired-rootfs', 'paired-boot'],
        'hardware_acceptance': False, 'images': images,
    }
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    files = sorted(path for path in args.output.rglob('*') if path.is_file())
    (args.output / 'SHA256SUMS').write_text(''.join(
        sha(path) + '  ' + path.relative_to(args.output).as_posix() + '\n' for path in files))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
