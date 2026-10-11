#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub 离线性能回归：只用合成菜单与核价回调，不请求 MCP、不读取账户。

验证核价调用量、三档覆盖、扩展前缀及已核价方案重算。计时只代表本机
Python 计算，不代表官方接口或 WorkBuddy 的真实端到端耗时。
"""

from __future__ import annotations

import json
from statistics import median
from time import perf_counter

import budget_engine as be


CHECKS = 0


def check(label, condition):
    global CHECKS
    if not condition:
        raise AssertionError(label)
    CHECKS += 1


def rejects(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def item(code, category, price, name=None, slots=0):
    return {"code": code, "name": name or code, "category": category,
            "price_cents": price, "combo_items": [{"name": f"组成{i}"} for i in range(slots)]}


def context(menu, budget=2500, **extra):
    return {"menu": menu, "budget_cents": budget, "order_type": "pickup", **extra}


def official_shaped_quote(cart):
    """合成回调，仅供离线断言；不是实际官方接口响应。"""
    total = sum(i["price_cents"] * i["qty"] for i in cart)
    return {"product_cents": total, "discount_cents": 0,
            "delivery_cents": 0, "payable_cents": total,
            "quoted_at": "2026-10-11T12:00:00+08:00"}


def main():
    menu = [item("C22", "combo", 2200, slots=3),
            item("C28", "combo", 2800, slots=4),
            item("M10", "main", 1000), item("M20", "main", 2000),
            item("S05", "snack", 500), item("D03", "drink", 300)]
    ctx = context(menu)
    quick = be.plan_quotes(ctx)
    full = be.plan_quotes({**ctx, "quote_limit": 12})
    signatures = lambda carts: [be.cart_signature(c) for c in carts]
    check("默认规划六项", quick["quote_limit"] == 6 and len(quick["carts"]) == 6)
    check("纯规划没有报价或推荐", "tiers" not in quick and "quote" not in quick)
    check("候选硬上限30", quick["candidate_count"] <= 30)
    check("六项不重复", len(set(signatures(quick["carts"]))) == 6)
    for limit in range(1, 13):
        planned = be.plan_quotes({**ctx, "quote_limit": limit})
        check(f"扩展到{limit}保持前缀", signatures(planned["carts"]) == signatures(full["carts"])[:limit])

    calls = []
    saved = {}

    def quote(cart):
        sig = be.cart_signature(cart)
        calls.append(sig)
        saved[sig] = official_shaped_quote(cart)
        return saved[sig]

    result = be.build_ladder(ctx, quote)
    check("实际回调与规划顺序一致", calls == signatures(quick["carts"]))
    check("默认只调用六次", result["meta"]["quote_calls"] == len(calls) == 6)
    check("保留B±5三档", [t["label"] for t in result["tiers"]] == ["B-5", "B", "B+5"])
    check("三档覆盖不同代表价", [t["plan"]["quote"]["payable_cents"] for t in result["tiers"]] == [1800, 2200, 2800])
    check("三档均来自真实格式报价", all(t["status"] == "priced" for t in result["tiers"]))
    reused = be.select_priced_ladder(ctx, saved)
    check("本地重算方案与直接回调相同", reused["tiers"] == result["tiers"] and reused["deltas"] == result["deltas"])
    check("本地重算零回调", reused["meta"]["quote_calls"] == 0 and len(calls) == 6)
    check("记录有效报价复用量", reused["meta"]["cached_quote_count"] == 6)
    changed = be.select_priced_ladder({**ctx, "budget_cents": 2100}, saved)
    check("修改预算仍只用已核价方案", all(not t.get("plan") or t["plan"]["quote"]["payable_cents"] <= t["budget_cents"] for t in changed["tiers"]))
    check("修改预算不触发核价", changed["meta"]["quote_calls"] == 0 and len(calls) == 6)
    check("保留官方实际核价时间", all(t["plan"]["quote"]["quoted_at"] == "2026-10-11T12:00:00+08:00" for t in result["tiers"]))
    ignored = be.select_priced_ladder(ctx, {"other-context": official_shaped_quote([])})
    check("未知候选报价不进入推荐", ignored["meta"]["cached_quote_count"] == 0 and all(not t.get("plan") for t in ignored["tiers"]))
    for source in ("demo_sample", "estimated", "quote_failed"):
        invalid = {sig: {**q, "source": source} for sig, q in saved.items()}
        blocked = be.select_priced_ladder(ctx, invalid)
        check(f"复用入口拒绝{source}", blocked["meta"]["cached_quote_count"] == 0 and all(not t.get("plan") for t in blocked["tiers"]))
    invalid = {sig: {**q, "payable_cents": q["payable_cents"] + 1} for sig, q in saved.items()}
    check("复用入口拒绝不自洽金额", be.select_priced_ladder(ctx, invalid)["meta"]["cached_quote_count"] == 0)
    for limit in (True, 0, 13, 6.0, "6", None):
        check(f"拒绝非法核价上限{limit!r}", rejects(lambda: be.plan_quotes({**ctx, "quote_limit": limit})))
    check("规划拒绝演示上下文", rejects(lambda: be.plan_quotes({**ctx, "mode": "demo"})))
    check("重算拒绝演示样例", rejects(lambda: be.select_priced_ladder({**ctx, "sample": {}}, saved)))
    check("拒绝无官方报价回调", rejects(lambda: be.build_ladder(ctx)))
    check("重算拒绝非映射输入", rejects(lambda: be.select_priced_ladder(ctx, None)))
    cash_ctx = {**ctx, "selection": "lowest_cash"}
    cash_result = be.build_ladder(cash_ctx, official_shaped_quote)
    check("省现金选择较便宜主餐而非套餐", all(t["plan"]["quote"]["payable_cents"] == 1000 and t["plan"]["main_code"] == "M10" for t in cash_result["tiers"]))
    check("默认仍优先套餐覆盖", be.build_ladder({**ctx, "selection": "balanced"}, official_shaped_quote)["tiers"] == result["tiers"])
    cash_planned = be.plan_quotes(cash_ctx)
    check("省现金规划与元数据同步", cash_planned["carts"][0][0]["code"] == "M10" and cash_planned["selection"] == cash_result["meta"]["selection"] == "lowest_cash")
    check("复用官方报价遵循省现金选项", be.select_priced_ladder(cash_ctx, saved)["tiers"] == cash_result["tiers"])
    pref_menu = [item("C26", "combo", 2600, name="鸡肉套餐", slots=3),
                 item("M09", "main", 900, name="麦香鱼"),
                 item("M14", "main", 1400, name="鸡肉汉堡")]
    pref_result = be.build_ladder(context(pref_menu, budget=3000, must=["鸡肉"], selection="lowest_cash"), official_shaped_quote)
    check("省现金仍满足硬性必选餐品", all(t["plan"]["main_code"] == "M14" for t in pref_result["tiers"]))
    soft_pref_menu = [item("SPICY22", "main", 2200, name="辣鸡腿汉堡"),
                      item("GRILL16", "main", 1600, name="板烧鸡腿汉堡")]
    soft_pref_result = be.build_ladder(context(soft_pref_menu, budget=3000, prefs=["鸡肉", "辣"],
                                               must=["鸡腿汉堡"], selection="lowest_cash"), official_shaped_quote)
    check("旧的软口味偏好不覆盖更低实付", all(t["plan"]["main_code"] == "GRILL16" and t["plan"]["quote"]["payable_cents"] == 1600 for t in soft_pref_result["tiers"]))
    free_sig = be.cart_signature([{"code": "M10", "qty": 1}])
    free_quotes = {**saved, free_sig: {"product_cents": 1000, "discount_cents": 1000,
                                     "delivery_cents": 0, "payable_cents": 0}}
    free_result = be.select_priced_ladder(cash_ctx, free_quotes)
    check("有效零实付官方格式报价可入选", all(t["plan"]["quote"]["payable_cents"] == 0 for t in free_result["tiers"]))
    for selection in ("unknown", None, 1):
        check(f"规划拒绝非法选择策略{selection!r}", rejects(lambda: be.plan_quotes({**ctx, "selection": selection})))
    check("核价入口拒绝未知选择策略", rejects(lambda: be.build_ladder({**ctx, "selection": "unknown"}, official_shaped_quote)))
    check("复用入口拒绝未知选择策略", rejects(lambda: be.select_priced_ladder({**ctx, "selection": "unknown"}, saved)))

    expensive = [item(f"C{i:02}", "combo", 4000, name="鸡肉套餐", slots=3) for i in range(7)]
    fallback = be.plan_quotes(context(expensive + [item("M15", "main", 1500, name="鸡肉汉堡")], prefs=["鸡肉"]))
    check("多项高价套餐仍保留低价回退", any(c[0]["code"] == "M15" for c in fallback["carts"]))
    empty = be.plan_quotes(context([]))
    check("空菜单无需核价", empty["carts"] == [] and empty["planned_quote_count"] == 0)
    empty_result = be.select_priced_ladder(context([]), saved)
    check("空菜单不编造推荐", empty_result["meta"]["cached_quote_count"] == 0 and all(not t.get("plan") for t in empty_result["tiers"]))
    complete_calls = []
    thorough = be.build_ladder({**ctx, "quote_limit": 12}, lambda cart: (complete_calls.append(be.cart_signature(cart)) or official_shaped_quote(cart)))
    check("深查最多十二次", thorough["meta"]["quote_calls"] == len(full["carts"]) <= 12)
    check("深查前六项可直接复用", complete_calls[:6] == calls)
    abort_calls = []

    def abort_after_two(cart):
        abort_calls.append(be.cart_signature(cart))
        if len(abort_calls) > 2:
            raise be.QuoteBatchAborted("私有故障细节不应进入输出")
        return official_shaped_quote(cart)

    partial = be.build_ladder(ctx, abort_after_two)
    check("整批故障立即停止剩余核价", partial["meta"]["quote_calls"] == 3 and len(abort_calls) == 3 and partial["meta"]["quote_aborted"])
    check("保留故障前已成功核价的方案", all(t.get("plan") and t["plan"]["signature"] in abort_calls[:2] for t in partial["tiers"]))
    check("输出不泄露原始异常细节", "私有故障" not in json.dumps(partial, ensure_ascii=False))

    # 106 项合成菜单。所有计时均为本地 CPU，没有模拟网络延迟或外部调用。
    large_menu = ([item(f"C{i:02}", "combo", 2200 + i * 120, slots=3) for i in range(10)]
                  + [item(f"M{i:02}", "main", 1000 + i * 90) for i in range(32)]
                  + [item(f"S{i:02}", "snack", 400 + i * 30) for i in range(32)]
                  + [item(f"D{i:02}", "drink", 300 + i * 30) for i in range(32)])
    large_ctx = context(large_menu)
    check("106项菜单可扩展到十二项且保持前缀",
          len(be.plan_quotes({**large_ctx, "quote_limit": 12})["carts"]) == 12
          and be.plan_quotes({**large_ctx, "quote_limit": 12})["carts"][:6] == be.plan_quotes(large_ctx)["carts"])
    timings = []
    for _ in range(3):
        start = perf_counter()
        large_result = be.build_ladder(large_ctx, official_shaped_quote)
        timings.append((perf_counter() - start) * 1000)
    check("106项菜单仍限定30候选6核价", large_result["meta"]["candidate_count"] == 30 and large_result["meta"]["quote_calls"] == 6)
    large_saved = {be.cart_signature(c): official_shaped_quote(c) for c in be.plan_quotes(large_ctx)["carts"]}
    start = perf_counter()
    large_reused = be.select_priced_ladder({**large_ctx, "budget_cents": 2700}, large_saved)
    local_reuse_ms = (perf_counter() - start) * 1000
    check("106项菜单改预算无需新增核价", large_reused["meta"]["quote_calls"] == 0 and large_reused["meta"]["cached_quote_count"] == 6)
    print(json.dumps({"checks_passed": CHECKS, "benchmark_scope": "offline Python CPU only",
                      "menu_items": len(large_menu), "candidate_count": large_result["meta"]["candidate_count"],
                      "default_quote_calls": 6, "thorough_quote_limit": 12,
                      "budget_only_new_quote_calls": 0,
                      "local_build_median_ms": round(median(timings), 2),
                      "local_budget_reuse_ms": round(local_reuse_ms, 2)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
