"""One summary per existing build; no polling or additional scheduled job."""
import json
import os
from pathlib import Path
from delivery_package import ROOT


def compare(previous,current):
    growth={key:count-previous.get('by_generator',{}).get(key,0) for key,count in current['by_generator'].items() if count>previous.get('by_generator',{}).get(key,0)}
    return {'files':current['files'],'previous_files':previous.get('files'),'growth_by_generator':growth,
            'unexpected_growth':bool(previous and current['files']>previous.get('files',0)*1.15)}


def main():
    path=ROOT/'build/output-report.json';current=json.loads(path.read_text())
    prior=ROOT/'build/previous-output-report.json';previous=json.loads(prior.read_text()) if prior.exists() else {}
    result=compare(previous,current)
    package_path=ROOT/'build/r2-package/package.json'
    if package_path.exists():
        package=json.loads(package_path.read_text());result.update({'r2_routes':package['routes'],'r2_package_bytes':package['bytes'],'unique_r2_objects':len(package['files'])})
    print(json.dumps(result))
    if result['unexpected_growth']:print('::warning::Output grew more than 15%; responsible generators: '+json.dumps(result['growth_by_generator']))
    summary=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as out:
            out.write('## Deployment inventory\n\n'+f"Rendered files: {current['files']}; bytes: {current['bytes']}.\n\n")
            out.write('| Generator | Files |\n| --- | ---: |\n'+''.join(f'| {name} | {count} |\n' for name,count in sorted(current['by_generator'].items())))
            out.write('\nFile types: `'+json.dumps(current['by_type'])+'`\n\nGrowth: `'+json.dumps(result)+'`\n')
    prior.write_text(json.dumps(current,sort_keys=True)+'\n')

if __name__=='__main__':main()
