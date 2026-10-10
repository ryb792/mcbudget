/* McBudget 确定性引擎（JS 版，演示模式）。
 * 与 scripts/budget_engine.py 保持同一数据约定与同一算法：
 * - 金额一律整数"分"
 * - 候选 ≤30、签名去重、稳定排序
 * - 演示优惠规则：一次购物车取最优单券，同一券不重复扣减
 * - 展示"本轮候选中的推荐"，不宣称全局最便宜
 * 真实模式走麦当劳 MCP（calculate-price 官方算价），由 SKILL.md 流程驱动，不在此文件内。
 */
(function (global) {
  "use strict";

  var MAX_CANDIDATES = 30;
  var MAX_QUOTE_CALLS = 12;
  var TIER_STEP_CENTS = 500;
  var DEMO_STATUS = "demo_sample";
  var UNSOLVABLE_STATUS = "unsolvable";

  function cartSignature(cart) {
    return cart
      .slice()
      .sort(function (a, b) { return a.code < b.code ? -1 : a.code > b.code ? 1 : 0; })
      .map(function (i) { return i.code + "x" + i.qty; })
      .join(";");
  }

  function itemMatchesExclusion(item, excluded) {
    var hay = item.name + (item.tags || []).join("");
    return (excluded || []).some(function (k) { return k && hay.indexOf(k) >= 0; });
  }

  function prefHits(item, prefs) {
    /* 仅主餐口径（main/combo），套餐把自带组成名称一并计入；prefs 为变体组（与 Python 同构） */
    if (item.category !== "main" && item.category !== "combo") return 0;
    var hay = item.name + (item.tags || []).join("");
    (item.combo_items || []).forEach(function (s) { hay += s.name || ""; });
    var n = 0;
    (prefs || []).forEach(function (variants) {
      if (variants.some(function (v) { return v && hay.indexOf(v) >= 0; })) n += 1;
    });
    return n;
  }

  function hasComboItem(cart) {
    return cart.some(function (i) { return i.category === "combo" || (i.combo_items && i.combo_items.length); });
  }

  function violatesMust(cart, must) {
    if (!must || !must.length) return false;
    var hay = "";
    cart.forEach(function (it) {
      hay += it.name + (it.tags || []).join("");
      (it.combo_items || []).forEach(function (s) { hay += s.name || ""; });
    });
    return !must.some(function (k) { return k && hay.indexOf(k) >= 0; });
  }

  function expandPrefs(prefs) {
    /* 与 Python expand_prefs 同构：鸡肉→[鸡肉,鸡]（真实菜单"鸡腿堡"不含"鸡肉"字样）；幂等 */
    if (!prefs || !prefs.length) return [];
    if (Object.prototype.toString.call(prefs[0]) === "[object Array]") {
      return prefs.map(function (g) { return g.slice(); });
    }
    var out = [];
    prefs.forEach(function (k) {
      if (!k) return;
      if (out.indexOf(k) < 0) out.push(k);
      if (k.length >= 2 && k.charAt(k.length - 1) === "肉" && out.indexOf(k.charAt(0)) < 0) out.push(k.charAt(0));
    });
    return out.map(function (k) { return [k]; });
  }

  function cartItem(m, qty) {
    qty = qty || 1;
    return {
      code: m.code, name: m.name, qty: qty, price_cents: m.price_cents,
      category: m.category || "other", tags: (m.tags || []).slice(),
      combo_items: (m.combo_items || []).slice()
    };
  }

  function generateCandidates(menu, prefs, excluded, must, maxCandidates) {
    maxCandidates = maxCandidates || MAX_CANDIDATES;
    prefs = expandPrefs(prefs || []); excluded = excluded || []; must = must || [];
    var mains = [], combos = [], snacks = [], drinks = [];
    menu.forEach(function (m) {
      if (itemMatchesExclusion(m, excluded)) return;
      if (m.category === "main") mains.push(m);
      else if (m.category === "combo") combos.push(m);
      else if (m.category === "snack") snacks.push(m);
      else if (m.category === "drink") drinks.push(m);
    });

    var raw = [];
    combos.forEach(function (c) { raw.push([cartItem(c)]); });
    var snackPool = [null].concat(snacks);
    var drinkPool = [null].concat(drinks);
    mains.forEach(function (b) {
      snackPool.forEach(function (s) {
        drinkPool.forEach(function (d) {
          var cart = [cartItem(b)];
          if (s) cart.push(cartItem(s));
          if (d) cart.push(cartItem(d));
          raw.push(cart);
        });
      });
    });

    var seen = {};
    raw.forEach(function (c) {
      if (violatesMust(c, must)) return;
      var sig = cartSignature(c);
      if (!seen[sig]) seen[sig] = c;
    });

    var ranked = Object.keys(seen).map(function (k) { return seen[k]; });
    ranked.sort(function (a, b) {
      var pa = -totalPref(a, prefs), pb = -totalPref(b, prefs);
      if (pa !== pb) return pa - pb;
      var ca = hasComboItem(a) ? 0 : 1, cb = hasComboItem(b) ? 0 : 1;
      if (ca !== cb) return ca - cb;
      if (a.length !== b.length) return a.length - b.length;
      var sa = cartSignature(a), sb = cartSignature(b);
      return sa < sb ? -1 : sa > sb ? 1 : 0;
    });
    return ranked.slice(0, maxCandidates);
  }

  function totalPref(cart, prefs) {
    var n = 0;
    cart.forEach(function (i) { n += prefHits(i, prefs); });
    return n;
  }

  function demoCouponDiscount(cart, productTotal, cpn) {
    var t = cpn.type;
    if (t === "item_discount") {
      var kw = cpn.target_keyword || "";
      var hit = cart.some(function (i) {
        return kw && i.name.indexOf(kw) >= 0 && i.category === (cpn.target_category || i.category);
      });
      return hit ? cpn.discount_cents : 0;
    }
    if (t === "order_discount") {
      return productTotal >= (cpn.threshold_cents || 0) ? cpn.discount_cents : 0;
    }
    if (t === "category_discount") {
      var sub = 0;
      cart.forEach(function (i) { if (i.category === cpn.category) sub += i.price_cents * i.qty; });
      return sub >= (cpn.threshold_cents || 0) ? cpn.discount_cents : 0;
    }
    return 0;
  }

  function demoPriceCart(cart, sample) {
    var product = 0;
    cart.forEach(function (i) { product += i.price_cents * i.qty; });
    var rule = sample.delivery || {};
    var fee = rule.fee_cents || 0;
    var threshold = rule.free_threshold_cents || 0;
    var delivery = threshold && product >= threshold ? 0 : fee;

    var best = null;
    (sample.coupons || []).forEach(function (cpn) {
      var d = demoCouponDiscount(cart, product, cpn);
      if (d > 0 && (!best || d > best[1])) best = [cpn, d];
    });
    var discount = best ? best[1] : 0;
    return {
      product_cents: product,
      discount_cents: discount,
      delivery_cents: delivery,
      payable_cents: product - discount + delivery,
      coupon: best ? best[0].title : null
    };
  }

  function coverageScore(cart, prefs, must) {
    /* 性价比覆盖度（与 Python coverage_score 同构）：主餐1 + 套餐组成计件 + 单点各1 + 用户槽位加成 */
    var slots = 0;
    cart.forEach(function (it) {
      if (it.category === "main" || it.category === "combo") {
        slots += 1 + (it.combo_items || []).length;
      } else {
        slots += 1;
      }
    });
    var text = "";
    cart.forEach(function (it) {
      text += it.name + (it.tags || []).join("");
      (it.combo_items || []).forEach(function (s) { text += s.name || ""; });
    });
    (must || []).forEach(function (k) { if (k && text.indexOf(k) >= 0) slots += 1; });
    (prefs || []).forEach(function (variants) {
      if (variants.some(function (v) { return v && text.indexOf(v) >= 0; })) slots += 1;
    });
    return slots;
  }

  function rankKey(cart, quote, prefs, must) {
    return [
      -totalPref(cart, prefs),
      hasComboItem(cart) ? 0 : 1,
      -coverageScore(cart, prefs, must),
      quote.payable_cents,
      cartSignature(cart)
    ];
  }

  function cmpKeys(a, b) {
    for (var i = 0; i < a.length; i++) {
      if (a[i] < b[i]) return -1;
      if (a[i] > b[i]) return 1;
    }
    return 0;
  }

  function yuan(cents) {
    var s = (cents / 100).toFixed(2);
    return s.replace(/\.?0+$/, "");
  }

  function itemMap(cart) {
    var m = {};
    cart.forEach(function (i) { m[i.code] = i; });
    return m;
  }

  function explainDelta(lowPlan, highPlan) {
    var out = [];
    var a = itemMap(lowPlan.cart), b = itemMap(highPlan.cart);
    var qa = lowPlan.quote, qb = highPlan.quote;
    var added = [], removed = [];
    Object.keys(b).forEach(function (c) { if (!a[c]) added.push(b[c]); });
    Object.keys(a).forEach(function (c) { if (!b[c]) removed.push(a[c]); });
    var parts = [];
    if (added.length) parts.push("增加 " + added.map(function (i) { return i.name; }).join("、"));
    if (removed.length) parts.push("去掉 " + removed.map(function (i) { return i.name; }).join("、"));
    if (lowPlan.main_code && highPlan.main_code && lowPlan.main_code !== highPlan.main_code && !added.length && !removed.length) {
      parts.push("把「" + a[lowPlan.main_code].name + "」换成「" + b[highPlan.main_code].name + "」");
    }
    Object.keys(a).forEach(function (c) {
      if (b[c] && a[c].qty !== b[c].qty) {
        var dq = b[c].qty - a[c].qty;
        parts.push(a[c].name + (dq > 0 ? " 多" : " 少") + Math.abs(dq) + " 份");
      }
    });
    if (!parts.length) {
      out.push("两档方案相同：更高的预算暂时没有符合偏好的升级，沿用同一方案。");
    } else {
      out.push(parts.join("；") + "。");
    }
    var dProduct = qb.product_cents - qa.product_cents;
    var dDisc = qb.discount_cents - qa.discount_cents;
    var dDeliv = qb.delivery_cents - qa.delivery_cents;
    var dPay = qb.payable_cents - qa.payable_cents;
    var why = [];
    if (dProduct) why.push("商品金额" + (dProduct > 0 ? "增加" : "减少") + " " + yuan(Math.abs(dProduct)) + " 元");
    if (dDisc) why.push("优惠" + (dDisc > 0 ? "多" : "少") + "减 " + yuan(Math.abs(dDisc)) + " 元");
    if (dDeliv) why.push("配送费" + (dDeliv > 0 ? "增加" : "减少") + " " + yuan(Math.abs(dDeliv)) + " 元");
    if (dPay === 0) {
      out.push(why.length ? "实付金额不变（" + why.join("，") + "）。" : "实付金额不变。");
    } else {
      var basis = why.length ? why.join("，") : "组成未变";
      out.push("实付由 " + yuan(qa.payable_cents) + " 元变为 " + yuan(qb.payable_cents) + " 元（" + (dPay > 0 ? "多花" : "少花") + " " + yuan(Math.abs(dPay)) + " 元；来源：" + basis + "）。");
    }
    out.push("以上差额来自实际餐品与官方/样例报价，不是预算档位差额。");
    return out;
  }

  function tierLabel(tb, budget) {
    if (tb === budget) return "B";
    var diff = Math.abs(budget - tb) / 100;
    return "B" + (tb < budget ? "-" : "+") + String(+diff.toFixed(2));
  }

  /* 演示模式 buildLadder（与 Python 版 demo 路径同构）。
   * 此处没有真实报价分支；Python 的真实模式仅用成功的官方报价判断预算。
   */
  function buildLadder(ctx) {
    var budget = ctx.budget_cents;
    var orderType = ctx.order_type || "pickup";
    var prefs = expandPrefs(ctx.prefs || []), excluded = ctx.excluded || [], must = ctx.must || [];
    var sample = ctx.sample;
    var menu = ctx.menu;

    var candidates = generateCandidates(menu, prefs, excluded, must);
    var quotes = {};
    candidates.forEach(function (cart) {
      var q = demoPriceCart(cart, sample);
      if (orderType === "pickup" || orderType === "dt") {
        q.delivery_cents = 0;
        q.payable_cents = q.product_cents - q.discount_cents;
      }
      quotes[cartSignature(cart)] = q;
    });

    var tiers = [];
    var prevPlan = null, prevLabel = null;
    [budget - TIER_STEP_CENTS, budget, budget + TIER_STEP_CENTS]
      .filter(function (b) { return b > 0; })
      .forEach(function (tb) {
        var feasible = candidates.filter(function (c) {
          return quotes[cartSignature(c)].payable_cents <= tb;
        });
        var entry = { budget_cents: tb, label: tierLabel(tb, budget) };
        if (feasible.length) {
          var rep = feasible[0];
          feasible.forEach(function (c) {
            if (cmpKeys(rankKey(c, quotes[cartSignature(c)], prefs, must), rankKey(rep, quotes[cartSignature(rep)], prefs, must)) < 0) rep = c;
          });
          var sig = cartSignature(rep);
          var plan = {
            cart: rep,
            quote: quotes[sig],
            status: DEMO_STATUS,
            main_code: (rep.filter(function (i) { return i.category === "main" || i.category === "combo"; })[0] || {}).code || null,
            signature: sig
          };
          if (prevPlan && prevPlan.signature === sig) plan.carry_over_from = prevLabel;
          entry.status = plan.status;
          entry.plan = plan;
          prevPlan = plan;
          prevLabel = entry.label;
        } else {
          var lowest = null;
          candidates.forEach(function (c) {
            if (!lowest || quotes[cartSignature(c)].payable_cents < quotes[cartSignature(lowest)].payable_cents ||
              (quotes[cartSignature(c)].payable_cents === quotes[cartSignature(lowest)].payable_cents && cartSignature(c) < cartSignature(lowest))) lowest = c;
          });
          entry.status = UNSOLVABLE_STATUS;
          entry.min_candidate = lowest ? { cart: lowest, quote: quotes[cartSignature(lowest)], status: DEMO_STATUS } : null;
          entry.gap_cents = lowest ? quotes[cartSignature(lowest)].payable_cents - tb : null;
        }
        tiers.push(entry);
      });

    var pricedPlans = tiers.filter(function (t) { return t.plan; });
    var deltas = [];
    for (var i = 1; i < pricedPlans.length; i++) {
      deltas.push({
        from: pricedPlans[i - 1].label,
        to: pricedPlans[i].label,
        explanation: explainDelta(pricedPlans[i - 1].plan, pricedPlans[i].plan)
      });
    }

    return {
      mode: "demo",
      order_type: orderType,
      budget_cents: budget,
      tiers: tiers,
      deltas: deltas,
      meta: {
        candidate_count: candidates.length,
        quote_calls: 0,
        max_candidates: MAX_CANDIDATES,
        max_quote_calls: MAX_QUOTE_CALLS,
        deterministic: true,
        claim: "本轮候选中的推荐，不构成全局最便宜或穷尽全部组合的承诺"
      }
    };
  }

  global.McBudgetEngine = {
    cartSignature: cartSignature,
    generateCandidates: generateCandidates,
    demoPriceCart: demoPriceCart,
    buildLadder: buildLadder,
    explainDelta: explainDelta,
    yuan: yuan,
    MAX_CANDIDATES: MAX_CANDIDATES
  };
})(typeof window !== "undefined" ? window : globalThis);
