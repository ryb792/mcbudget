# MCP_INTEGRATION —— McBudget 与麦当劳 MCP 的集成说明

## 1. 使用的 MCP Server

| 项 | 值 |
|----|----|
| 服务 | 麦当劳中国 MCP（官方远程托管） |
| 地址 | `https://mcp.mcd.cn` |
| 协议 | Streamable HTTP |
| 认证 | `Authorization: Bearer <MCP Token>`（Token 由用户在 open.mcd.cn 申请，仅存于客户端本地配置或环境变量） |
| 限流 | 600 次/分钟（429 = 超限） |
| 配置样例 | `mcp-config.example.json`（JSON 客户端）与 `mcp-config.codex.example.toml`（Codex），仅环境变量占位符或引用 |

## 2. 实际使用的工具与用途

| 工具 | 用途 | 调用时机 |
|------|------|----------|
| `now-time-info` | 获取当前时间，判定时段/预约 | 流程开始（需要时） |
| `query-nearby-stores` | 到店场景找门店（beType=1 到店 / 5 得来速） | 缺门店时 |
| `delivery-query-addresses` | 拉取账号已有配送地址 | 外送缺地址时 |
| `delivery-query-stores` | 按 addressId 查可配门店（beType=2） | 外送选门店 |
| `query-meals` | 当前门店菜单（分类/编码/价格/随单购） | 构建候选前 |
| `query-meal-detail` | 套餐组成与特制结构 | 展示套餐组成/用户要求换子项时 |
| `query-store-coupons` | 当前门店+方式可用券 | 构建候选前/领券后 |
| `available-coupons` / `auto-bind-coupons` / `query-my-coupons` | 麦麦省券查询/一键领券/我的券 | **仅用户要求领券时** |
| `calculate-price` | 官方算价（含配送费/优惠/餐具费） | 每轮 ≤12 个去重购物车；下单前必算 |
| `create-order` | 创建订单 | 用户确认后，且算价未失效 |
| `query-order` / `order-list` | 核实订单状态 | 创建超时/结果不明确时；用户查进度 |

不在 V1 主路径：营养列表、团餐助餐、积分/商城/抽奖/主题活动、`delivery-create-address`（仅用户要求新增地址时）、`cancel-order`（仅用户要求取消时）。

## 3. 数据流（真实模式一轮挑战）

```
用户输入(预算/方式/偏好)
  │
  ├─ 缺门店/地址 → query-nearby-stores / delivery-query-addresses → delivery-query-stores
  │
  ├─ 用户请求或确认领券 → auto-bind-coupons（失败不阻塞）
  │
  ├─ query-meals ──► adapt_query_meals() 菜单(元字符串)──► 统一菜单(分)
  ├─ query-store-coupons ──► 券上下文(仅展示；能否用券以算价为准)
  │
  ├─ budget_engine.build_ladder(ctx)
  │     ├─ 生成 ≤30 个候选购物车(去重、套餐优先排序)
  │     ├─ 前 ≤12 个去重购物车 → calculate-price ──► adapt_quote() 整数分
  │     │     └─ 校验 price == productPrice − discount + deliveryPrice + packingPrice（缺省按 0）
  │     └─ 输出 B-5/B/B+5 阶梯 + 增减解释（三档共享报价）
  │
  ├─ 用户选定方案 → 展示门店/方式/餐品/优惠/餐具/金额 → 确认
  │
  ├─ 下单前重新 calculate-price（内容或金额变化则更新确认）
  │
  └─ create-order(takeWayCode 来自算价 takeWayList / addressId 外送)
        └─ 核对 orderDetail → 支付交付（链接优先 / App 待付订单 / 本地二维码 make_qr.py）
              └─ 用户自行完成支付 → query-order 可查进度
```

演示模式：同一引擎、同一契约，`quote_fn` 为空时用 `assets/sample_data.json` 的样例规则定价，全部方案标记 `demo_sample`，无任何真实写操作。演示页内嵌 JS 引擎与 Python 引擎输出经 `scripts/test_engine_parity.py` 验证一致。

**支付交付边界**：MCP 无支付工具（也不应有——资金操作必须由用户完成）。**默认方式 A（链接优先，2026-10-10 用户确认）**：下单后按固定模板交付纯文本 `payH5Url` + 操作指引（复制到手机，微信/浏览器打开即付，模板内置方式 B 的 App 待付路径兜底）；方式 C 本地二维码（`scripts/make_qr.py`，订单链接不出本机，不走第三方二维码服务）**仅在用户主动要求时**使用。H5 收银页手机端实际表现（是否可直接拉起微信/支付宝）待真实订单实测。

## 4. 报价与下单边界

- **报价有效性**：与 storeCode/beCode/orderType/beType/时段/购物车内容/券绑定。任一变化即失效；预算变化仅可复用"完全相同购物车+上下文"的短期展示报价，下单前必须重新 `calculate-price`。
- **下单原子性**：确认 → 复核算价 → create-order 一次。超时/结果不明确**不自动重试**：有 orderId 走 `query-order`；无 orderId 走 `order-list` 辅助核实；禁止猜测成功或重复创建（避免重复扣款风险）。
- **支付边界**：技能只展示 `payH5Url`，支付动作永远由用户完成。
- **写操作白名单**：领券（用户要求时）、下单（用户确认后）。调整预算、浏览方案、导出卡片均无写操作。

## 5. 错误处理与状态

| 情形 | 表现 | 恢复 |
|------|------|------|
| MCP 未连接 | 运行 `scripts/check_mcp.py` 判定状态（not_configured/placeholder/configured/verified/invalid/network_error），输出安装与绑定引导；期间回落演示模式并明确标注 | 按引导申请 Token（open.mcd.cn）→ 配置连接器 → 启用/信任 → 重新 check |
| 401 认证失败 | 提示 Token 无效/过期 | 重新申请并更新连接器配置 |
| 429 限流 | 提示稍后重试，自动降低调用频率 | 等待后继续 |
| 菜单为空/门店不可售 | 如实说明，不编造餐品 | 换门店/时段或稍后再试 |
| 券失效 | 从候选定价中剔除并重算 | 提示用户券不可用 |
| calculate-price 失败 | 该购物车标记 quote_failed，不展示为可行 | 用户重试或换方案 |
| create-order 超时 | 不自动重试；按第 4 节核实 | 查订单确认后再决定 |

## 6. 真实验证状态（如实声明）

- **已验证（真实 MCP 连接，2026-10-09 实测）**：本机已配置有效 MCP Token（WorkBuddy 本地 mcp.json / 环境变量），通过 `scripts/real_smoke.py` 直连完成只读端到端验证：
  - `now-time-info` ✓；`query-nearby-stores`（肇庆市·端州三路，searchType=2，city 与 keyword **均必传**）✓ 选中麦当劳肇庆端州三路餐厅 storeCode=1420419；
  - `query-meals` ✓ 返回 106 项，`adapt_query_meals` 适配为统一菜单（元字符串→分）；
  - `calculate-price` ✓ 12 次官方算价 0 失败（整数分），25 元预算输出 [priced] 方案：鸡肉堡单品精选应付 ¥24；
  - 实测发现两处与文档示例的差异，均已适配：① 到店场景返回**缺省 deliveryPrice/packingPrice 字段**（按 0 处理，打包费纳入恒等式）；② 返回含文档未列的 `packingPrice`（打包费）与 `enjoyed`/`enjoyable`（优惠明细，`realDiscount` 单位为**元**）。
- **未验证（需用户操作授权）**：`auto-bind-coupons`（会改变账户券状态）、`create-order`（真实下单）及之后的支付流程。首次使用时按第 4 节边界执行，建议先用最小订单验证。
- 字段或行为与本文不符时，**以实际返回为准**并回改 `references/mcp_tools.md` 与适配器。
