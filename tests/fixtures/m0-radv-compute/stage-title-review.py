# SPDX-License-Identifier: GPL-3.0-or-later

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile


FIXTURE = Path(__file__).resolve().parent
ROOT = FIXTURE.parents[2]
ELF = 'm0-radv-compute-link-only.elf'
LINK_REPORTS = (
    'elf-header.txt', 'elf-dynamic.txt', 'runtime-imports.txt',
    'import-stub-candidates.tsv',
)
WORKLOAD_SOURCES = ('compute.comp', 'compute.cpp', 'compute.hpp', 'CMakeLists.txt', 'cross-check.sh')
ENTRY_SOURCES = ('main.cpp', 'timing-main.cpp')
LINK_SOURCES = ('elf-link-check.sh', 'elf-link-inputs.txt', 'check-link-imports.py')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked_manifest(directory):
    subprocess.run(('sha256sum', '--strict', '--quiet', '-c', 'SHA256SUMS'), cwd=directory, check=True)
    return {name: checksum for checksum, name in
            (line.split('  ', 1) for line in (directory / 'SHA256SUMS').read_text().splitlines())}


def stage(primary, repeat, cross, output):
    if primary == repeat:
        raise ValueError('provide two separate PS5 link directories')
    if output.exists():
        raise FileExistsError(output)

    cross_checks = checked_manifest(cross)
    entries = [name for name in ENTRY_SOURCES if str(FIXTURE / name) in cross_checks]
    if len(entries) != 1:
        raise ValueError('cross-build must identify exactly one compute entry source')
    entry = entries[0]
    timing = entry == 'timing-main.cpp'
    cross_digest = digest(cross / 'SHA256SUMS')
    link_checks = checked_manifest(primary)
    repeat_checks = checked_manifest(repeat)
    if any(checks.get(str(cross / 'SHA256SUMS')) != cross_digest for checks in (link_checks, repeat_checks)):
        raise ValueError('link records must reference the supplied cross-build')
    for name in (ELF, *LINK_REPORTS, 'toolchain.txt', 'elf-archive-members.tsv', 'elf-link.map'):
        if link_checks[name] != repeat_checks[name]:
            raise ValueError(f'links disagree on {name}')

    archive_paths = {Path(name).name: Path(name) for name in cross_checks if Path(name).suffix == '.a'}
    radv = archive_paths['libvulkan_radeon.ps5.a']
    provenance = dict(line.split(': ', 1) for line in
                      (radv.parent.parent / 'PROVENANCE.txt').read_text().splitlines() if ': ' in line)
    if provenance['archive sha256'] != cross_checks[str(radv)]:
        raise ValueError('RADV provenance disagrees with the cross-build archive digest')

    archive_stats = (primary / 'elf-archive-members.tsv').read_text().splitlines()[1:]
    extracted = {}
    for row in archive_stats:
        members, selected, path = row.split('\t')
        if int(selected):
            extracted[Path(path).name] = {'members': int(members), 'selected': int(selected)}

    files = {
        f'binary/{ELF}': (primary / ELF, link_checks[ELF]),
        **{f'evidence/{name}': (primary / name, link_checks[name]) for name in LINK_REPORTS},
        'evidence/compute.spv': (cross / 'compute.spv', cross_checks['compute.spv']),
        'LICENSE': (ROOT / 'LICENSE', digest(ROOT / 'LICENSE')),
    }
    if not timing:
        verifier = 'tools/verify-m0-radv-compute.py'
        files[verifier] = (ROOT / verifier, digest(ROOT / verifier))
    dependency_table = (primary / 'elf-dynamic.txt').read_text()
    required_libraries = re.findall(r'\(NEEDED\).*\[([^\]]+)\]', dependency_table)
    if not required_libraries:
        raise ValueError('missing required-library declarations')
    source_files = {}
    workload_sources = (*WORKLOAD_SOURCES, entry)
    for names, checks in ((workload_sources, cross_checks), (LINK_SOURCES, link_checks)):
        for name in names:
            path = FIXTURE / name
            source_files[path.relative_to(ROOT).as_posix()] = checks[str(path)]
    manifest = {
        'schema_version': 1,
        'artifact_type': 'ps5_title_review',
        'name': 'ProsperoVK-Lab Compute Timing' if timing else 'ProsperoVK-Lab Compute Smoke',
        'application': {
            'display_name': 'ProsperoVK Lab',
            'internal_id': 'a5acce60-1153-47a5-8c89-80f3413d55fb',
        },
        'target': {'console': 'PS5 Slim', 'firmware': '13.60', 'hardware_status': 'NOT_RUN'},
        'title': {'id': None, 'package': None, 'launch_method': None, 'runtime_providers_verified': False},
        'workload': {'case_id': 'm0.radv.compute', 'spv_sha256': cross_checks['compute.spv']},
        'capture': {'stdout': 'result.json', 'stderr': 'start.log', 'exit_code': 'exit-code.txt'},
        'build': {
            'executable': f'binary/{ELF}', 'elf_sha256': link_checks[ELF],
            'cross_manifest_sha256': cross_digest,
            'link_records': 2,
            'lab_source_sha256': source_files,
            'radv': {'revision': provenance['revision'], 'assertions': provenance['assertions']},
            'sdk_revision': provenance['sdk'],
            'link_toolchain': [line for line in (primary / 'toolchain.txt').read_text().splitlines()
                               if not line.startswith('InstalledDir:')],
            'platform_source_sha256': {name: checksum for name, checksum in link_checks.items()
                                       if name.startswith('upstream/')},
            'archive_sha256': {name: cross_checks[str(path)] for name, path in archive_paths.items()},
            'archive_extraction': extracted,
            'link_map_sha256': link_checks['elf-link.map'],
            'required_runtime_libraries': required_libraries,
        },
        'license_review': {'lab_spdx': 'GPL-3.0-or-later', 'combined_title_review': 'PENDING'},
        'files_sha256': {name: checksum for name, (_, checksum) in files.items()},
    }
    if timing:
        manifest['workload']['mode'] = 'timing'
        manifest['capture'].update(report_schema_version=1, verbose_option='--verbose')

    # Stage and publish on the same filesystem without replacing an existing archive.
    with tempfile.TemporaryDirectory(dir=output.parent) as temp_dir:
        candidate = Path(temp_dir) / 'title-review.zip'
        with zipfile.ZipFile(candidate, 'x') as bundle:
            checksums = dict(manifest['files_sha256'])
            for name, (path, expected) in sorted(files.items()):
                checksum = hashlib.sha256()
                entry = zipfile.ZipInfo(name)
                entry.create_system = 3  # Unix mode bits in the ZIP directory.
                entry.external_attr = 0o100644 << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                with path.open('rb') as source, bundle.open(entry, 'w') as dest:
                    while chunk := source.read(1024 * 1024):
                        checksum.update(chunk)
                        dest.write(chunk)
                if checksum.hexdigest() != expected:
                    raise ValueError(f'{path.name} changed during export')

            payload = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
            bundle.writestr(zipfile.ZipInfo('manifest.json'), payload)
            checksums['manifest.json'] = hashlib.sha256(payload).hexdigest()
            bundle.writestr(zipfile.ZipInfo('SHA256SUMS'), ''.join(
                f'{checksum}  {name}\n' for name, checksum in sorted(checksums.items())))
        output.hardlink_to(candidate)


def main():
    parser = argparse.ArgumentParser(description='Create a local PS5 title review archive from verified link evidence.')
    for name in ('primary', 'repeat', 'cross', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    try:
        stage(args.primary.resolve(), args.repeat.resolve(), args.cross.resolve(), args.output.absolute())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Title review export failed: {error}\n')


if __name__ == '__main__':
    main()
