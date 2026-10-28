from pathlib import Path

root = Path(SPECPATH).resolve().parents[1]
a = Analysis(
    [str(root / "packaging/windows/desktop_entry.py")], pathex=[str(root)],
    datas=[(str(root / "ets/desktop/index.html"), "ets/desktop"),
           (str(root / "LICENSE"), "licenses"), (str(root / "NOTICE"), "licenses")],
    hiddenimports=["webview", "webview.platforms.edgechromium"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="ets-desktop",
          debug=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ets-desktop")
