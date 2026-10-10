#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""McBudget 确定性预算引擎。

同一份算法与数据约定同时服务两种模式，避免"演示与真实计算含义不同"：
- 演示模式：quote_fn 为空，使用 assets/sample_data.json 的样例优惠规则估算，所有方案状态为 demo_sample。
- 真实模式：调用方（WorkBuddy、Codex 等支持 MCP 的客户端）把 query-meals/calculate-price 的返回适配成本引擎的
  输入契约，并通过 quote_fn 提交真实报价（≤12 个去重购物车），方案状态为 priced / quote_failed / estimated。

硬约束（与 SKILL.md 一致）：
- 内部金额一律整数"分"；菜单与订单的"元字符串"、算价的"整数分"由适配器按官方文档显式转换。
- 每轮最多 30 个候选购物车；真实报价最多 12 个去重购物车；三档共享同一批候选与报价。
- 展示"本轮候选中的推荐"，不宣称全局最便宜。
- 同输入、同数据 → 同输出（含顺序）。
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from itertools import product as iter_product
from typing import Any, Callable, Optional

DEMO_STATUS = "demo_sample"
PRICED_STATUS = "priced"
ESTIMATED_STATUS = "estimated"
QUOTE_FAILED_STATUS = "quote_failed"
CARRY_OVER_STATUS = "carry_over"
UNSOLVABLE_STATUS = "unsolvable"

MAX_CANDIDATES = 30
MAX_QUOTE_CALLS = 12
TIER_STEP_CENTS = 500  # 默认 5 元


# ---------------------------------------------------------------------------
# 金额处理：内部一律整数分
# ---------------------------------------------------------------------------

def to_cents(value: Any, source: str) -> int:
    """把外部金额统一转换为整数分。

    source 指明来源字段，按官方文档规定显式声明单位，禁止按数值大小猜测：
    - "menu_yuan"   : query-meals / query-meal-detail 的 currentPrice/price/originalPrice（元字符串，如 "55.5"）
    - "quote_cents" : calculate-price 的 price/discount/deliveryPrice 等字段（整数分）
    - "order_yuan"  : create-order / query-order 的 totalAmount/realTotalAmount 等（元字符串）
    - "user_yuan"   : 用户输入的预算（元，数字或字符串）
    """
    if value is None:
        raise ValueError(f"{source}: 金额为空")
    if source in ("quote_cents",):
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValueError(f"{source}: 非法的整数分金额 {value!r}")
        iv = int(Decimal(str(value)))
        if Decimal(str(value)) != Decimal(iv):
            raise ValueError(f"{source}: 整数分金额含小数 {value!r}")
        return iv
    # 元字符串 / 用户元输入
    d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(d * 100)


def from_cents(cents: int) -> str:
    """整数分 → 展示用元字符串（与订单字段同形，如 2450 -> "24.5"）。"""
    d = Decimal(cents) / Decimal(100)
    s = format(d.quantize(Decimal("0.01")), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def format_yuan(cents: int) -> str:
    """整数分 → 展示文本（2450 -> "24.5"）。"""
    return from_cents(cents)


# ---------------------------------------------------------------------------
# 真实 MCP 返回适配器（依据 open.mcd.cn/mcp/doc 提取的官方字段）
# ---------------------------------------------------------------------------

def adapt_query_meals(data: dict) -> list[dict]:
    """query-meals 返回 → 统一菜单列表（元→分）。

    官方结构：data.meals = {code: {name, currentPrice, originalPrice, discountType, ...}}
    菜单价格为元字符串（文档示例 "55.5"）。
    """
    menu = []
    meals = (data or {}).get("meals") or {}
    if isinstance(meals, dict):
        for code, m in meals.items():
            menu.append(
                {
                    "code": str(code),
                    "name": m.get("name", ""),
                    "category": _guess_category(m.get("name", "")),
                    "price_cents": to_cents(m.get("currentPrice"), "menu_yuan"),
                    "tags": [],
                    "is_combo": False,
                }
            )
    elif isinstance(meals, list):
        for m in meals:
            menu.append(
                {
                    "code": str(m.get("code")),
                    "name": m.get("name", ""),
                    "category": _guess_category(m.get("name", "")),
                    "price_cents": to_cents(m.get("currentPrice"), "menu_yuan"),
                    "tags": [],
                    "is_combo": False,
                }
            )
    return menu


def _guess_category(name: str) -> str:
    if any(k in name for k in ("套餐", "件套")):
        return "combo"
    if any(k in name for k in ("可乐", "咖啡", "柠檬水", "奶茶", "果汁", "豆浆", "矿泉水", "雪碧", "麦炫酷", "美汁源")):
        return "drink"
    if any(k in name for k in ("薯条", "派", "麦乐鸡", "鸡翅", "沙拉", "玉米杯", "圆筒", "新地")):
        return "snack"
    if any(k in name for k in ("堡", "卷", "麦满分", "吉士蛋", "板烧")):
        return "main"
    return "other"


def adapt_quote(data: dict, cart: list[dict]) -> dict:
    """calculate-price 返回 → 统一报价（官方字段为整数分，源单位 quote_cents）。

    price=应付总额；productPrice=商品金额；discount=优惠；deliveryPrice=配送费；packingPrice=打包费。
    实测（2026-10，端州三路店）：到店场景 deliveryPrice/packingPrice 可能整字段缺省，按 0 处理；
    商品金额与优惠字段的对应关系以官方返回为准，本函数不做二次扣减。
    """
    product = to_cents(data.get("productPrice"), "quote_cents")
    delivery = to_cents(data.get("deliveryPrice", 0), "quote_cents")
    packing = to_cents(data.get("packingPrice", 0), "quote_cents")
    discount = to_cents(data.get("discount"), "quote_cents")
    payable = to_cents(data.get("price"), "quote_cents")
    expected = product - discount + delivery + packing
    if payable != expected:
        raise ValueError(
            f"quote_cents: 官方算价不自洽 price={payable} != productPrice({product}) - discount({discount}) "
            f"+ deliveryPrice({delivery}) + packingPrice({packing})"
        )
    return {
        "product_cents": product,
        "discount_cents": discount,
        "delivery_cents": delivery + packing,
        "payable_cents": payable,
    }


def adapt_order_amounts(order_detail: dict) -> dict:
    """create-order/query-order 的 orderDetail 金额 → 统一报价（元字符串，source=order_yuan）。"""
    return {
        "total_cents": to_cents(order_detail.get("totalAmount"), "order_yuan"),
        "real_total_cents": to_cents(order_detail.get("realTotalAmount"), "order_yuan"),
        "product_cents": to_cents(order_detail.get("productPrice"), "order_yuan"),
        "delivery_cents": to_cents(order_detail.get("deliveryPrice"), "order_yuan"),
    }


# ---------------------------------------------------------------------------
# 购物车与候选
# ---------------------------------------------------------------------------

def cart_signature(cart: list[dict]) -> str:
    """购物车稳定签名：排序后的 (code, qty) 列表，用于去重与平局排序。"""
    return ";".join(f"{i['code']}x{i['qty']}" for i in sorted(cart, key=lambda x: x["code"]))


def item_matches_exclusion(item: dict, excluded: list[str]) -> bool:
    hay = item["name"] + "".join(item.get("tags", []))
    return any(k and k in hay for k in excluded)


def expand_prefs(prefs: list[str]) -> list[list[str]]:
    """偏好关键词同族扩展：返回"变体组"列表，每组对应一个原始偏好。

    麦当劳常用"鸡腿堡/板烧鸡腿/麦乐鸡"命名，用户说"想吃鸡肉"若按字面匹配
    将漏掉全部鸡腿类主餐。规则：以"肉"结尾的词追加首字（鸡肉→[鸡肉, 鸡]），
    其余原样保留。命中组内任一变体 = 该原始偏好命中 1 次（同组变体不叠加计分）。
    """
    groups: list[list[str]] = []
    if prefs and isinstance(prefs[0], (list, tuple)):
        return [list(g) for g in prefs]  # 已是变体组（幂等）
    for k in prefs or []:
        if not k:
            continue
        variants = [k]
        if len(k) >= 2 and k.endswith("肉"):
            variants.append(k[0])
        groups.append(variants)
    return groups


def pref_hits(item: dict, prefs: list[list[str]]) -> int:
    """偏好命中数（仅主餐口径：main/combo，套餐把自带组成名称一并计入）。

    用户偏好表达的是主餐方向；小食/饮品的偶然命中不算偏好满足，
    只计入 coverage（性价比覆盖度）。prefs 为 expand_prefs 的变体组。
    """
    if item.get("category") not in ("main", "combo"):
        return 0
    hay = item["name"] + "".join(item.get("tags", []))
    for sub in item.get("combo_items", []) or []:
        hay += sub.get("name", "")
    return sum(1 for variants in prefs if any(v and v in hay for v in variants))


def has_combo_item(cart: list[dict]) -> bool:
    return any(i.get("category") == "combo" or (i.get("combo_items") or []) for i in cart)


def violates_must(cart: list[dict], must: list[str]) -> bool:
    """必选餐品：购物车中必须出现匹配 must 关键词的商品（含套餐组成）。"""
    if not must:
        return False
    hay = ""
    for it in cart:
        hay += it["name"] + "".join(it.get("tags", []))
        for sub in it.get("combo_items", []) or []:
            hay += sub.get("name", "")
    return not any(k and k in hay for k in must)


def generate_candidates(
    menu: list[dict],
    prefs: list[str],
    excluded: list[str],
    must: list[str],
    max_candidates: int = MAX_CANDIDATES,
) -> list[list[dict]]:
    """确定性生成候选购物车（≤ max_candidates，签名去重）。

    组合规则（一人份优先，不为花光预算堆叠）：
    - 恰好 1 份主餐（汉堡/套餐）；套餐即完整购物车（V1 用完整默认组成，不猜子项）。
    - 非套餐可搭配 0~1 小食、0~1 饮品；单品不重复。
    - 排除项命中任何成员即弃置；必选关键词无法满足的购物车弃置。
    """
    mains = [m for m in menu if m.get("category") == "main" and not item_matches_exclusion(m, excluded)]
    combos = [m for m in menu if m.get("category") == "combo" and not item_matches_exclusion(m, excluded)]
    snacks = [m for m in menu if m.get("category") == "snack" and not item_matches_exclusion(m, excluded)]
    drinks = [m for m in menu if m.get("category") == "drink" and not item_matches_exclusion(m, excluded)]
    prefs = expand_prefs(prefs)

    raw: list[list[dict]] = []

    def cart_item(m: dict, qty: int = 1) -> dict:
        return {"code": m["code"], "name": m["name"], "qty": qty, "price_cents": m["price_cents"], "category": m.get("category", "other"), "tags": list(m.get("tags", [])), "combo_items": m.get("combo_items", [])}

    # 套餐购物车
    for c in combos:
        raw.append([cart_item(c)])
    # 汉堡 × 0/1 小食 × 0/1 饮品
    for b, s, d in iter_product(mains, [None] + snacks, [None] + drinks):
        cart = [cart_item(b)]
        if s is not None:
            cart.append(cart_item(s))
        if d is not None:
            cart.append(cart_item(d))
        raw.append(cart)

    # 必选过滤
    raw = [c for c in raw if not violates_must(c, must)]

    # 去重（签名）
    seen: dict[str, list[dict]] = {}
    for c in raw:
        sig = cart_signature(c)
        if sig not in seen:
            seen[sig] = c

    # 排序后截断：偏好命中多者优先；同分下套餐优先（性价比）、件数少者贴近一人份；再按签名稳定排序（确定性）
    ranked = sorted(
        seen.values(),
        key=lambda c: (
            -sum(pref_hits(i, prefs) for i in c),
            0 if has_combo_item(c) else 1,
            len(c),
            cart_signature(c),
        ),
    )
    return ranked[:max_candidates]


# ---------------------------------------------------------------------------
# 定价
# ---------------------------------------------------------------------------

def demo_price_cart(cart: list[dict], sample: dict) -> dict:
    """演示模式定价：按样例优惠规则取最优单券。返回与 adapt_quote 相同结构。"""
    product = sum(i["price_cents"] * i["qty"] for i in cart)
    delivery_rule = sample.get("delivery", {})
    fee = delivery_rule.get("fee_cents", 0)
    threshold = delivery_rule.get("free_threshold_cents", 0)
    delivery = 0 if threshold and product >= threshold else fee

    best = None
    for cpn in sample.get("coupons", []):
        d = _demo_coupon_discount(cart, product, cpn)
        if d > 0 and (best is None or d > best[1]):
            best = (cpn, d)
    discount = best[1] if best else 0
    return {
        "product_cents": product,
        "discount_cents": discount,
        "delivery_cents": delivery,
        "payable_cents": product - discount + delivery,
        "coupon": best[0]["title"] if best else None,
    }


def _demo_coupon_discount(cart: list[dict], product_total: int, cpn: dict) -> int:
    t = cpn.get("type")
    if t == "item_discount":
        kw = cpn.get("target_keyword", "")
        hit = [i for i in cart if kw and kw in i["name"] and i.get("category") == cpn.get("target_category", i.get("category"))]
        if not hit:
            return 0
        # 样例规则：无论命中几件只减一次（不重复扣减）
        return cpn["discount_cents"]
    if t == "order_discount":
        return cpn["discount_cents"] if product_total >= cpn.get("threshold_cents", 0) else 0
    if t == "category_discount":
        sub = sum(i["price_cents"] * i["qty"] for i in cart if i.get("category") == cpn.get("category"))
        return cpn["discount_cents"] if sub >= cpn.get("threshold_cents", 0) else 0
    return 0


def demo_price_fn_factory(sample: dict) -> Callable[[list[dict]], Optional[dict]]:
    def quote_fn(cart: list[dict]) -> Optional[dict]:
        return demo_price_cart(cart, sample)
    return quote_fn


# ---------------------------------------------------------------------------
# 排序与代表方案
# ---------------------------------------------------------------------------

def coverage_score(cart: list[dict], prefs: list[list[str]], must: list[str]) -> int:
    """性价比覆盖度（同等偏好下优先覆盖更多内容的套餐/组合）：

    - 主餐（main/combo）计 1；
    - 套餐按自带组成计件（组成通常=主+小食+饮），套餐天然优于单买；
    - 单点小食/饮品各计 1；
    - 用户 must 关键词、prefs 变体组命中的购物车再各加 1。
    排序键保持 偏好命中 ↓ → 套餐组优先 ↓ → 覆盖度 ↓ → 实付 ↑ → 签名 ↑：
    预算内优先推荐套餐，而非最便宜的单买。
    """
    slots = 0
    for it in cart:
        cat = it.get("category")
        if cat in ("main", "combo"):
            slots += 1
            slots += len(it.get("combo_items", []) or [])
        else:
            slots += 1
    text = ""
    for it in cart:
        text += it["name"] + "".join(it.get("tags", []))
        for sub in it.get("combo_items", []) or []:
            text += sub.get("name", "")
    for k in must:
        if k and k in text:
            slots += 1
    for variants in prefs:
        if any(v and v in text for v in variants):
            slots += 1
    return slots


def rank_key(cart: list[dict], quote: dict, prefs: list[str], must: list[str]):
    """代表方案排序键：偏好满足（主餐口径）↓ → 套餐优先（性价比）↓ → 覆盖度 ↓ → 实付 ↑ → 签名 ↑。"""
    pref_total = sum(pref_hits(i, prefs) for i in cart)
    combo_first = 0 if has_combo_item(cart) else 1
    return (-pref_total, combo_first, -coverage_score(cart, prefs, must), quote["payable_cents"], cart_signature(cart))


# ---------------------------------------------------------------------------
# 增减预算解释
# ---------------------------------------------------------------------------

def _item_map(cart: list[dict]) -> dict:
    return {i["code"]: i for i in cart}


def explain_delta(low_plan: dict, high_plan: dict) -> list[str]:
    """比较相邻档位方案：解释增加/减少/替换了什么，及应付金额变化的归因。"""
    out: list[str] = []
    a, b = _item_map(low_plan["cart"]), _item_map(high_plan["cart"])
    qa, qb = low_plan["quote"], high_plan["quote"]

    added = [b[c] for c in b if c not in a]
    removed = [a[c] for c in a if c not in b]
    same = [c for c in a if c in b]
    qty_changed = [a[c] for c in same if a[c]["qty"] != b[c]["qty"]]
    replaced = []
    if low_plan.get("main_code") and high_plan.get("main_code") and low_plan["main_code"] != high_plan["main_code"] and not added and not removed:
        replaced = [(a.get(low_plan["main_code"]), b.get(high_plan["main_code"]))]

    parts = []
    if added:
        parts.append("增加 " + "、".join(f"{i['name']}" for i in added))
    if removed:
        parts.append("去掉 " + "、".join(f"{i['name']}" for i in removed))
    for old, new in replaced:
        parts.append(f"把「{old['name']}」换成「{new['name']}」")
    for it in qty_changed:
        delta_qty = b[it["code"]]["qty"] - a[it["code"]]["qty"]
        word = "多" if delta_qty > 0 else "少"
        parts.append(f"{it['name']} {word}{abs(delta_qty)} 份")
    if not parts:
        out.append("两档方案相同：更高的预算暂时没有符合偏好的升级，沿用同一方案。")
    else:
        out.append("；".join(parts) + "。")

    d_product = qb["product_cents"] - qa["product_cents"]
    d_disc = qb["discount_cents"] - qa["discount_cents"]
    d_deliv = qb["delivery_cents"] - qa["delivery_cents"]
    d_pay = qb["payable_cents"] - qa["payable_cents"]
    why = []
    if d_product:
        why.append(f"商品金额{'增加' if d_product > 0 else '减少'} {format_yuan(abs(d_product))} 元")
    if d_disc:
        why.append(f"优惠{'多' if d_disc > 0 else '少'}减 {format_yuan(abs(d_disc))} 元")
    if d_deliv:
        why.append(f"配送费{'增加' if d_deliv > 0 else '减少'} {format_yuan(abs(d_deliv))} 元")
    if d_pay == 0:
        out.append("实付金额不变（" + "，".join(why) + "）。" if why else "实付金额不变。")
    else:
        basis = "，".join(why) if why else "组成未变"
        out.append(f"实付由 {format_yuan(qa['payable_cents'])} 元变为 {format_yuan(qb['payable_cents'])} 元（{'多花' if d_pay > 0 else '少花'} {format_yuan(abs(d_pay))} 元；来源：{basis}）。")
    out.append("以上差额来自实际餐品与官方/样例报价，不是预算档位差额。")
    return out


# ---------------------------------------------------------------------------
# 预算阶梯
# ---------------------------------------------------------------------------

def _tier_budgets(budget_cents: int, step: int = TIER_STEP_CENTS) -> list[int]:
    return [b for b in (budget_cents - step, budget_cents, budget_cents + step) if b > 0]


def build_ladder(
    ctx: dict,
    quote_fn: Optional[Callable[[list[dict]], Optional[dict]]] = None,
) -> dict:
    """构建预算阶梯。

    ctx 契约（演示与真实共享）：
      budget_cents: int            应付总额上限（含配送费）
      order_type: "pickup"|"delivery"
      menu: [item]                 统一菜单（price_cents）
      sample: dict|None            演示样例数据（demo 模式必填）
      prefs: [str]; excluded: [str]; must: [str]
    真实模式：quote_fn 提交官方算价；返回 None 视为核价失败。
    """
    budget = int(ctx["budget_cents"])
    order_type = ctx.get("order_type", "pickup")
    if order_type not in ("pickup", "dt", "delivery"):
        raise ValueError(f"order_type 必须是 pickup/dt/delivery，收到 {order_type!r}（就餐方式必须在选餐前确认，决定菜单上下文）")
    prefs = expand_prefs(list(ctx.get("prefs", [])))
    excluded = list(ctx.get("excluded", []))
    must = list(ctx.get("must", []))
    menu = ctx["menu"]
    is_demo = quote_fn is None

    if excluded and order_type == "delivery":
        pass  # 外送同样适用排除项

    candidates = generate_candidates(menu, prefs, excluded, must)

    # 候选定价（演示：规则定价；真实：估算→提交≤12个去重购物车官方报价）
    quotes: dict[str, dict] = {}
    statuses: dict[str, str] = {}
    quote_calls = 0

    def demo_quote(cart):
        q = demo_price_cart(cart, ctx["sample"])
        q["delivery_cents"] = 0 if order_type in ("pickup", "dt") else q["delivery_cents"]
        q["payable_cents"] = q["product_cents"] - q["discount_cents"] + q["delivery_cents"]
        return q

    if is_demo:
        for cart in candidates:
            sig = cart_signature(cart)
            quotes[sig] = demo_quote(cart)
            statuses[sig] = DEMO_STATUS
    else:
        for cart in candidates:
            sig = cart_signature(cart)
            est = _estimate_for_real(cart, order_type, ctx)
            quotes[sig] = est
            statuses[sig] = ESTIMATED_STATUS
        ordered = sorted(
            candidates,
            key=lambda c: (
                -sum(pref_hits(i, prefs) for i in c),
                0 if has_combo_item(c) else 1,
                quotes[cart_signature(c)]["payable_cents"],
                cart_signature(c),
            ),
        )
        for cart in ordered[:MAX_QUOTE_CALLS]:
            sig = cart_signature(cart)
            quote_calls += 1
            try:
                res = quote_fn(cart) if quote_fn else None
            except Exception:
                res = None
            if res is None:
                statuses[sig] = QUOTE_FAILED_STATUS
            else:
                quotes[sig] = {**res}
                statuses[sig] = PRICED_STATUS

    def tier_label(c: int, b: int) -> str:
        if c == b:
            return "B"
        return f"B{'-' if c < b else '+'}{abs(b - c) // 100:g}"

    tiers = []
    prev_plan = None
    prev_label = None
    # 菜单估算仅用于安排核价；真实模式的预算判断必须来自成功的官方报价。
    usable_status = DEMO_STATUS if is_demo else PRICED_STATUS
    usable_candidates = [c for c in candidates if statuses[cart_signature(c)] == usable_status]
    for tb in _tier_budgets(budget):
        feasible = [c for c in usable_candidates if quotes[cart_signature(c)]["payable_cents"] <= tb]
        entry: dict[str, Any] = {"budget_cents": tb, "label": tier_label(tb, budget)}
        if feasible:
            rep = min(feasible, key=lambda c: rank_key(c, quotes[cart_signature(c)], prefs, must))
            sig = cart_signature(rep)
            plan = {
                "cart": rep,
                "quote": quotes[sig],
                "status": statuses[sig],
                "main_code": next((i["code"] for i in rep if i.get("category") == "main" or i.get("category") == "combo"), None),
                "signature": sig,
            }
            if prev_plan is not None and prev_plan["signature"] == sig:
                plan["carry_over_from"] = prev_label
            entry.update({"status": plan["status"], "plan": plan})
            prev_plan = plan
            prev_label = entry["label"]
        else:
            if usable_candidates:
                lowest = min(usable_candidates, key=lambda c: (quotes[cart_signature(c)]["payable_cents"], cart_signature(c)))
                lq = quotes[cart_signature(lowest)]
                entry.update(
                    {
                        "status": UNSOLVABLE_STATUS,
                        "min_candidate": {"cart": lowest, "quote": lq, "status": statuses[cart_signature(lowest)]},
                        "gap_cents": lq["payable_cents"] - tb,
                    }
                )
            else:
                entry.update({"status": UNSOLVABLE_STATUS if is_demo else QUOTE_FAILED_STATUS, "min_candidate": None, "gap_cents": None})
                if not is_demo:
                    entry["note"] = "本轮未获得可用官方报价，不能判断预算内方案"
        tiers.append(entry)

    deltas = []
    priced_plans = [t for t in tiers if t.get("plan")]
    for i in range(1, len(priced_plans)):
        deltas.append(
            {
                "from": priced_plans[i - 1]["label"],
                "to": priced_plans[i]["label"],
                "explanation": explain_delta(priced_plans[i - 1]["plan"], priced_plans[i]["plan"]),
            }
        )

    return {
        "mode": "demo" if is_demo else "real",
        "order_type": order_type,
        "budget_cents": budget,
        "tiers": tiers,
        "deltas": deltas,
        "meta": {
            "candidate_count": len(candidates),
            "quote_calls": quote_calls,
            "max_candidates": MAX_CANDIDATES,
            "max_quote_calls": MAX_QUOTE_CALLS,
            "deterministic": True,
            "claim": "本轮候选中的推荐，不构成全局最便宜或穷尽全部组合的承诺",
        },
    }


def _estimate_for_real(cart: list[dict], order_type: str, ctx: dict) -> dict:
    """真实模式的估算价：菜单价合计（不含优惠）。仅用于排序与安排核价顺序。

    配送费：delivery 按预设下限（真实值以算价为准）；pickup/dt（到店/得来速）为 0。
    """
    product = sum(i["price_cents"] * i["qty"] for i in cart)
    delivery = ctx.get("delivery_fee_cents", 0) if order_type == "delivery" else 0
    return {
        "product_cents": product,
        "discount_cents": 0,
        "delivery_cents": delivery,
        "payable_cents": product + delivery,
        "estimated": True,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _read_ctx(args) -> dict:
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            return json.load(f)
    ctx = {
        "budget_cents": to_cents(str(args.budget), "user_yuan"),
        "order_type": args.order_type,
        "menu": [],
        "sample": None,
        "prefs": args.pref or [],
        "excluded": args.exclude or [],
        "must": args.must or [],
    }
    if args.sample_data:
        with open(args.sample_data, encoding="utf-8") as f:
            sample = json.load(f)
        ctx["sample"] = sample
        ctx["menu"] = sample["menu"]
    return ctx


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="McBudget 确定性预算引擎")
    ap.add_argument("--input", help="上下文 JSON 文件（含 budget_cents/order_type/menu 等）")
    ap.add_argument("--budget", type=str, default="25", help="预算（元）")
    ap.add_argument("--order-type", choices=["pickup", "dt", "delivery"], default="pickup",
                    help="就餐方式：pickup 到店取餐 / dt 得来速 / delivery 麦乐送（方式决定菜单上下文，必须先于选餐确认）")
    ap.add_argument("--sample-data", default=None, help="演示样例数据 JSON（assets/sample_data.json）")
    ap.add_argument("--pref", action="append", help="口味偏好关键词，可多次")
    ap.add_argument("--exclude", action="append", help="不想吃的关键词，可多次")
    ap.add_argument("--must", action="append", help="必选餐品关键词，可多次")
    ap.add_argument("--indent", type=int, default=2)
    args = ap.parse_args(argv)

    ctx = _read_ctx(args)
    result = build_ladder(ctx)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=args.indent)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
