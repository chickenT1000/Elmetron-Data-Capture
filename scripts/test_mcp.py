"""Verify real stdio, including negotiation by a legacy host, for source or EXE."""
import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


async def current(command, args):
    async with Client(StdioServerParameters(command=command,args=args)) as client:
        tools=await client.list_tools()
        assert len(tools.tools)==8
        assert all(t.annotations.read_only_hint for t in tools.tools)
        result=await client.call_tool('get_status',{})
        assert not result.is_error and result.structured_content['access']=='read-only'
        resources=await client.list_resources()
        assert len(resources.resources)==2
        await client.read_resource('elmetron://openapi')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--exe',type=Path)
    parser.add_argument('--data-dir',type=Path,required=True)
    args=parser.parse_args()
    prefix=[str(args.exe.resolve())] if args.exe else [sys.executable,'-m','elmetron.cli.app']
    command=prefix[0];arguments=prefix[1:]+['--data-dir',str(args.data_dir.resolve()),'mcp']
    asyncio.run(current(command,arguments))
    request={'jsonrpc':'2.0','id':1,'method':'initialize','params':{
        'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'legacy-test','version':'1'}}}
    response=subprocess.run([command,*arguments],input=json.dumps(request)+'\n',text=True,encoding='utf-8',capture_output=True,timeout=30)
    messages=[json.loads(line) for line in response.stdout.splitlines() if line.strip()]
    initialized=next(m for m in messages if m.get('id')==1)
    assert 'error' not in initialized,initialized
    assert initialized['result']['protocolVersion']=='2025-11-25'
    print('MCP stdio: eight read-only tools, resources and legacy negotiation passed')


if __name__=='__main__': main()
