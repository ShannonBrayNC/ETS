# Run from the repository root: python -m PyInstaller packaging/windows/verifier.spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).resolve().parents[1]
# ets.core resolves compatibility exports dynamically; static analysis misses these.
hidden = collect_submodules("ets.core")
a = Analysis(
    [str(root / "packaging/windows/verifier_entry.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "LICENSE"), "licenses"), (str(root / "NOTICE"), "licenses")],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="ets-verify",
    debug=False, strip=False, upx=False, console=True,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ets-verify")
