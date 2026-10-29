from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).resolve().parents[1]
a = Analysis(
    [str(root / "packaging/windows/developer_entry.py")], pathex=[str(root)],
    datas=[(str(root / "ets/desktop/index.html"), "ets/desktop"),
           (str(root / "ets/desktop/developer.html"), "ets/desktop"),
           (str(root / "ets/desktop/assets/sdk-test-kit.zip"), "ets/desktop/assets"),
           (str(root / "packaging/windows/developer-kit.json"), "ets/desktop/assets"),
           (str(root / "LICENSE"), "licenses"), (str(root / "NOTICE"), "licenses")],
    hiddenimports=["webview", "webview.platforms.edgechromium", *collect_submodules("ets.core")],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="ets-developer",
          debug=False, strip=False, upx=False, console=False,
          manifest=str(root / "packaging/windows/desktop.manifest"))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ets-developer")
