# Security

Report security issues privately through GitHub's security advisory mechanism
for this repository. Include the version, reproduction steps and impact. Never
post API tokens or laboratory databases in an issue.

The beta binds HTTP to `127.0.0.1`. Mutations need the local bearer token or the
browser CSRF cookie/header. MCP is local stdio and exposes read-only tools.
The OS user and any host that launches MCP can read the selected archive.
Keep this service local; remote access and multi-user isolation are outside the
supported deployment. Token: `%LOCALAPPDATA%\Elmetron\config\api-token`.

There is no remote calibration tool or arbitrary SQL/shell MCP tool.
