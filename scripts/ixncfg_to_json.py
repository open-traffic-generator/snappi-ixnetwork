"""
Convert an IxNetwork .ixncfg config file to JSON by loading it into a live
IxNetwork session and using ResourceManager.ExportConfig.

Usage:
    python scripts/ixncfg_to_json.py <path-to.ixncfg> [output.json]

If output path is omitted, the JSON is written alongside the .ixncfg with a
.json extension.
"""

import json
import pathlib
import sys

from ixnetwork_restpy import SessionAssistant
from ixnetwork_restpy.files import Files

ADDRESS = "10.66.45.228"
REST_PORT = 443
USERNAME = ""
PASSWORD = ""


def connect():
    print(f"Connecting to IxNetwork at {ADDRESS}:{REST_PORT} ...")
    assistant = SessionAssistant(
        IpAddress=ADDRESS,
        RestPort=REST_PORT,
        UserName=USERNAME,
        Password=PASSWORD,
        ClearConfig=True,
        LogLevel=SessionAssistant.LOGLEVEL_WARNING,
    )
    ixnetwork = assistant.Ixnetwork
    print(f"Connected. Session: {assistant.Session.href}")
    return assistant, ixnetwork


def load_ixncfg(ixnetwork, ixncfg_path: str):
    print(f"Uploading and loading: {ixncfg_path}")
    ixnetwork.LoadConfig(Files(ixncfg_path, local_file=True))
    print("Config loaded.")


def export_json(ixnetwork) -> str:
    print("Exporting config as JSON via ResourceManager ...")
    json_str = ixnetwork.ResourceManager.ExportConfig(
        ["/descendant-or-self::*"],  # entire config tree
        True,                        # include default-valued attributes
        "json",                      # output format
    )
    print(f"Export complete ({len(json_str):,} chars).")
    return json_str


def main():
    if len(sys.argv) < 2:
        print("Usage: python ixncfg_to_json.py <config.ixncfg> [output.json]")
        sys.exit(1)

    ixncfg_path = sys.argv[1]
    output_path = (
        sys.argv[2]
        if len(sys.argv) > 2
        else str(pathlib.Path(ixncfg_path).with_suffix(".json"))
    )

    assistant, ixnetwork = connect()
    try:
        load_ixncfg(ixnetwork, ixncfg_path)
        json_str = export_json(ixnetwork)

        # Pretty-print the JSON before saving
        parsed = json.loads(json_str)
        pretty = json.dumps(parsed, indent=2)

        out = pathlib.Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(pretty, encoding="utf-8")
        print(f"Saved: {out}  ({out.stat().st_size:,} bytes)")
    finally:
        print("Removing session ...")
        assistant.Session.remove()
        print("Done.")


if __name__ == "__main__":
    main()
