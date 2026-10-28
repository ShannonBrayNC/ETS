"""Dedicated Developer preview entry point; the standalone verifier stays unchanged."""

import json
import multiprocessing
import sys
from pathlib import Path

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        from ets.desktop.host import main

        raise SystemExit(main(developer=True))
    except Exception as exc:
        if "--smoke-result" in sys.argv:
            target = Path(sys.argv[sys.argv.index("--smoke-result") + 1])
            target.write_text(json.dumps({"status": 1, "detail": repr(exc)}), encoding="utf-8")
        elif sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0,
                "ETS could not start. Keep the complete application folder together.",
                "ETS Desktop Developer (Preview)",
                0x10,
            )
        raise SystemExit(1) from exc
