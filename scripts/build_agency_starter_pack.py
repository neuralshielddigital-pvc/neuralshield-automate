"""Build the pinned Starter download from the owner's recovered files (offline)."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'backend/app/agency_resources/content'
MANIFEST = ROOT / 'docs/agency-starter-source-manifest.json'
OUTPUT_NAME = 'NeuralShield_Agency_Starter_Toolkit_V1.zip'
EXCLUDED = {
    'NSD_ACE_Start_Here_Welcome_and_Product_Map_V1.docx',
    'NSD_ACE_Start_Here_Welcome_and_Product_Map_V1.pdf',
    'NSD_ACE_TRN001_Quick_Start_and_Workflow_Walkthrough_Scripts_V1.docx',
    'NSD_ACE_TRN001_Quick_Start_and_Workflow_Walkthrough_Scripts_V1.pdf',
}


def build(source: Path, output: Path) -> None:
    manifest = json.loads(MANIFEST.read_text())
    names = {item['name'] for item in manifest}
    if len(manifest) != 41 or len(names) != 41 or not EXCLUDED <= names:
        raise ValueError('Unexpected recovered source manifest')
    payloads = {}
    # Verify all source files, including files deliberately not shipped.
    for item in sorted(manifest, key=lambda row: row['name']):
        name = item['name']
        if Path(name).name != name:
            raise ValueError('Source filename must not contain directories')
        data = (source / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError(f'Source checksum mismatch: {name}')
        if name not in EXCLUDED:
            payloads[f'Templates/{name}'] = data
    payloads['START_HERE.md'] = (CONTENT / 'starter-read-first.md').read_bytes()
    inventory = (
        'STARTER TOOLKIT CONTENTS\n\n'
        '37 original files in multiple formats. Some are format variants.\n'
        'Read START_HERE.md for package scope and suggested order.\n\n'
        + '\n'.join(sorted(payloads)) + '\n'
    )
    payloads['CONTENTS.txt'] = inventory.encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(payloads.items()):
            info = ZipInfo(name, date_time=(2026, 9, 18, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with ZipFile(output) as archive:
        if archive.testzip() is not None or len(archive.namelist()) != 39:
            raise ValueError('Invalid output archive')
    print(f'Built {output.name}: 37 source files + 2 package guides')
    print(f'SHA256 {hashlib.sha256(output.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=CONTENT / OUTPUT_NAME)
    args = parser.parse_args()
    build(args.source, args.output)
