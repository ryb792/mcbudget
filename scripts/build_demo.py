#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建自包含演示页：assets/demo_template.html + scripts/engine.js + assets/sample_data.json
→ demo/index.html（双击即可打开，无外网依赖、无 fetch）。

运行：python scripts/build_demo.py
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))


def main() -> int:
    with open(os.path.join(ROOT, "assets", "demo_template.html"), encoding="utf-8") as f:
        template = f.read()
    with open(os.path.join(HERE, "engine.js"), encoding="utf-8") as f:
        engine = f.read()
    with open(os.path.join(ROOT, "assets", "sample_data.json"), encoding="utf-8") as f:
        sample_json = json.dumps(json.load(f), ensure_ascii=False, indent=1)

    for token in ("/*__ENGINE_JS__*/", "/*__SAMPLE_DATA__*/null"):
        if token not in template:
            raise SystemExit(f"模板缺少占位符 {token}，构建中止")

    html = template.replace("/*__ENGINE_JS__*/", engine)
    html = html.replace("/*__SAMPLE_DATA__*/null", sample_json)

    out_dir = os.path.join(ROOT, "demo")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    size = os.path.getsize(out_path)
    print(f"已生成 {out_path}（{size / 1024:.1f} KB，自包含）")
    # 校验：不允许出现外网资源引用
    for bad in ("http://", "https://", "fetch(", "XMLHttpRequest"):
        if bad in html.replace("https://m-sit", ""):
            # 模板中允许出现的说明性 URL 只存在于注释里；正文含协议头则检查是否在注释
            occurrences = [i for i in range(len(html)) if html.startswith(bad, i)]
            print(f"提示：文本中出现 {bad!r} {len(occurrences)} 处，请确认全部位于注释或免责文案")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
