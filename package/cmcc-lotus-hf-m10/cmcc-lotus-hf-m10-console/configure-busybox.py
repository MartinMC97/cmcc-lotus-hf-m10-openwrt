#!/usr/bin/env python3
import pathlib
import re
import subprocess
import sys
bb=pathlib.Path(sys.argv[1]); seed=pathlib.Path(sys.argv[2]).read_text()
keys={line.split('=')[0] for line in seed.splitlines() if line.startswith('CONFIG_')}
lines=[line for line in (bb/'.config').read_text().splitlines() if (re.match(r'(?:# )?(CONFIG_\w+)',line) is None or re.match(r'(?:# )?(CONFIG_\w+)',line)[1] not in keys)]
(bb/'.config').write_text('\n'.join(lines)+'\n'+seed)
subprocess.run(['make','-C',str(bb),'oldconfig'],input='\n'*4096,text=True,check=True)
resolved=(bb/'.config').read_text().splitlines()
for line in seed.splitlines():
    if line.startswith('CONFIG_') and line not in resolved:
        raise ValueError('Required option missing: '+line)
