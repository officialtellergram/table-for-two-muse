"""CLI harness:  python -m agent.cli "Get four of us into Carbone this Saturday around eight"

Prints every tool call and result preview as the planner makes them, then the final
plan and token usage. `--tool NAME k=v ...` runs one tool directly without the model.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import config, planner, tools


def _kv(pairs: list[str]) -> dict:
    out = {}
    for p in pairs:
        k, _, v = p.partition("=")
        if v.isdigit():
            out[k] = int(v)
        else:
            out[k] = v
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agent.cli", description=__doc__.splitlines()[0])
    ap.add_argument("message", nargs="?", help="what the guest said")
    ap.add_argument("--city", default="nyc", help="default city key/label (default nyc)")
    ap.add_argument("--model", default=None, help=f"planner model (default {config.PLANNER_MODEL})")
    ap.add_argument("--json", action="store_true", help="emit the collected run as JSON instead of text")
    ap.add_argument("--quiet", action="store_true", help="only print the final plan")
    ap.add_argument("--tool", nargs="+", metavar="NAME k=v", help="run one tool directly, no model")
    ap.add_argument("--system", action="store_true", help="print the rendered system prompt and exit")
    a = ap.parse_args(argv)

    if a.system:
        print(planner.system_prompt(a.city))
        return 0
    if a.tool:
        print(json.dumps(tools.call(a.tool[0], _kv(a.tool[1:])), indent=2, ensure_ascii=False, default=str))
        return 0
    if not a.message:
        ap.error("message is required unless --tool or --system is given")

    if a.json:
        print(json.dumps(planner.ask(a.message, a.city, model=a.model), indent=2, ensure_ascii=False))
        return 0

    out = sys.stdout
    try:  # Windows consoles default to cp1252 and mangle the model's punctuation
        out.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    rc = 0
    for ev in planner.run(a.message, a.city, model=a.model):
        t = ev["type"]
        if t == "tool_call" and not a.quiet:
            out.write(f"-> {ev['name']} {json.dumps(ev['input'], ensure_ascii=False)}\n")
        elif t == "tool_result" and not a.quiet:
            flag = "ok" if ev["ok"] else "ERROR"
            out.write(f"<- {ev['name']} [{flag}, {ev['bytes']} B] {ev['preview'][:160]}\n")
        elif t == "text" and not a.quiet:
            out.write(f".. {ev['text']}\n")
        elif t == "usage" and not a.quiet:
            out.write(f"   round {ev['round']} {ev['model']} {ev['ms']} ms, in {ev['input_tokens']} "
                      f"out {ev['output_tokens']} cache {ev['cache_read']} stop={ev['stop_reason']}\n")
        elif t == "note":
            out.write(f"!! {ev['text']}\n")
        elif t == "final":
            out.write("\n" + ev["text"] + "\n")
            if not a.quiet:
                out.write(f"\n[{ev['rounds']} rounds, {ev['input_tokens']} in / {ev['output_tokens']} out]\n")
        elif t == "error":
            out.write(f"ERROR: {ev['text']}\n")
            rc = 1
        out.flush()
    return rc


if __name__ == "__main__":
    sys.exit(main())
