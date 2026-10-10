# McBudget 真实 MCP 数据约定

本约定用于安装后的真实 Skill：门店、菜单、券与报价都来自当前麦当劳 MCP。预算引擎必须收到官方报价回调，未连接或未获得成功核价时不能生成可下单方案。

## 1. 就餐方式

`order_type` 为 `pickup`（到店，beType=1）、`dt`（得来速，beType=5）或 `delivery`（外送，beType=2）。先确认方式再查门店、菜单、券；方式变化后重新建立上下文。到店子方式由算价 `takeWayList` 决定。

外送预算包含配送费；估算只安排核价顺序，实际费用始终取官方算价。

## 2. 金额

- 内部一律整数分；展示时除以 100。
- 输入单位按来源显式声明：`user_yuan` 为用户预算元，`menu_yuan` 为菜单元字符串，`quote_cents` 为算价整数分，`order_yuan` 为订单元字符串。
- 转换通过 `to_cents` / `from_cents`，元转分以 HALF_UP 保留到分，不按数值大小猜单位。
- 官方适配校验：`price = productPrice − discount + deliveryPrice + packingPrice`。缺省配送与打包费按 0；不自洽即拒绝使用。
- 引擎统一报价的 `delivery_cents` 包含适配后的配送费与打包费，恒等式为 `payable_cents = product_cents − discount_cents + delivery_cents`。不再次扣减优惠或重复加费用。

## 3. 上下文与报价回调

`build_ladder(ctx, quote_fn=callback)` 的 ctx 字段：

| 字段 | 类型与来源 |
| --- | --- |
| `budget_cents` | 用户预算转换后的整数分，总应付上限 |
| `order_type` | 用户确认的 pickup / dt / delivery |
| `menu` | 从当前 query-meals 适配的菜单，含 code、name、category、price_cents、tags、可确认的套餐组成 |
| `prefs` / `excluded` / `must` | 用户口味、排除项与必选项关键词列表 |
| `delivery_fee_cents` | 可选；仅用于外送估算排序，不能替代核价 |
| `mode` | 可省略；如提供必须为 real |

不提供样例数据字段。没有可调用的 quote_fn 时引擎拒绝运行。

回调收到候选购物车后，由客户端根据真实详情和当前 schema 构建完整 items：券商品带真实券标识，套餐带真实轮次与子项，特制带真实选项。只有结构完整的购物车才提交 `calculate-price`；通过 `adapt_quote` 将成功结果转换为：

```text
product_cents / discount_cents / delivery_cents / payable_cents：非负整数分
quoted_at：可选，记录本轮收到官方核价结果的带时区 ISO 8601 时间
```

失败、缺失或字段不合法时回调返回 `None`，不自行定价。

只能逐次调用 MCP 的客户端可分两阶段：先记录候选且返回 None；逐一官方核价；再以同上下文中的报价缓存作为回调重新运行。首轮不产生可用推荐，缓存不跨门店、方式、时段、商品或券变化复用。

## 4. 候选与排序

- 默认单人点餐：恰好一份主餐或套餐；非套餐可配最多一份小食与一份饮品，不为花光预算堆叠商品。
- 排除项命中即弃置，无法满足必选项即弃置。
- 引擎购物车签名由排序后的商品 code 与 qty 生成。客户端还须保证完整结构与业务上下文一致，不把不同套餐子项或券配置的报价合并。
- 每轮最多 30 个候选，最多 12 个去重购物车官方核价；B−5 / B / B＋5 共享本轮候选与报价。
- 菜单估算仅决定核价顺序；预算判断、推荐与最低金额缺口均只使用成功官方报价。
- 代表方案排序：主餐偏好命中优先 → 套餐优先 → 覆盖度高优先 → 应付低优先 → 签名稳定排序。推荐是本轮候选中的结果，不表示穷尽全部组合。
- 领券仅在用户请求或确认后执行；领取后重查门店券并重新核价。

## 5. 状态

| 状态 | 含义与展示 |
| --- | --- |
| `estimated` | 内部待核价估算，只用于安排报价顺序，不展示为可行方案 |
| `priced` | 官方核价成功，可用于展示；下单前仍须重新核价 |
| `quote_failed` | 核价失败，不参与可下单方案筛选 |
| `carry_over_from` | 高档沿用同一方案的附加标记，解释没有合适升级 |
| `unsolvable` | 已核价候选没有预算内方案，报告真实最低应付与差额 |

全部报价失败时不展示虚构的最低金额或预算缺口。

## 6. 增减解释

比较相邻档的商品与数量，说明新增、移除、替换及商品金额、优惠、相关费用变化。实际付款差额来自真实餐品与官方报价，不等同于预算档位的 5 元差。

## 7. 真实结果卡

`scripts/render_card.py` 接收引擎的 real 阶梯 JSON，仅接受已核价的所选档位。生成本地 HTML 后在浏览器导出 PNG：

```bash
python scripts/render_card.py --input ladder.json --output result.html --tier B --quoted-at "本轮核价的带时区ISO8601时间"
```

`--tier` 默认 B。`--quoted-at` 可在输入 result、plan 或 quote 已包含有效 `quoted_at` 时省略。客户端应记录实际核价时间；生成时间不能冒充报价时间。

卡片仅展示预算、餐品、应付、剩余预算、增减解释与核价时间。不得包含 Token、手机号、地址、券码、支付链接、完整订单号或原始账户响应。用户需要查订单时，订单号展示可截断为尾四位并说明。
