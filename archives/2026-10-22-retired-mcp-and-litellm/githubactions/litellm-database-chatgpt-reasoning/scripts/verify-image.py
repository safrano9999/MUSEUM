#!/usr/bin/env python3
"""Run upstream recovery regressions against the official base and candidate."""
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

repo=Path.cwd()
manifest=json.loads((repo/'patches/manifest.json').read_text())
candidate=sys.argv[1]
base=manifest['base_image']+'@'+manifest['base_digest']
root=Path(os.environ['RUNNER_TEMP'])/'litellm-verification'
deps=root/'deps';reports=root/'reports';reports.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--target',str(deps),'pytest==8.4.2'],check=True)

def run(image, name, tests):
    subprocess.run(['docker','pull',image],check=True)
    args=['docker','run','--rm','--network','none','--user','0:0',
          '-e','LITELLM_LOCAL_MODEL_COST_MAP=True','-e','PYTEST_DISABLE_PLUGIN_AUTOLOAD=1',
          '-e','PYTHONPATH=/verification/deps',
          '-v',str(repo/'tests')+':/verification/tests:ro',
          '-v',str(deps)+':/verification/deps:ro',
          '-v',str(reports)+':/verification/reports',
          '-w','/verification','--entrypoint','python3',image,
          '-m','pytest','-q','--confcutdir=/verification/tests',
          '--junitxml=/verification/reports/'+name+'.xml',*tests]
    result=subprocess.run(args)
    report=ET.parse(reports/(name+'.xml')).getroot()
    return result.returncode,report

code,baseline=run(base,'official-base',['tests/test_chatgpt_stream_bridge.py'])
core=[c for c in baseline.iter('testcase') if c.get('name','').startswith('test_stream_bridge_recovers_empty_terminal_output[')]
assert code==1 and len(core)==4,'Expected sync/async item/text regressions not reproduced'
for case in core:
    failure=case.find('failure')
    assert failure is not None,'Baseline must reach the empty-output error'
    assert failure.get('message','')=='ValueError: Unknown items in responses API response: []','Unexpected baseline failure'
assert len(list(baseline.iter('failure')))==4,'An unrelated baseline control failed'
assert not list(baseline.iter('error')),'Baseline must fail assertions, not setup/import'
code,result=run(candidate,'patched',['tests/test_streaming_iterator_output_recovery.py','tests/test_chatgpt_responses_transformation.py','tests/test_chatgpt_stream_bridge.py'])
assert code==0 and not list(result.iter('failure')) and not list(result.iter('error')),'Patched runtime regressions failed'
assert len(list(result.iter('testcase')))>=43,'Missing upstream or end-to-end bridge regression coverage'
print(json.dumps({'status':'PASS','baseline_regression_reproduced':True,'patched_tests':len(list(result.iter('testcase')))}))
