#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a private-data-free challenge card from a real, officially priced ladder.

Usage: python scripts/render_card.py --input ladder.json --output result.html
       --quoted-at 2026-10-10T18:30:00+08:00 --tier B

The timestamp must describe the actual official quote, not HTML generation time.
The generated self-contained HTML can export its selected result as a PNG.
This renderer never queries MCP, claims coupons, creates orders, or pays.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "result_template.html"
DATA_MARKER = "__MCBUDGET_REAL_RESULT_JSON__"
TIER_PATTERN = re.compile(r"B(?:[+-]\d+(?:\.\d+)?)?\Z")
ORDER_TYPES = {"pickup": "到店取餐", "dt": "得来速", "delivery": "麦乐送"}


def integer(value: Any, field: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{field} 必须是大于等于 {minimum} 的整数")
    if value > 10**15:
        raise ValueError(f"{field} 超出支持范围")
    return value


def text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 180:
        raise ValueError(f"{field} 必须是 1–180 字的文字")
    value = " ".join(value.split())
    # Names come from the menu. Redact accidentally embedded contact details too.
    value = re.sub(r"https?://\S+", "[已隐藏链接]", value, flags=re.I)
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[已隐藏邮箱]", value)
    value = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", "[已隐藏手机号]", value)
    value = re.sub(r"(?<![\w])[A-Za-z0-9_-]{32,}(?![\w])", "[已隐藏标识]", value)
    return value


def timestamp(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} 缺失；请传实际核价时间 --quoted-at")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} 必须是带时区的 ISO 8601 核价时间") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} 必须包含时区，例如 +08:00")
    return parsed.isoformat(timespec="seconds")


def item(value: Any, field: str, allow_components: bool = True) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{field} 必须是餐品对象")
    result = {
        "name": text(value.get("name"), f"{field}.name"),
        "qty": integer(value.get("qty"), f"{field}.qty", 1),
    }
    if allow_components:
        components = value.get("combo_items") or []
        if not isinstance(components, list) or len(components) > 30:
            raise ValueError(f"{field}.combo_items 必须是最多 30 项的列表")
        # A component quantity is often absent in the normalized menu: one
        # component is a description of that meal, never an order quantity.
        result["combo_items"] = [
            item({"name": component.get("name"), "qty": component.get("qty", 1)},
                 f"{field}.combo_items[{i}]", False)
            if isinstance(component, dict) else _invalid_component(field)
            for i, component in enumerate(components)
        ]
    return result


def _invalid_component(field: str) -> Any:
    raise ValueError(f"{field}.combo_items 中的组成必须是对象")


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return f"{sign}{whole}" + (f".{fraction:02d}".rstrip("0") if fraction else "")


def compare(low: dict, high: dict) -> list[str]:
    """Rebuild display explanations from the whitelist, not raw input prose."""
    def names(plan: dict) -> dict[str, int]:
        output: dict[str, int] = {}
        for entry in plan["cart"]:
            description = entry["name"]
            if entry["combo_items"]:
                description += "（" + "、".join(
                    f"{component['name']}×{component['qty']}" for component in entry["combo_items"]
                ) + "）"
            output[description] = output.get(description, 0) + entry["qty"]
        return output

    before, after = names(low), names(high)
    changes = []
    for name in sorted(before.keys() | after.keys()):
        difference = after.get(name, 0) - before.get(name, 0)
        if difference:
            changes.append(f"{'增加' if difference > 0 else '减少'} {name} ×{abs(difference)}")
    output = ["；".join(changes) + "。" if changes else "餐单相同，增加预算未带来餐品变化。"]
    a, b = low["quote"], high["quote"]
    difference = b["payable_cents"] - a["payable_cents"]
    amounts = []
    for key, label in (("product_cents", "商品金额"), ("discount_cents", "优惠"), ("delivery_cents", "配送及打包费")):
        delta = b[key] - a[key]
        if delta:
            amounts.append(f"{label}{'增加' if delta > 0 else '减少'} ¥{money(abs(delta))}")
    if not difference:
        output.append("应付金额不变。" + ("；".join(amounts) + "。" if amounts else ""))
    else:
        output.append(f"应付由 ¥{money(a['payable_cents'])} 变为 ¥{money(b['payable_cents'])}"
                      f"（{'多花' if difference > 0 else '少花'} ¥{money(abs(difference))}）；"
                      + "；".join(amounts) + "。")
    output.append("差额来自餐单和官方核价，并非预算档位差额。")
    return output


def sanitize_result(data: Any, quoted_at: str | None = None, selected_tier: str = "B") -> dict:
    """Return only display fields; no original order/cart identifiers survive."""
    if not isinstance(data, dict) or data.get("mode") != "real":
        raise ValueError("仅接受 mode=real 的真实核价结果")
    order_type = data.get("order_type")
    if order_type not in ORDER_TYPES:
        raise ValueError("order_type 必须是 pickup/dt/delivery")
    budget = integer(data.get("budget_cents"), "budget_cents", 1)
    tiers = data.get("tiers")
    if not isinstance(tiers, list) or not 1 <= len(tiers) <= 3:
        raise ValueError("tiers 必须包含 1–3 档方案")
    fallback_time = quoted_at or data.get("quoted_at")
    if fallback_time is not None:
        fallback_time = timestamp(fallback_time, "quoted_at")
    safe_tiers = []
    seen = set()
    for index, tier in enumerate(tiers):
        field = f"tiers[{index}]"
        if not isinstance(tier, dict):
            raise ValueError(f"{field} 必须是对象")
        label = tier.get("label")
        if not isinstance(label, str) or not TIER_PATTERN.fullmatch(label) or label in seen:
            raise ValueError(f"{field}.label 非法或重复")
        seen.add(label)
        safe = {"label": label, "budget_cents": integer(tier.get("budget_cents"), field + ".budget_cents", 1)}
        if label == "B" and safe["budget_cents"] != budget:
            raise ValueError("B 档预算与 budget_cents 不一致")
        plan = tier.get("plan")
        if tier.get("status") != "priced" or not isinstance(plan, dict) or plan.get("status") != "priced":
            # Estimated/failed/unsolvable candidates have no displayed amounts.
            safe["status"] = "unavailable"
            safe_tiers.append(safe)
            continue
        quote = plan.get("quote")
        if not isinstance(quote, dict) or quote.get("estimated") or quote.get("mode") in ("demo", "sample"):
            raise ValueError(f"{field} 缺少真实官方核价")
        if "status" in quote and quote["status"] != "priced":
            raise ValueError(f"{field} 核价状态不是 priced")
        if quote.get("source") in ("demo_sample", "estimated", "quote_failed"):
            raise ValueError(f"{field} 核价来源不是成功的官方核价")
        safe_quote = {key: integer(quote.get(key), f"{field}.quote.{key}") for key in
                      ("product_cents", "discount_cents", "delivery_cents", "payable_cents")}
        if safe_quote["product_cents"] - safe_quote["discount_cents"] + safe_quote["delivery_cents"] != safe_quote["payable_cents"]:
            raise ValueError(f"{field} 官方核价金额不自洽")
        if safe_quote["payable_cents"] > safe["budget_cents"]:
            raise ValueError(f"{field} 应付金额超过该档预算")
        actual_time = quote.get("quoted_at") or plan.get("quoted_at") or fallback_time
        safe_quote["quoted_at"] = timestamp(actual_time, field + ".quote.quoted_at")
        cart = plan.get("cart")
        if not isinstance(cart, list) or not 1 <= len(cart) <= 30:
            raise ValueError(f"{field}.cart 必须包含 1–30 个餐品")
        safe.update({"status": "priced", "cart": [item(value, f"{field}.cart[{i}]") for i, value in enumerate(cart)], "quote": safe_quote})
        safe_tiers.append(safe)
    priced = [tier for tier in safe_tiers if tier["status"] == "priced"]
    if not priced:
        raise ValueError("没有 status=priced 的官方核价方案，不能生成挑战卡")
    if selected_tier not in {tier["label"] for tier in priced}:
        raise ValueError(f"所选 {selected_tier} 档没有成功的官方核价；请用 --tier 选择可用档位")
    safe_tiers.sort(key=lambda tier: tier["budget_cents"])
    priced.sort(key=lambda tier: tier["budget_cents"])
    return {
        "mode": "real", "budget_cents": budget, "order_type": order_type,
        "selected_tier": selected_tier, "tiers": safe_tiers,
        "deltas": [{"from": low["label"], "to": high["label"], "explanation": compare(low, high)}
                   for low, high in zip(priced, priced[1:])],
    }


def render_html(data: dict) -> str:
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # JSON is placed inside a non-executable script element. Escape markup and
    # JavaScript separators so user/menu text cannot close that element.
    for char, replacement in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                              ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        encoded = encoded.replace(char, replacement)
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(DATA_MARKER) != 1:
        raise ValueError("真实结果模板标记无效")
    return template.replace(DATA_MARKER, encoded)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从真实官方核价生成 McBudget PNG 挑战卡页面")
    parser.add_argument("--input", required=True, help="budget_engine.build_ladder 的真实结果 JSON")
    parser.add_argument("--output", required=True, help="生成的独立 HTML 文件")
    parser.add_argument("--quoted-at", help="实际核价时间（带时区 ISO 8601）；输入无 quoted_at 时必填")
    parser.add_argument("--tier", default="B", help="选定档位，如 B、B-5 或 B+5（默认 B）")
    args = parser.parse_args(argv)
    try:
        source = Path(args.input)
        destination = Path(args.output)
        if source.resolve() == destination.resolve():
            raise ValueError("输出文件不能覆盖输入 JSON")
        data = json.loads(source.read_text(encoding="utf-8-sig"))
        output = render_html(sanitize_result(data, args.quoted_at, args.tier))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(output, encoding="utf-8")
    except (ValueError, OSError) as exc:
        print(f"无法生成真实挑战卡：{exc}", file=sys.stderr)
        return 2
    print(f"已生成真实核价挑战卡页面：{destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
