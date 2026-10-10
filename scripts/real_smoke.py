#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""McBudget 真实模式冒烟验证：直连麦当劳 MCP（Streamable HTTP）验证
now-time-info → query-nearby-stores → query-meals → 预算阶梯(真实算价)。

- Token 来源：跨客户端首选环境变量 MCD_MCP_TOKEN；仍兼容回退到
  ~/.workbuddy/mcp.json 的 mcpServers.mcd-mcp.headers.Authorization（Bearer xxx）。
  WorkBuddy、Codex 等客户端的配置示例见 README.md。Codex 通过
  bearer_token_env_var 引用该环境变量，本脚本不自动扫描其 TOML，不打印 Token。
- 只做读操作（门店/菜单/算价），不领券、不下单。真实对话流程会在构建候选前
  先执行 auto-bind-coupons 领券（写操作），再 query-store-coupons 进入算价；
  本脚本为保持只读跳过领券步骤。
- 城市与门店可传参覆盖；默认沿用开发时实测的肇庆市端州区门店。

运行：python scripts/real_smoke.py --budget 25 --pref 鸡肉 --exclude 咖啡
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import budget_engine as be  # noqa: E402

MCP_URL = "https://mcp.mcd.cn"
_ID = [0]


def load_token() -> str:
    tok = os.environ.get("MCD_MCP_TOKEN", "").strip()
    if tok:
        return tok
    cfg = Path.home() / ".workbuddy" / "mcp.json"
    if cfg.exists():
        data = json.loads(cfg.read_text(encoding="utf-8"))
        auth = ((data.get("mcpServers") or {}).get("mcd-mcp") or {}).get("headers", {}).get("Authorization", "")
        m = re.match(r"Bearer\s+(.+)", auth)
        if m:
            return m.group(1).strip()
    raise SystemExit("未找到 MCP Token：请优先设置环境变量 MCD_MCP_TOKEN；WorkBuddy、Codex 等客户端配置见 README.md。仍兼容 ~/.workbuddy/mcp.json 的 mcd-mcp 配置。")


def call_tool(token: str, name: str, arguments: dict) -> dict:
    _ID[0] += 1
    body = json.dumps({
        "jsonrpc": "2.0", "id": _ID[0], "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }).encode("utf-8")
    req = urllib.request.Request(
        MCP_URL, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    payload = raw.strip()
    # 兼容 SSE（data: {...}）与纯 JSON 两种返回
    if payload.startswith("data:") or "\ndata:" in payload or "\r\ndata:" in payload:
        lines = [ln[5:].strip() for ln in payload.splitlines() if ln.startswith("data:")]
        payload = lines[-1] if lines else "{}"
    obj = json.loads(payload)
    if obj.get("error"):
        raise RuntimeError(f"MCP error: {json.dumps(obj['error'], ensure_ascii=False)[:400]}")
    content = obj.get("result", {}).get("content", [])
    texts = [c.get("text", "") for c in content if c.get("type") == "text"]
    return {"_text": "\n".join(texts), "_json": _try_json("\n".join(texts))}


def _try_json(text: str):
    """工具 text 内容是『说明文本 + 业务 JSON』混合体；从中提取第一个含 success/data 的 JSON 对象。"""
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _end = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and ("success" in obj or "data" in obj or "error" in obj):
            return obj
    return None


def unwrap(call_result: dict) -> dict:
    """tools/call 的 text 内容通常为业务 JSON：{success, code, message, data}。"""
    data = call_result.get("_json")
    if isinstance(data, dict) and ("data" in data or data.get("success") is False):
        if data.get("success") is False:
            raise RuntimeError(f"业务失败: {json.dumps(data, ensure_ascii=False)[:300]}")
        return data.get("data") or {}
    raise RuntimeError("返回不是预期的业务 JSON 结构，请核对 references/mcp_tools.md")


def main() -> int:
    ap = argparse.ArgumentParser(description="McBudget 真实模式冒烟验证（只读）")
    ap.add_argument("--budget", type=str, default="25")
    ap.add_argument("--order-type", choices=["pickup", "dt"], default="pickup",
                    help="pickup 到店(beType=1) / dt 得来速(beType=5)；此脚本不执行外送验证")
    ap.add_argument("--pref", action="append", default=[])
    ap.add_argument("--exclude", action="append", default=[])
    ap.add_argument("--must", action="append", default=[])
    ap.add_argument("--city", default="肇庆市")
    ap.add_argument("--keyword", default="端州三路")
    ap.add_argument("--store-code", default=None, help="跳过门店查询，直接用该门店")
    ap.add_argument("--be-code", default=None)
    args = ap.parse_args()

    token = load_token()
    print("== 1. now-time-info ==")
    t = call_tool(token, "now-time-info", {})
    print((t["_text"] or "")[:200])

    store_code, be_code = args.store_code, args.be_code
    be_type = "5" if args.order_type == "dt" else "1"
    if not store_code:
        print(f"\n== 2. query-nearby-stores(city={args.city}, keyword={args.keyword}, beType={be_type}) ==")
        res = call_tool(token, "query-nearby-stores", {
            "searchType": "2", "beType": be_type, "city": args.city, "keyword": args.keyword,
        })
        stores = unwrap(res)
        if not stores:
            raise SystemExit("附近无可用门店")
        first = stores[0]
        store_code, be_code = first.get("storeCode"), first.get("beCode")
        print(f"选用门店：{first.get('storeName')} storeCode={store_code} beCode={be_code}")
    print(f"\n门店上下文：storeCode={store_code} beCode={be_code} beType={be_type} orderType=1")

    print("\n== 3. query-meals ==")
    qm_args = {"storeCode": store_code, "orderType": "1", "beType": be_type}
    if be_code:
        qm_args["beCode"] = be_code
    res = call_tool(token, "query-meals", qm_args)
    data = unwrap(res)
    menu = be.adapt_query_meals(data)
    if not menu:
        raise SystemExit(f"菜单为空。原始返回片段：{json.dumps(data, ensure_ascii=False)[:400]}")
    print(f"适配菜单 {len(menu)} 项（内部单位：分）；前 6 项：")
    for m in menu[:6]:
        print(f"  [{m['category']}] {m['name']} ¥{be.format_yuan(m['price_cents'])}")

    print("\n== 4. 预算阶梯（真实算价） ==")
    ctx = {
        "budget_cents": be.to_cents(args.budget, "user_yuan"),
        "order_type": args.order_type,
        "menu": menu,
        "sample": None,
        "prefs": args.pref,
        "excluded": args.exclude,
        "must": args.must,
        "delivery_fee_cents": 0,  # 真实配送费由 calculate-price 返回，不预设
    }

    quote_stats = {"calls": 0, "failed": 0}

    def quote_fn(cart):
        items = [{"productCode": i["code"], "quantity": i["qty"]} for i in cart]
        cp_args = {"storeCode": store_code, "orderType": "1", "beType": be_type, "items": items}
        if be_code:
            cp_args["beCode"] = be_code
        quote_stats["calls"] += 1
        try:
            qdata = unwrap(call_tool(token, "calculate-price", cp_args))
            return be.adapt_quote(qdata, cart)
        except Exception as e:  # noqa: BLE001 —— 单次核价失败标记 quote_failed，不中断
            quote_stats["failed"] += 1
            print(f"  [quote_failed] {be.cart_signature(cart)}: {str(e)[:160]}")
            return None

    result = be.build_ladder(ctx, quote_fn=quote_fn)
    print(f"候选 {result['meta']['candidate_count']} 个；官方算价 {quote_stats['calls']} 次（失败 {quote_stats['failed']}）")
    for tier in result["tiers"]:
        if tier.get("plan"):
            q = tier["plan"]["quote"]
            items = " + ".join(i["name"] for i in tier["plan"]["cart"])
            print(f"  {tier['label']} (≤¥{be.format_yuan(tier['budget_cents'])}) [{tier['plan']['status']}] {items}")
            print(f"      商品 ¥{be.format_yuan(q['product_cents'])} 优惠 -¥{be.format_yuan(q['discount_cents'])} 配送 ¥{be.format_yuan(q['delivery_cents'])} → 应付 ¥{be.format_yuan(q['payable_cents'])}")
        elif tier["status"] == "unsolvable":
            mc = tier.get("min_candidate")
            gap = tier.get("gap_cents")
            if mc:
                print(f"  {tier['label']} 无可行方案；最低候选 ¥{be.format_yuan(mc['quote']['payable_cents'])}（差额 ¥{be.format_yuan(gap)}）")
            else:
                print(f"  {tier['label']} 无可行方案（无可核价候选）")

    for d in result["deltas"]:
        print(f"  [{d['from']}→{d['to']}] " + " ".join(d["explanation"]))

    out_path = Path(os.environ.get("SMOKE_OUT", "real_smoke_result.json"))
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完整结果已写入 {out_path.resolve()}（注意：请勿把真实地址/订单信息提交到公开仓库）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
