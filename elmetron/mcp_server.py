"""Read-only MCP adapter. No USB, SQL write or shell tools are exposed."""
from pathlib import Path
from typing import Any
from mcp.server import MCPServer
from mcp_types import ToolAnnotations
from .api.app import VERSION
from .data import DataRepository
from .paths import configuration, active_home, read_status, RESOURCE_ROOT


def create_server(home):
    home=Path(home)
    server=MCPServer('Elmetron',version=VERSION)
    annotations=ToolAnnotations(read_only_hint=True,destructive_hint=False,idempotent_hint=True,open_world_hint=False)
    def repo():
        return DataRepository(configuration(active_home(home)).storage.database_path)
    @server.tool(annotations=annotations, structured_output=True)
    def get_status() -> dict[str, Any]:
        """Read capture status. This never starts hardware or the browser."""
        import time
        status=read_status(home)
        if status.get('state') in ('running','starting','reconnecting') and time.time()-status.get('updated_at',0)>5:
            status.update(state='stale',detail='Capture heartbeat expired')
        return {**status,'version':VERSION,'access':'read-only'}
    @server.tool(annotations=annotations, structured_output=True)
    def list_instruments() -> dict[str, Any]:
        """Read known instruments from the active archive."""
        return {'instruments':repo().instruments()}
    @server.tool(annotations=annotations, structured_output=True)
    def list_sessions(limit: int=100,cursor: int=0,operator: str|None=None,start_date: str|None=None,end_date: str|None=None) -> dict[str, Any]:
        """List sessions. Follow next_cursor until null to retrieve all pages."""
        return repo().sessions(limit,cursor,operator=operator,start_date=start_date,end_date=end_date)
    @server.tool(annotations=annotations, structured_output=True)
    def get_session(session_id: int) -> dict[str, Any]:
        """Read a session's metadata, counts and instrument identity."""
        return repo().session(session_id)
    @server.tool(annotations=annotations, structured_output=True)
    def get_measurements(session_id: int,cursor: int=0,limit: int=1000,start: str|None=None,end: str|None=None,parameter: str|None=None) -> dict[str, Any]:
        """Read original and normalized measurements, units and time provenance. Follow next_cursor; maximum page size 1000."""
        return repo().measurements(session_id,cursor,limit,start,end,parameter)
    @server.tool(annotations=annotations, structured_output=True)
    def get_statistics(session_id: int,start: str|None=None,end: str|None=None,parameter: str|None=None) -> dict[str, Any]:
        """Compute statistics for the entire selected range, grouped by normalized unit."""
        return repo().statistics(session_id,start=start,end=end,parameter=parameter)
    @server.tool(annotations=annotations, structured_output=True)
    def get_markers(session_id: int) -> dict[str, Any]:
        """Read session markers; no changes are allowed."""
        return {'markers':repo().markers(session_id)}
    @server.tool(annotations=annotations, structured_output=True)
    def get_calibrations(session_id: int) -> dict[str, Any]:
        """Read records of calibrations performed manually on the instrument."""
        return {'calibrations':repo().markers(session_id,'calibration')}
    @server.resource('elmetron://capabilities')
    def capabilities() -> str:
        import json
        return json.dumps({'version':VERSION,'access':'read-only','transports':['stdio'],'model':'CX-505'})
    @server.resource('elmetron://openapi')
    def openapi() -> str:
        return (RESOURCE_ROOT/'openapi.json').read_text(encoding='utf-8')
    return server
