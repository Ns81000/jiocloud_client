#!/usr/bin/env python3
"""
Example 06 — AI Agent Integration
Demonstrates the machine-readable tool interface that lets AI agents
(LLM function-calling, MCP hosts, RPA bots) autonomously operate Jio Cloud:
inspect, search, download, and manage files via strict JSON envelopes.

UNOFFICIAL PROJECT — personal backup / data-portability use only.
Not affiliated with Reliance Jio Infocomm Ltd. See DISCLAIMER.md.

Usage:
    python examples/06_agent_integration.py            # demo of safe read-only calls
    python examples/06_agent_integration.py --schema   # print the full tools schema
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from jiocloud import AGENT_TOOLS_SCHEMA, handle_tool_call


def main():
    if "--schema" in sys.argv:
        # Hand this array to any LLM 'tools' parameter (OpenAI/Anthropic format).
        print(json.dumps(AGENT_TOOLS_SCHEMA, indent=2))
        return

    print("=" * 70)
    print("AI AGENT INTEGRATION DEMO (read-only calls)")
    print("=" * 70)

    # 1) Account inventory -----------------------------------------------------
    call = {"tool": "account_info", "arguments": {}}
    print(f"\n> {json.dumps(call)}")
    res = handle_tool_call(call)
    print(json.dumps(res, indent=2)[:800])

    # 2) Recent activity -------------------------------------------------------
    call = {"tool": "recent_activity", "arguments": {}}
    print(f"\n> {json.dumps(call)}")
    res = handle_tool_call(call)
    items = res.get("result", []) if res.get("ok") else []
    print(f"  ok={res.get('ok')} | recent items returned: {len(items)}")

    # 3) List root files ---------------------------------------------------------
    call = {"tool": "list_files", "arguments": {"limit": 10}}
    print(f"\n> {json.dumps(call)}")
    res = handle_tool_call(call)
    for f in (res.get("result") or [])[:10]:
        print(f"  - {f['name']} ({f['human_size']}) key={f['object_key'][:12]}…")

    # 4) Destructive guard demonstration ----------------------------------------
    call = {"tool": "move_to_trash", "arguments": {"object_keys": ["x"], "confirm": False}}
    print(f"\n> Destructive op WITHOUT confirm: {json.dumps(call)}")
    res = handle_tool_call(call)
    print("  ->", json.dumps(res))  # must be confirmation_required, nothing deleted

    print("\nAgent bridge contract:")
    print('  request : {"tool": "<name>", "arguments": {...}}')
    print('  response: {"ok": true, "result": ...} | {"ok": false, "error": {...}}')
    print("\nDestructive tools (download_file, download_all, move_to_trash,")
    print("restore_from_trash, share_link) REQUIRE confirm=true.")
    print("\nMCP-style stdio server:  python cli.py agent serve")


if __name__ == "__main__":
    main()
