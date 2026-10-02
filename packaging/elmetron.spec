# Build from repository root: pyinstaller --noconfirm packaging/elmetron.spec
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

root = Path(SPECPATH).parent
resources = [(str(root/name), name) for name in ('ui/dist','config','docs','examples','assets','third_party')]
resources += [(str(root/name), '.') for name in ('LICENSE','NOTICE','README.md','openapi.json')]
resources += collect_data_files('mcp')
hidden = collect_submodules('mcp', filter=lambda name: not name.startswith('mcp.cli')) + ['elmetron.cli.app','waitress','tomlkit','reportlab','yaml']
desktop = Analysis([str(root/'launcher.py')],pathex=[str(root)],datas=resources,hiddenimports=hidden)
cli = Analysis([str(root/'elmetron_entry.py')],pathex=[str(root)],datas=resources,hiddenimports=hidden)
desktop_exe = EXE(PYZ(desktop.pure),desktop.scripts,[],exclude_binaries=True,name='Elmetron',console=False)
cli_exe = EXE(PYZ(cli.pure),cli.scripts,[],exclude_binaries=True,name='elmetron-cli',console=True)
COLLECT(desktop_exe,cli_exe,desktop.binaries,desktop.datas,cli.binaries,cli.datas,name='Elmetron')
