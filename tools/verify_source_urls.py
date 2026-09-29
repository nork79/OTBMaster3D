"""Independently download each inventoried public archive and compare its hash."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def verify(entry):
    path = ROOT / 'release-materials/1.4.0-beta.2/sources' / entry['file']
    result = {'file': entry['file'], 'url': entry.get('url'), 'expected_sha256': entry['sha256'],
              'local_sha256': hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None}
    result['local_match'] = result['local_sha256'] == entry['sha256']
    if not entry.get('url'):
        result['public_status'] = 'No archive URL; retained original or exact Git archive; see source inventory'
        return result
    try:
        request = urllib.request.Request(entry['url'], headers={'User-Agent': 'OTBMaster3D-source-verification'})
        with urllib.request.urlopen(request, timeout=45) as response:
            digest, size = hashlib.sha256(), 0
            while data := response.read(1024*1024):
                digest.update(data)
                size += len(data)
            result.update(final_url=response.url, downloaded_bytes=size, downloaded_sha256=digest.hexdigest(),
                          public_status='MATCH' if digest.hexdigest() == entry['sha256'] else 'HASH MISMATCH')
    except Exception as exc:
        result.update(public_status='UNAVAILABLE', error=str(exc))
    return result


if __name__ == '__main__':
    inventory = json.loads((ROOT / 'docs/licensing/source-inventory.json').read_text())
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(verify, inventory['sources']))
    out = ROOT / 'docs/licensing/evidence/closure-source-url-checks.json'
    out.write_text(json.dumps({'sources': results, 'release_archive_urls': 'PENDING AUTHORIZED PUBLICATION'}, indent=2))
    print(json.dumps({'local_matches': sum(x['local_match'] for x in results),
                      'public_matches': sum(x['public_status'] == 'MATCH' for x in results),
                      'total': len(results), 'output': str(out)}, indent=2))
