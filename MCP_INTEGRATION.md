# McBudget 与麦当劳 MCP 的集成说明

## 1. 使用的 MCP Server

| 项 | 值 |
| --- | --- |
| 服务 | 麦当劳中国 MCP（官方远程托管） |
| 地址 | `https://mcp.mcd.cn` |
| 协议 | Streamable HTTP |
| 认证 | `Authorization: Bearer <MCP Token>`；用户在 [开放平台](https://open.mcd.cn)申请，Token 仅存于本机配置或环境变量 |
| 限流 | 600 次/分钟；429 表示超限 |
| 配置样例 | `mcp-config.example.json` 与 `mcp-config.codex.example.toml`，仅含占位符或环境变量引用 |

Skill 只使用真实 MCP 数据。未连接时按 [安装指引](docs/GETTING_STARTED.md)配置并验证，不生成替代餐单或报价。调用前发现当前客户端中的工具名与 schema；工具名前缀和字段以当前服务为准。

## 2. 工具与调用时机

| 工具 | 用途 | 调用时机 |
| --- | --- | --- |
| `now-time-info` | 当前时间与时段上下文 | 流程开始，需要时 |
| `query-nearby-stores` | 找到店或得来速门店 | 缺门店时；beType=1 到店、5 得来速 |
| `delivery-query-addresses` | 获取账户已有配送地址 | 外送缺地址时 |
| `delivery-query-stores` | 按 addressId 查可配门店 | 外送选择门店；beType=2 |
| `query-meals` | 获取当前门店菜单 | 构建候选前 |
| `query-meal-detail` | 套餐轮次、默认子项与特制结构 | 构建完整套餐或用户要求调整时 |
| `query-store-coupons` | 当前门店与方式可用券 | 构建候选前、领券后 |
| `available-coupons` / `auto-bind-coupons` / `query-my-coupons` | 查询可领券、领取券与查询我的券 | **领取只在用户请求或确认后执行** |
| `calculate-price` | 官方算价，含优惠与相关费用 | 每轮最多 12 个去重购物车；下单前重新算价 |
| `create-order` | 创建真实订单 | 用户确认后，且最终算价仍适用 |
| `query-order` / `order-list` | 核实订单与查看进度 | 创建结果不明确时、用户要求查进度时 |

营养、积分、商城、抽奖、团餐等能力不属于当前主流程。`delivery-create-address` 与 `cancel-order` 仅在用户明确要求新增地址或取消订单时处理。

## 3. 一轮预算挑战的数据流

```text
用户输入预算、就餐方式和口味
  → 确认到店 / 得来速 / 外送，再选真实门店或地址
  → 用户请求或确认领券时 auto-bind-coupons
  → query-meals + query-meal-detail + query-store-coupons
  → 适配菜单，构建完整且可核价的候选购物车
  → build_ladder(ctx, quote_fn=callback)
      → 生成最多 30 个候选
      → 最多 12 个去重购物车提交 calculate-price
      → 校验并适配官方报价，输出 B-5 / B / B+5 与增减解释
  → 用户选定方案，下单前重新 calculate-price
  → 展示最终门店、方式、餐品、优惠、餐具、应付金额
  → 用户确认后 create-order
  → 核对 orderDetail，交付支付链接
  → 用户完成支付；需要时 query-order 查询结果
```

**客户端对接**：预算引擎不自己调用 MCP。调用方将真实菜单适配为统一格式，构建含券、套餐轮次、特制等必要字段的完整购物车，提交当前 `calculate-price`，再通过 `adapt_quote` 返回整数分报价。不能确认完整结构的候选不用于真实订单。

如果客户端只能在对话中逐次调用工具，可以先用记录购物车并返回 `None` 的回调收集本轮候选，逐一官方核价，再通过本轮报价缓存重新运行引擎。两次运行必须保持同一输入与门店、方式、时段上下文；首轮没有成功报价，不是可用餐单。`scripts/real_smoke.py` 提供只读程序对接示例。

**卡片交付**：`scripts/render_card.py` 从已核价的阶梯结果生成本地 HTML，可在浏览器中导出 PNG。仅使用成功核价的选定方案与本轮带时区的核价时间；不使用生成时间冒充核价时间，不读取账户信息。输入约定见 [数据约定](references/data_conventions.md)。

**支付交付**：创建订单后交付 `payH5Url` 纯文本及手机打开指引，并提供 App 待付订单路径兜底。用户主动要求二维码时，可使用 `scripts/make_qr.py` 在本机生成，订单链接不发送给第三方二维码服务。支付在用户打开的官方收银流程中完成，技能不代替用户执行付款。

## 4. 报价与下单边界

- **报价有效性**：与 storeCode、beCode、orderType、beType、时段、购物车及券绑定。任一变化即重新核价；相同购物车的展示报价也须在下单前刷新。
- **金额校验**：实测官方返回满足 `price = productPrice − discount + deliveryPrice + packingPrice`，到店缺省配送费与打包费按 0。字段不自洽时停止使用该报价，按当前 schema 核实费用归属，不能重复扣减优惠。
- **下单确认**：最终核价后展示订单信息并确认。内容或金额变化时更新确认，不用先前同意替代对变化的确认。
- **避免重复订单**：`create-order` 超时或结果不明确时不自动重试；有 orderId 查 `query-order`，没有则通过 `order-list` 辅助核实。
- **状态变化**：领券会改变账户券状态，只在用户请求或确认后执行。调预算、浏览方案和导出卡片均不创建订单。
- **支付**：订单支付链接只向当前用户交付，不进入日志、仓库或挑战卡；用户完成付款。

## 5. 错误处理

| 情形 | 表现与恢复 |
| --- | --- |
| MCP 未连接 | 检查当前工具与本机配置，提供安装、Token 申请及连接指引；连接成功后再继续 |
| 401 认证失败 | 提示 Token 无效或失效，更新本机配置后重试 |
| 429 限流 | 降低调用频率，等待后继续 |
| 菜单为空或门店不可售 | 如实说明，换门店、时段或稍后重试 |
| 券不可用或领取失败 | 重新查询现有可用券并核价；不虚构减免 |
| 算价失败 | 标记 `quote_failed`，不作为预算内方案 |
| 全部报价失败 | 说明本轮没有可用官方报价，不计算虚构预算缺口 |
| 创建订单结果不明确 | 先查订单核实，不自动重复创建 |

## 6. 真实验证记录

### 已记录的只读端到端实测

源项目记录于 2026-10-09 使用 `scripts/real_smoke.py` 直连麦当劳 MCP：

- `now-time-info` 与 `query-nearby-stores` 调用成功；肇庆市端州三路餐厅，storeCode=1420419。searchType=2 时 city 与 keyword 均必传。
- `query-meals` 返回 106 项，菜单的元字符串成功适配为整数分。
- `calculate-price` 完成 12 次官方算价、0 失败；当时 25 元预算返回已核价方案，鸡肉堡单品精选应付 24 元。该金额是历史验证记录，不能用作当前门店价格。
- 适配了到店返回中可能缺省的 deliveryPrice、packingPrice，以及实测出现的 packingPrice、enjoyed、enjoyable 字段。优惠明细 realDiscount 单位为元。

### 开发者补充确认的真实流程

开发者在本次版本更新中明确确认：**`auto-bind-coupons`、`create-order` 及之后的支付流程已测试可行**。当前文档与技能流程据此更新。

验证来源为开发者补充说明；本次发布的离线检查结果见 [GitHub 发布记录](https://github.com/ryb792/mcbudget/blob/main/docs/RELEASE_VALIDATION.md)。此前各版本的检查记录按当时情况保留，后续复测或字段变化可更新本节及 [工具参考](references/mcp_tools.md)。
