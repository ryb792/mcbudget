#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨引擎一致性测试：Python 引擎与 JS 引擎（演示页内嵌）对同一输入输出完全一致。

运行：python scripts/test_engine_parity.py
需要 node（仅用于运行 JS 版引擎做对比；缺失时跳过并说明）。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import budget_engine as be  # noqa: E402

CASES = [
    {"budget_cents": 2500, "order_type": "pickup", "prefs": ["鸡肉"], "excluded": ["咖啡"], "must": []},
    {"budget_cents": 3500, "order_type": "delivery", "prefs": [], "excluded": ["咖啡"], "must": []},
    {"budget_cents": 800, "order_type": "pickup", "prefs": [], "excluded": [], "must": []},
    {"budget_cents": 2500, "order_type": "pickup", "prefs": [], "excluded": ["咖啡"], "must": ["麦香鱼"]},
]

NODE_JS = """
const fs = require('fs');
require({engine_js!r});
const sample = JSON.parse(fs.readFileSync({sample_json!r}, 'utf8'));
const cases = {cases!r};
const out = cases.map(c => McBudgetEngine.buildLadder({{
  budget_cents: c.budget_cents, order_type: c.order_type,
  menu: sample.menu, sample: sample,
  prefs: c.prefs, excluded: c.excluded, must: c.must
}}));
fs.writeFileSync(process.argv[2], JSON.stringify(out));
"""


def main() -> int:
    node = shutil.which("node")
    if not node:
        candidates = sorted((Path.home() / ".workbuddy/binaries/node/versions").glob("*/node.exe"))
        node = str(candidates[-1]) if candidates else ""
    if not (os.path.exists(node)):
        print("跳过：未找到 node，无法运行 JS 引擎对比（Python 引擎测试见 run_tests.py）")
        return 0

    sample_path = os.path.join(ROOT, "assets", "sample_data.json")
    engine_path = os.path.join(HERE, "engine.js")
    with open(sample_path, encoding="utf-8") as f:
        sample = json.load(f)

    with tempfile.TemporaryDirectory() as td:
        script_path = os.path.join(td, "parity.js")
        out_path = os.path.join(td, "out.json")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(NODE_JS.format(engine_js=engine_path, sample_json=sample_path, cases=CASES))
        subprocess.run([node, script_path, out_path], check=True, capture_output=True)
        with open(out_path, encoding="utf-8") as f:
            js_results = json.load(f)

    ok = True
    for i, case in enumerate(CASES):
        ctx = {
            "budget_cents": case["budget_cents"],
            "order_type": case["order_type"],
            "menu": sample["menu"],
            "sample": sample,
            "prefs": case["prefs"],
            "excluded": case["excluded"],
            "must": case["must"],
        }
        py_out = be.build_ladder(ctx)
        same = json.dumps(py_out, sort_keys=True, ensure_ascii=False) == json.dumps(js_results[i], sort_keys=True, ensure_ascii=False)
        status = "ok  " if same else "FAIL"
        print(f"{status} 用例{i + 1} B={case['budget_cents'] / 100:g}元 {case['order_type']} prefs={case['prefs']} excluded={case['excluded']} must={case['must']}")
        if not same:
            ok = False
            print("  py:", json.dumps(py_out, ensure_ascii=False)[:300])
            print("  js:", json.dumps(js_results[i], ensure_ascii=False)[:300])
    print("结果：", "全部一致（演示页与 Python 引擎同构）" if ok else "存在不一致，需修复")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
