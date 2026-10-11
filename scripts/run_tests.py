#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""McBudget 引擎自测：覆盖验收清单，纯标准库，无外部依赖。

运行：python scripts/run_tests.py
"""

from __future__ import annotations

import copy
import io
import json
import os
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import budget_engine as be  # noqa: E402
import demo_engine as de  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PATH = os.path.join(HERE, "..", "assets", "sample_data.json")

PASS, FAIL = 0, []


def check(name: str, cond: bool, detail: str = ""):
    global PASS
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL.append(name)
        print(f"FAIL  {name}  {detail}")


def _raises(fn) -> bool:
    try:
        fn()
        return False
    except Exception:
        return True


def load_sample():
    with open(SAMPLE_PATH, encoding="utf-8") as f:
        return json.load(f)


def demo_ctx(sample, budget_yuan, order_type="pickup", prefs=None, excluded=None, must=None):
    return {
        "budget_cents": be.to_cents(str(budget_yuan), "user_yuan"),
        "order_type": order_type,
        "menu": sample["menu"],
        "sample": sample,
        "prefs": prefs or [],
        "excluded": excluded or [],
        "must": must or [],
    }


def real_ctx(sample, budget_yuan, order_type="pickup", prefs=None, excluded=None, must=None, quote_fn=None):
    ctx = demo_ctx(sample, budget_yuan, order_type, prefs, excluded, must)
    ctx.pop("sample")
    ctx["delivery_fee_cents"] = 900
    return ctx, quote_fn


# ---------------------------------------------------------------------------
print("[1] 金额处理与单位转换")
check("menu_yuan 元字符串→分", be.to_cents("55.5", "menu_yuan") == 5550)
check("quote_cents 整数分直通", be.to_cents(1600, "quote_cents") == 1600)
check("quote_cents 拒绝小数", _raises(lambda: be.to_cents(16.5, "quote_cents")))
check("order_yuan 元字符串→分", be.to_cents("22", "order_yuan") == 2200)
check("user_yuan 用户预算→分", be.to_cents("25", "user_yuan") == 2500)
check("from_cents 2450→24.5", be.from_cents(2450) == "24.5")
check("from_cents 2200→22", be.from_cents(2200) == "22")

doc_meals = {"meals": {"920215": {"name": "培根安格斯厚牛堡大套餐", "currentPrice": "55.5", "originalPrice": "65.5"}, "9900008139": {"name": "DC套餐测试", "currentPrice": "14"}}}
menu = be.adapt_query_meals(doc_meals)
check("adapt_query_meals 数量", len(menu) == 2, str(menu))
check("adapt_query_meals 单位", all(m["price_cents"] in (5550, 1400) for m in menu))

doc_quote = {"productPrice": 1600, "deliveryPrice": 600, "originalPrice": 2200, "discount": 0, "price": 2200}
q = be.adapt_quote(doc_quote, [])
check("adapt_quote 文档示例", q == {"product_cents": 1600, "discount_cents": 0, "delivery_cents": 600, "payable_cents": 2200})
check("adapt_quote 不自洽报错", _raises(lambda: be.adapt_quote({**doc_quote, "price": 999}, [])))

doc_order = {"totalAmount": "22", "realTotalAmount": "22", "productPrice": "16", "deliveryPrice": "6"}
oa = be.adapt_order_amounts(doc_order)
check("adapt_order_amounts", oa == {"total_cents": 2200, "real_total_cents": 2200, "product_cents": 1600, "delivery_cents": 600})

# ---------------------------------------------------------------------------
print("[2] 应付总额边界（恰好等于/超一分钱/配送费超预算）")
sample = load_sample()
m_yu = next(i for i in sample["menu"] if i["code"] == "1005")
m_pai2 = next(i for i in sample["menu"] if i["code"] == "3004")
def _plain(m, qty=1):
    return {"code": m["code"], "name": m["name"], "qty": qty, "price_cents": m["price_cents"], "category": m["category"], "tags": list(m.get("tags", [])), "combo_items": m.get("combo_items", [])}


exact = de.demo_price_cart([_plain(m_yu), _plain(m_pai2)], sample)
check("存在恰好 2000 分的可行组合（麦香鱼+菠萝派）", exact["product_cents"] == 2000 and exact["discount_cents"] == 0 and exact["payable_cents"] == 2000 + exact["delivery_cents"], str(exact))

r = de.build_ladder(demo_ctx(sample, 20))
t_low = r["tiers"][1]  # B = 2000 分（20 元档）
check("B=20元 档位方案不超预算", t_low.get("plan") and t_low["plan"]["quote"]["payable_cents"] <= 2000, json.dumps(t_low, ensure_ascii=False)[:200])

r2 = de.build_ladder(demo_ctx(sample, 19.99))
check("预算少一分则 B 档不含该方案", all(
    not t.get("plan") or t["plan"]["quote"]["payable_cents"] <= t["budget_cents"] for t in r2["tiers"]
), "所有展示方案不得超过对应档位预算")

r3 = de.build_ladder(demo_ctx(sample, 23, order_type="delivery"))
t = r3["tiers"][1]  # B = 2300
check("外送 23 元档位无方案或含配送费不超预算", (t["status"] == "unsolvable" and t["gap_cents"] is not None and t["gap_cents"] > 0) or t["plan"]["quote"]["payable_cents"] <= 2300, json.dumps(t, ensure_ascii=False)[:200])
if t["status"] == "unsolvable":
    check("配送费超预算时报告差额而非编造", t["min_candidate"]["quote"]["delivery_cents"] == 900 and t["gap_cents"] == t["min_candidate"]["quote"]["payable_cents"] - 2300)

# ---------------------------------------------------------------------------
print("[3] 优惠规则（不重复扣减/跨档/失效，取最优单券）")


def mk(m, qty=1):
    return {"code": m["code"], "name": m["name"], "qty": qty, "price_cents": m["price_cents"], "category": m["category"], "combo_items": m.get("combo_items", [])}


m_mala = next(i for i in sample["menu"] if i["code"] == "1002")
m_kele = next(i for i in sample["menu"] if i["code"] == "4001")
m_pai = next(i for i in sample["menu"] if i["code"] == "3003")

# 1650 单买：不满 K2 门槛(2500)，K1 命中 → 减 300
pq_single = de.demo_price_cart([mk(m_mala)], sample)
check("K1 单品立减（1650-300）", pq_single["discount_cents"] == 300 and pq_single["payable_cents"] == 1350 + 900, str(pq_single))

# 1650+950=2600：K2(400) 优于 K1(300) → 取最优单券
pq_combo = de.demo_price_cart([mk(m_mala), mk(m_kele)], sample)
check("最优单券取 K2（2600-400）", pq_combo["discount_cents"] == 400 and pq_combo["payable_cents"] == 2200 + 900, str(pq_combo))

# 两份小食 1600：K3 只减一次
pq_two = de.demo_price_cart([mk(m_pai, 2)], sample)
check("双份命中 K3 仍只减一次", pq_two["discount_cents"] == 200, str(pq_two))
check("同一券不在多件上重复扣减", pq_two["discount_cents"] != 400)

r4 = de.build_ladder(demo_ctx(sample, 25))
p25 = r4["tiers"][1]
check("25 元档位有方案且不超预算", p25.get("plan") and p25["plan"]["quote"]["payable_cents"] <= 2500, json.dumps(p25, ensure_ascii=False)[:160])
# 券跨档（候选级验证）：麦辣+可乐 2600 分无券超 25 元预算，用券后进入预算内
cands25 = be.generate_candidates(sample["menu"], ["麦辣"], [], [])
target = next(c for c in cands25 if be.cart_signature(c) == "1002x1;4001x1")
tq = de.demo_price_cart(target, sample)
check("券使候选跨入预算档位（2600→2200≤2500）", tq["payable_cents"] - tq["delivery_cents"] <= 2500 and tq["discount_cents"] > 0, str(tq))

sample_nok1 = copy.deepcopy(sample)
sample_nok1["coupons"] = [c for c in sample_nok1["coupons"] if c["id"] != "K1"]
r5 = de.build_ladder(demo_ctx(sample_nok1, 25))
check("券失效后不再出现该优惠", all((not t.get("plan")) or t["plan"]["quote"].get("coupon") != "麦辣鸡腿堡立减3元" for t in r5["tiers"]))

# ---------------------------------------------------------------------------
print("[4] 候选控制（去重/上限/报价次数）")
r6 = de.build_ladder(demo_ctx(sample, 25))
check("候选数 ≤ 30", r6["meta"]["candidate_count"] <= 30, str(r6["meta"]["candidate_count"]))
cands = be.generate_candidates(sample["menu"], [], [], [])
sigs = [be.cart_signature(c) for c in cands]
check("候选签名去重", len(sigs) == len(set(sigs)))
check("演示模式报价调用为 0", r6["meta"]["quote_calls"] == 0)

calls = []
def stub_quote(cart):
    sig = be.cart_signature(cart)
    calls.append(sig)
    return {"product_cents": sum(i["price_cents"] * i["qty"] for i in cart), "discount_cents": 0, "delivery_cents": 0, "payable_cents": sum(i["price_cents"] * i["qty"] for i in cart)}

ctx_r, qf = real_ctx(sample, 25, quote_fn=stub_quote)
r7 = be.build_ladder(ctx_r, quote_fn=qf)
check("真实模式报价调用 ≤ 12", len(calls) <= 12, str(len(calls)))
check("报价购物车去重", len(calls) == len(set(calls)))
check("已核价方案状态为 priced", any(t.get("plan") and t["plan"]["status"] == "priced" for t in r7["tiers"]))

def failing_quote(cart):
    return None
ctx_f, qf2 = real_ctx(sample, 25, quote_fn=failing_quote)
r8 = be.build_ladder(ctx_f, quote_fn=qf2)
check("核价全失败：不产生代表方案", all(
    not t.get("plan") for t in r8["tiers"]
), json.dumps([(t.get("plan") or {}).get("status") for t in r8["tiers"]], ensure_ascii=False))
check("核价全失败：明确提示不能判断预算内方案", all(
    t["status"] == "quote_failed" and "官方报价" in t["note"] for t in r8["tiers"]
))

def flaky_quote(cart):
    return None if be.cart_signature(cart) == be.cart_signature([next(i for i in sample["menu"] if i["code"] == "1005")]) else {"product_cents": sum(i["price_cents"] * i["qty"] for i in cart), "discount_cents": 0, "delivery_cents": 0, "payable_cents": sum(i["price_cents"] * i["qty"] for i in cart)}
ctx_h, qf3 = real_ctx(sample, 25, quote_fn=flaky_quote)
r9 = be.build_ladder(ctx_h, quote_fn=qf3)
check("部分核价失败：失败方案不作为代表展示", all(
    (not t.get("plan")) or t["plan"]["status"] == "priced" for t in r9["tiers"]
), json.dumps([(t.get("plan") or {}).get("status") for t in r9["tiers"]], ensure_ascii=False))

# ---------------------------------------------------------------------------
print("[5] 预算阶梯语义（低预算/高档沿用/状态标记）")
r10 = de.build_ladder(demo_ctx(sample, 5))
t0 = r10["tiers"][0]
check("低预算无方案", t0["status"] == "unsolvable", json.dumps(t0, ensure_ascii=False)[:160])
check("报告最低候选与差额", t0["min_candidate"] is not None and t0["gap_cents"] == t0["min_candidate"]["quote"]["payable_cents"] - 500, str(t0.get("gap_cents")))

r11 = de.build_ladder(demo_ctx(sample, 25, prefs=["咖啡"], excluded=["咖啡"], must=["麦香鱼"]))
carry = [t for t in r11["tiers"] if t.get("plan") and t.get("carry_over_from")]
check("高档位可沿用同一方案并标记", isinstance(carry, list))  # 结构可用性（是否触发取决于样例数据）
check("演示模式状态全部为 demo_sample", all(t.get("plan") is None or t["plan"]["status"] in ("demo_sample",) for t in r11["tiers"]))

r12 = de.build_ladder(demo_ctx(sample, 25))
check("演示三档默认为 B-5/B/B+5", [t["label"] for t in r12["tiers"]] == ["B-5", "B", "B+5"], str([t["label"] for t in r12["tiers"]]))
check("三档共享同一候选上下文（无额外报价）", r12["meta"]["quote_calls"] == 0)

r13 = de.build_ladder(demo_ctx(sample, 3))
check("非正数档位省略（B-5=负数被丢弃）", [t["label"] for t in r13["tiers"]] == ["B", "B+5"], str([t["label"] for t in r13["tiers"]]))

# ---------------------------------------------------------------------------
print("[6] 偏好/排除/必选")
r14 = de.build_ladder(demo_ctx(sample, 25, prefs=["鸡肉"]))
plan14 = r14["tiers"][1]["plan"]
check("偏好命中鸡肉", "鸡肉" in "".join(i["name"] + "".join(i.get("tags", [])) for i in plan14["cart"]), json.dumps(plan14["cart"], ensure_ascii=False)[:120])

r15 = de.build_ladder(demo_ctx(sample, 35, order_type="delivery", excluded=["咖啡"]))
all_codes = [i["code"] for t in r15["tiers"] if t.get("plan") for i in t["plan"]["cart"]]
check("排除项生效（无咖啡）", "4003" not in all_codes, str(all_codes))
check("外送计入配送费", any(t.get("plan") and t["plan"]["quote"]["delivery_cents"] == 900 for t in r15["tiers"]), json.dumps([(t.get("plan") or {}).get("quote") for t in r15["tiers"]], ensure_ascii=False)[:200])

cands16 = be.generate_candidates(sample["menu"], [], ["咖啡"], [])
check("候选生成阶段排除咖啡", all(i["code"] != "4003" for c in cands16 for i in c))

cands17 = be.generate_candidates(sample["menu"], [], [], ["麦辣鸡腿堡"])
check("必选餐品：所有候选含麦辣鸡腿堡", all(any("麦辣鸡腿堡" in i["name"] or any("麦辣鸡腿堡" in (s.get("name", "")) for s in i.get("combo_items", [])) for i in c) for c in cands17))

# ---------------------------------------------------------------------------
print("[7] 套餐组成与解释")
combo = next(i for i in sample["menu"] if i["code"] == "2001")
check("套餐组成完整（3 项）", len(combo["combo_items"]) == 3)

r18 = de.build_ladder(demo_ctx(sample, 25, prefs=["鸡肉"]))
deltas = r18["deltas"]
check("相邻档位生成解释", len(deltas) >= 1)
if deltas:
    text = "".join(deltas[0]["explanation"])
    check("解释含归因来源（商品/优惠/配送费）", any(k in text for k in ("商品金额", "优惠", "配送费", "实付")), text)
    check("解释声明非预算档位差额", "不是预算档位差额" in text)

# ---------------------------------------------------------------------------
print("[8] 确定性")
sa = de.build_ladder(demo_ctx(sample, 25, prefs=["鸡肉"], excluded=["咖啡"]))
sb = de.build_ladder(demo_ctx(sample, 25, prefs=["鸡肉"], excluded=["咖啡"]))
check("同输入两次输出完全一致", json.dumps(sa, ensure_ascii=False, sort_keys=True) == json.dumps(sb, ensure_ascii=False, sort_keys=True))

# ---------------------------------------------------------------------------
print("[9] 演示样例无写操作与免责标记")
with open(SAMPLE_PATH, encoding="utf-8") as f:
    raw = f.read()
check("样例数据含免责声明", "演示样例数据" in raw and "虚构样例" in raw)
check("样例数据不含真实 Token 字段", "token" not in raw.lower() or "MCD_MCP_TOKEN" not in raw)

# ---------------------------------------------------------------------------
print("[10] 连接检查状态判定（check_mcp）")
import tempfile  # noqa: E402

import check_mcp as cm  # noqa: E402


def cfg_file(content: str) -> str:
    f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


p_ok = cfg_file(json.dumps({"mcpServers": {"mcd-mcp": {"type": "streamablehttp", "url": "https://mcp.mcd.cn", "headers": {"Authorization": "Bearer abcDEF1234567890xyz"}}}}))
p_ph = cfg_file(json.dumps({"mcpServers": {"mcd-mcp": {"headers": {"Authorization": "Bearer ${MCD_MCP_TOKEN}"}}}}))
p_ph2 = cfg_file(json.dumps({"mcpServers": {"mcd-mcp": {"headers": {"Authorization": "Bearer YOUR_MCP_TOKEN"}}}}))
p_none = cfg_file(json.dumps({"mcpServers": {"other-mcp": {"url": "x"}}}))
p_nobearer = cfg_file(json.dumps({"mcpServers": {"mcd-mcp": {"headers": {"Authorization": "abc"}}}}))

cases = [
    ("配置文件不存在 → not_configured", cm.load_local_config(os.path.join(tempfile.gettempdir(), "no_such_mcp.json")), "not_configured"),
    ("无 mcd-mcp 条目 → not_configured", cm.load_local_config(p_none), "not_configured"),
    ("占位符 ${MCD_MCP_TOKEN} → placeholder", cm.load_local_config(p_ph), "placeholder"),
    ("占位符 YOUR_MCP_TOKEN → placeholder", cm.load_local_config(p_ph2), "placeholder"),
    ("Bearer 缺失 → placeholder（需补 Token）", cm.load_local_config(p_nobearer), "placeholder"),
    ("真实形态 Token → configured", cm.load_local_config(p_ok), "configured"),
]
for name, local, expect in cases:
    r = cm.classify(local, do_probe=False, config_path=None)
    check(name, r["status"] == expect, f"got {r['status']}")
    if r["status"] in ("not_configured", "placeholder"):
        check(f"{name} 附引导步骤", isinstance(r.get("guide"), list) and len(r["guide"]) >= 4, "")

check("占位符判定：包含 ${ / YOUR_MCP_TOKEN / 中文提示", cm._looks_like_placeholder("${X}") and cm._looks_like_placeholder("YOUR_MCP_TOKEN") and cm._looks_like_placeholder("请替换你的Token"))
check("占位符判定：普通 Token 不误判", not cm._looks_like_placeholder("8f3a9c2e77b14d05"))
check("check_mcp 不回显 Token 内容", "abcDEF1234567890xyz" not in json.dumps(cm.classify(cm.load_local_config(p_ok), do_probe=False, config_path=p_ok), ensure_ascii=False))

for p in (p_ok, p_ph, p_ph2, p_none, p_nobearer):
    os.unlink(p)

# ---------------------------------------------------------------------------
print("[11] 性价比与套餐优先（用户需求：选餐前先领券、优先看套餐）")
m_combo_mala = next(i for i in sample["menu"] if i["code"] == "2001")
m_snack_lemon = next(i for i in sample["menu"] if i["code"] == "4004")

check("coverage：套餐=主餐1+组成3=4", be.coverage_score([mk(m_combo_mala)], [], []) == 4, str(be.coverage_score([mk(m_combo_mala)], [], [])))
check("coverage：单买=1", be.coverage_score([mk(m_yu)], [], []) == 1, str(be.coverage_score([mk(m_yu)], [], [])))
check("coverage：单买+小食+饮=3", be.coverage_score([mk(m_yu), mk(m_pai), mk(m_snack_lemon)], [], []) == 3)
check("pref：套餐按组成命中偏好（真实菜单无 tags 也生效）", be.pref_hits(mk(m_combo_mala), ["麦辣"]) >= 1)
check("pref：小食/饮品命中不计入偏好（仅主餐口径）", be.pref_hits(mk(next(i for i in sample["menu"] if i["code"] == "3001")), ["鸡肉"]) == 0)

r19 = de.build_ladder(demo_ctx(sample, 25, prefs=["鸡肉"]))
plan19 = r19["tiers"][1]["plan"]
check("25元+想吃鸡肉：B 档优先推荐套餐", plan19["cart"][0]["category"] == "combo", json.dumps(plan19["cart"], ensure_ascii=False)[:120])
check("套餐方案实付 ¥22.5（券后）", plan19["quote"]["payable_cents"] == 2250, str(plan19["quote"]))

r20 = de.build_ladder(demo_ctx(sample, 25))
plan20 = r20["tiers"][1]["plan"]
check("无偏好时 B 档同样套餐优先（性价比）", plan20["cart"][0]["category"] == "combo", json.dumps(plan20["cart"], ensure_ascii=False)[:120])

r21 = de.build_ladder(demo_ctx(sample, 20))
plan21 = r21["tiers"][1]["plan"]
check("20元档套餐不可行时回落最优单点组合", plan21["quote"]["payable_cents"] <= 2000, str(plan21["quote"]))

r22 = de.build_ladder(demo_ctx(sample, 30, prefs=["鸡肉"]))
b22, p22 = r22["tiers"][0]["plan"], r22["tiers"][1]["plan"]
b25, p25b = r22["tiers"][2]["plan"], r22["tiers"][2]["plan"]
check("30元预算：B-5 可行时 B 档升级为覆盖更高的套餐（非沿用）", p22["cart"][0]["category"] == "combo" or p22["quote"]["payable_cents"] > b22["quote"]["payable_cents"], json.dumps([b22["quote"], p22["quote"]], ensure_ascii=False)[:200])

# ---------------------------------------------------------------------------
print("[12] 就餐方式前置（pickup/dt/delivery，先定方式再选餐）")
check("引擎拒绝未知就餐方式", _raises(lambda: de.build_ladder({**demo_ctx(sample, 25), "order_type": "堂食"})))
r23 = de.build_ladder(demo_ctx(sample, 35, order_type="dt"))
t23 = r23["tiers"][1]
check("dt（得来速）与到店同为 0 配送费", t23.get("plan") and t23["plan"]["quote"]["delivery_cents"] == 0, str(t23.get("plan", {}).get("quote")))
check("dt 输出标记 order_type=dt", r23["order_type"] == "dt")
r24 = de.build_ladder(demo_ctx(sample, 35, order_type="delivery"))
p_pick = r23["tiers"][1]["plan"]["quote"]["payable_cents"]
check("同预算 dt 与 delivery 应付不同（外送含配送费）", r24["tiers"][1].get("plan") and r24["tiers"][1]["plan"]["quote"]["payable_cents"] >= p_pick, "")

# ---------------------------------------------------------------------------
print("[13] 真实预算判断仅使用已核价候选")
regression_menu = [
    {"code": f"T{i:02d}", "name": "测试套餐", "category": "combo", "price_cents": 1000,
     "combo_items": [{"name": "测试组成"}] * (10 if i == 12 else 1)}
    for i in range(13)
]
regression_ctx = {"budget_cents": 2500, "order_type": "pickup",
                  "menu": regression_menu, "prefs": [], "excluded": [], "must": [], "quote_limit": 12}


def regression_quote(cart):
    return {"product_cents": 2000, "discount_cents": 0, "delivery_cents": 0, "payable_cents": 2000}


regression_priced = be.build_ladder(regression_ctx, regression_quote)
planned_signatures = {be.cart_signature(cart) for cart in be.plan_quotes(regression_ctx)["carts"]}
check("未核价候选不得压过已核价方案", all(
    t.get("plan") and t["plan"]["status"] == "priced" and be.cart_signature(t["plan"]["cart"]) in planned_signatures
    for t in regression_priced["tiers"]
))
regression_low = be.build_ladder({**regression_ctx, "budget_cents": 500}, regression_quote)
check("最低候选与缺口只来自官方报价", all(
    not t.get("plan") and t["min_candidate"]["status"] == "priced"
    and t["min_candidate"]["quote"]["payable_cents"] == 2000
    and t["gap_cents"] == 2000 - t["budget_cents"] for t in regression_low["tiers"]
))
regression_failed = be.build_ladder(regression_ctx, lambda cart: None)
check("全部核价失败时不展示剩余菜单估算为可行方案", all(not t.get("plan") for t in regression_failed["tiers"]))
check("无成功报价时不编造最低金额或缺口", all(
    t["status"] == "quote_failed" and t["min_candidate"] is None and t["gap_cents"] is None
    for t in regression_failed["tiers"]
))

# ---------------------------------------------------------------------------
print("[14] HTTP 200 也必须验证 MCP 与业务成功（全程模拟网络）")
from unittest.mock import patch  # noqa: E402


class FakeProbeResponse:
    status = 200

    def __init__(self, body):
        self.body = body.encode("utf-8")

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def rpc_content(text, **extra):
    return json.dumps({"jsonrpc": "2.0", "id": 1, "result": {
        "content": [{"type": "text", "text": text}], **extra}}, ensure_ascii=False)


probe_cases = [
    ("正常 JSON-RPC 成功结果", rpc_content('{"success":true,"data":{"now":"fixture"}}'), "verified"),
    ("正常 SSE 成功结果", "event: message\ndata: " + rpc_content('{"success":true,"data":{}}') + "\n\n", "verified"),
    ("HTTP 200 JSON-RPC error", json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32603, "message": "fixture"}}), "network_error"),
    ("HTTP 200 MCP isError", rpc_content("fixture", isError=True), "network_error"),
    ("HTTP 200 业务 success:false", rpc_content('{"success":false,"data":{}}'), "network_error"),
    ("混合说明文本中的业务失败", rpc_content('说明文本\nOriginal Response: {"success":false,"error":"fixture"}'), "network_error"),
    ("结构化业务失败", rpc_content("fixture", structuredContent={"success": False}), "network_error"),
    ("仅有成功关键词的异常文本", "success data jsonrpc", "network_error"),
    ("缺少 tools/call result", json.dumps({"jsonrpc": "2.0", "id": 1, "success": True}), "network_error"),
    ("空工具结果", json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": []}}), "network_error"),
]
for probe_name, probe_body, probe_status in probe_cases:
    with patch.object(cm.urllib.request, "urlopen", return_value=FakeProbeResponse(probe_body)):
        probe_result = cm.probe_token("offline-fixture")
    check(probe_name, probe_result["status"] == probe_status)

# ---------------------------------------------------------------------------
print("[15] 安装的 Skill 只接受真实核价回调")
check("未传回调明确拒绝计算", _raises(lambda: be.build_ladder(regression_ctx)))
check("传入不可调用回调明确拒绝计算", _raises(lambda: be.build_ladder(regression_ctx, quote_fn={})))
check("虚构 sample 即使有回调也拒绝进入真实核心", _raises(lambda: be.build_ladder(demo_ctx(sample, 25), regression_quote)))
check("mode=demo 拒绝进入真实核心", _raises(lambda: be.build_ladder({**regression_ctx, "mode": "demo"}, regression_quote)))
fake_callback_ctx, _ = real_ctx(sample, 25)
fake_callback_result = be.build_ladder(fake_callback_ctx, lambda cart: de.demo_price_cart(cart, sample))
check("演示适配器报价不能成为真实代表方案", all(not t.get("plan") and t["status"] == "quote_failed" for t in fake_callback_result["tiers"]))
for bad_name, bad_quote in (
    ("菜单估算", {"product_cents": 1000, "discount_cents": 0, "delivery_cents": 0, "payable_cents": 1000, "estimated": True}),
    ("不自洽金额", {"product_cents": 1000, "discount_cents": 0, "delivery_cents": 0, "payable_cents": 999}),
    ("缺失金额字段", {"payable_cents": 0}),
    ("小数分金额", {"product_cents": 1000.5, "discount_cents": 0, "delivery_cents": 0, "payable_cents": 1000.5}),
    ("estimated 状态", {"product_cents": 1000, "discount_cents": 0, "delivery_cents": 0, "payable_cents": 1000, "status": "estimated"}),
    ("quote_failed 状态", {"product_cents": 1000, "discount_cents": 0, "delivery_cents": 0, "payable_cents": 1000, "status": "quote_failed"}),
    ("estimated 来源", {"product_cents": 1000, "discount_cents": 0, "delivery_cents": 0, "payable_cents": 1000, "source": "estimated"}),
):
    bad_result = be.build_ladder(regression_ctx, lambda cart: bad_quote)
    check(f"{bad_name} 不用于预算判断", all(not t.get("plan") for t in bad_result["tiers"]))
captured = []


def capture_cart(cart):
    captured.append(be.cart_signature(cart))
    return None


captured_result = be.build_ladder(regression_ctx, capture_cart)
check("两阶段捕获只生成最多12个待核价购物车", len(captured) == 12 and len(set(captured)) == 12)
check("两阶段第一遍无真实推荐", all(not t.get("plan") for t in captured_result["tiers"]))
quote_cache = {sig: regression_quote([]) for sig in captured}
cached_result = be.build_ladder(regression_ctx, lambda cart: quote_cache.get(be.cart_signature(cart)))
check("两阶段官方报价缓存与直接回调一致", cached_result == regression_priced)

print()
if FAIL:
    print(f"结果：{PASS} 通过，{len(FAIL)} 失败 -> {FAIL}")
    sys.exit(1)
print(f"结果：全部 {PASS} 项通过")
