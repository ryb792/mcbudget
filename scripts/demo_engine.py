#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub 独立演示与离线回归适配器，不属于安装的 McBudget Skill。

仅使用虚构样例价格；复用真实核心的候选生成、排序与三档选择。
每个演示报价显式标记为 demo_sample，真实 build_ladder 拒绝该来源。
"""

from __future__ import annotations

import budget_engine as be

DEMO_STATUS = "demo_sample"


def demo_price_cart(cart: list[dict], sample: dict) -> dict:
    """虚构演示规则：取最优单券，不请求 MCP，也不能用于真实订单。"""
    product = sum(i["price_cents"] * i["qty"] for i in cart)
    delivery_rule = sample.get("delivery", {})
    fee = delivery_rule.get("fee_cents", 0)
    threshold = delivery_rule.get("free_threshold_cents", 0)
    delivery = 0 if threshold and product >= threshold else fee
    best = None
    for cpn in sample.get("coupons", []):
        discount = _coupon_discount(cart, product, cpn)
        if discount > 0 and (best is None or discount > best[1]):
            best = (cpn, discount)
    discount = best[1] if best else 0
    return {
        "product_cents": product, "discount_cents": discount,
        "delivery_cents": delivery, "payable_cents": product - discount + delivery,
        "coupon": best[0]["title"] if best else None, "source": DEMO_STATUS,
    }


def _coupon_discount(cart: list[dict], product_total: int, coupon: dict) -> int:
    kind = coupon.get("type")
    if kind == "item_discount":
        keyword = coupon.get("target_keyword", "")
        matched = any(keyword and keyword in i["name"] and i.get("category") == coupon.get("target_category", i.get("category")) for i in cart)
        return coupon["discount_cents"] if matched else 0
    if kind == "order_discount":
        return coupon["discount_cents"] if product_total >= coupon.get("threshold_cents", 0) else 0
    if kind == "category_discount":
        subtotal = sum(i["price_cents"] * i["qty"] for i in cart if i.get("category") == coupon.get("category"))
        return coupon["discount_cents"] if subtotal >= coupon.get("threshold_cents", 0) else 0
    return 0


def build_ladder(ctx: dict) -> dict:
    """仅为 GitHub 演示生成带 demo 标记的结果，永不调用真实入口。"""
    sample = ctx.get("sample")
    if not isinstance(sample, dict):
        raise ValueError("GitHub 演示需要显式传入虚构 sample 数据")
    order_type = ctx.get("order_type", "pickup")
    if order_type not in ("pickup", "dt", "delivery"):
        raise ValueError("order_type 必须是 pickup/dt/delivery")
    budget = int(ctx["budget_cents"])
    prefs = be.expand_prefs(list(ctx.get("prefs", [])))
    must = list(ctx.get("must", []))
    candidates = be.generate_candidates(ctx["menu"], prefs, list(ctx.get("excluded", [])), must)
    quotes, statuses = {}, {}
    for cart in candidates:
        sig = be.cart_signature(cart)
        quote = demo_price_cart(cart, sample)
        quote.pop("source")  # 对外结果由 mode 与方案 status 统一标记，与网页协议一致。
        if order_type in ("pickup", "dt"):
            quote["delivery_cents"] = 0
        quote["payable_cents"] = quote["product_cents"] - quote["discount_cents"] + quote["delivery_cents"]
        quotes[sig], statuses[sig] = quote, be.PRICED_STATUS
    tiers, deltas = be._select_tiers(budget, candidates, quotes, statuses, prefs, must)
    for tier in tiers:
        for key in ("plan", "min_candidate"):
            if tier.get(key):
                tier[key]["status"] = DEMO_STATUS
        if tier["status"] == be.PRICED_STATUS:
            tier["status"] = DEMO_STATUS
        elif tier["status"] == be.QUOTE_FAILED_STATUS:
            tier["status"] = be.UNSOLVABLE_STATUS
            tier.pop("note", None)
    for delta in deltas:
        delta["explanation"] = [text.replace("官方报价", "官方/样例报价") for text in delta["explanation"]]
    return {
        "mode": "demo", "order_type": order_type, "budget_cents": budget,
        "tiers": tiers, "deltas": deltas,
        "meta": {
            "candidate_count": len(candidates), "quote_calls": 0,
            "max_candidates": be.MAX_CANDIDATES, "max_quote_calls": be.MAX_QUOTE_CALLS,
            "deterministic": True,
            "claim": "本轮候选中的推荐，不构成全局最便宜或穷尽全部组合的承诺",
        },
    }
