# 麦当劳 MCP 工具参考（McBudget 用到的部分）

来源：官方接入说明 https://github.com/M-China/mcd-mcp-server 与参数文档 https://open.mcd.cn/mcp/doc（2026-10 提取）。**以连接后实际返回的 schema 为准**——工具可能带客户端前缀（如 `mcp__mcd-mcp__query-meals`），调用前先发现实际工具名与参数。

## 接入

- 地址 `https://mcp.mcd.cn`，协议 Streamable HTTP，请求头 `Authorization: Bearer <MCP Token>`。
- Token 在 open.mcd.cn 控制台申请；限流 600 次/分钟，超限返回 429。
- 401 = Token 无效/过期/未提供；429 = 限流。
- WorkBuddy、Codex 等客户端的安装和配置见 `../docs/GETTING_STARTED.md`；JSON 客户端参考 `../mcp-config.example.json`，Codex 参考 `../mcp-config.codex.example.toml`。工具名前缀与配置格式以当前客户端为准。

## 金额单位陷阱（最重要）

| 工具 | 字段 | 单位 | 示例 |
|------|------|------|------|
| query-meals | `meals.{code}.currentPrice` / `originalPrice` | **元字符串** | `"55.5"` |
| query-meal-detail | `data.price` | **元字符串** | `"26"` |
| calculate-price | `productPrice` / `deliveryPrice` / `discount` / `price` / `productList[].subtotal` / `tablewarePrice` | **整数分** | `1600` = 16 元 |
| create-order / query-order | `totalAmount` / `realTotalAmount` / `productPrice` / `deliveryPrice` / `totalDiscountAmount` | **元字符串** | `"22"` |

规则：内部一律整数分；`budget_engine.to_cents(value, source)` 按 `source` 显式声明来源单位（`menu_yuan` / `quote_cents` / `order_yuan` / `user_yuan`），禁止按数值大小猜单位；`adapt_quote` 校验 `price == productPrice - discount + deliveryPrice + packingPrice`（缺省费用按 0），不自洽即报错，不能重复扣减优惠。Skill 只使用当前真实工具返回；未连接时先配置，不用替代报价继续。

## McBudget 使用路径上的工具

### query-nearby-stores（到店）
入参：`searchType`（1 收藏/2 位置/3 经纬度，默认 1）、`beType`（**1 到店取餐 / 5 得来速**）、`city`+`keyword`（searchType=2 必填）或 `longitude`+`latitude`（searchType=3 必填）。
返回 `data[]`：`storeCode`、`beCode`、`storeName`、`address`、`distance`、`businessStatus/StartTime/EndTime`、`reservationTimeOptions[]`（预约时段，预约场景必用）。

### delivery-query-addresses（外送地址）
无入参。返回 `data.addresses[]`：`addressId`、`contactName`、`phone`（脱敏）、`fullAddress`。外送优先用已有地址。

### delivery-query-stores（外送门店）
入参：`addressId`（必填）、`beType`（**2 麦乐送 / 6 企业团餐**）。返回门店列表，字段同上（含 `storeCode`/`beCode`）。

### query-meals（菜单）
入参：`storeCode`、`beCode`、`orderType`（1 到店 / 2 外送）、`beType`、`reservationDate`（预约场景必填，yyyy-MM-dd HH:mm）。
返回 `data.frequent[]`（常点 code）；`data.categories[]`（分类 → `meals[]`：`code`/`tags[]`，含 daypart）；`data.meals{code}`：`name`、`currentPrice`（元）、`originalPrice`（元，促销划线价）、`discountType`（null/"促销优惠"/"麦金卡优惠"等）、`isCanWithOrder`+`withOrder`（随单购麦金卡/早餐卡；选择随单购时必须把 `withOrder` 原样带入算价与下单）。

### query-meal-detail（套餐详情）
入参：`code`、`storeCode`、`beCode`、`orderType`、`beType`、`reservationDate`。
返回 `data`：`price`（元）、`rounds[]`（套餐轮次）、`modification.items[]`（特制选项，minValues/maxValues/values[] 含 code/selectedKey）、`supportModify`。
V1 原则：**优先完整默认套餐**，不猜测套餐子项或特制选项；仅用户明确要求换子项/特制时按返回的 `rounds`/`modification` 结构构建。

### query-store-coupons（门店可用券）
入参：`storeCode`、`beCode`、`orderType`、`beType`、`reservationDate`（预约必填）。
返回 `data[]`：`title`、`couponId`、`couponCode`、`tradeDateTime`（有效期区间）、`products[]`（适用 `productCode`/`productName`）。券能否使用由当前门店和算价结果校验，**不根据券标题推算折扣**。

### available-coupons / auto-bind-coupons / query-my-coupons（麦麦省领券）
三者均无入参。`auto-bind-coupons` 自动领取全部可领券，改变账户券状态，只在用户请求或确认后调用。返回可能为 markdown 文本，按当前返回提取 `couponId`/`couponCode`。领券后必须重新 `query-store-coupons` + `calculate-price`。开发者已补充确认领券、创建订单与后续支付流程测试可行，验证来源见 `../MCP_INTEGRATION.md` 第 6 节。

### calculate-price（算价）
入参：`storeCode`、`beCode`、`orderType`、`beType`、`reservationDate`（预约）、`gmServiceCode`（团餐）、`withOrder`（随单购，来自菜单返回）、`needTableware`（餐具费）、`items[]`。

`items[]`：`productCode`（必填）、`quantity`（必填）、`couponId`+`couponCode`（用券时）、`modification`（单品特调：`values[]{code,quantity,key}`）、`roundList[]`（套餐子项：`round` + `comboItemList[]{code,quantity,modification}`）。

返回 `data`（整数分）：`productOriginalPrice`、`productPrice`（商品金额）、`deliveryOriginalPrice`、`deliveryPrice`（配送费）、`packingOriginalPrice`、`packingPrice`（**打包费**，实测存在而文档示例未列；**到店场景 deliveryPrice/packingPrice 可能整字段缺省，按 0 处理**）、`originalPrice`、`discount`（优惠）、`price`（**应付总额**）、`productList[]`（单项 `originalSubtotal`/`subtotal`）、`takeWayList[]`（**到店取餐方式选项：`code`（eat-in 堂食/locker-in 外带等）+title+subtitle，下单 takeWayCode 从这里取**）、`mealAssistanceList[]`、`enjoyed`/`enjoyable`（已享受/可享受优惠：`amountType` 1 特价 2 折扣 3 立减；`realDiscount` 单位**元**；`balance` 门槛差额单位分）、`tablewarePrice`。
实测恒等式：`price == productPrice − discount + deliveryPrice + packingPrice`（缺省字段按 0）。

### create-order（下单）
入参与算价一致，另有：`addressId`（外送必填）、`takeWayCode`（**到店必填，取自算价 takeWayList**）、`remark`（备注，≤50 字，仅外送引导填写）。
返回：`orderId`、`payId`、`payH5Url`（支付链接）、`orderDetail{orderStatus, storeName, orderProductList[]（含 comboItemList）, totalAmount, realTotalAmount, totalDiscountAmount, couponList, deliveryInfo, createTime, deliveryPrice, productPrice, takeWay, pickupCode, lockerCode, lockerQrCode, remark}`。
**超时/结果不明确 → 不自动重试**：有 orderId 则 `query-order`；无则 `order-list` 核实；不猜测、不重复创建。

### query-order / order-list
`query-order` 入参 `orderId`；`order-list` 无入参，返回最近 10 笔。金额字段为元字符串。

### now-time-info
无入参，返回当前时间。用于确定时段（早餐/正餐）与预约时间。

## 按需省钱工具

官方工具列表还包含以下能力；具体参数、分页与返回单位读取当前连接的 schema 和真实响应，商城字段不沿用餐饮订单字段猜测。完整省钱流程见 [savings.md](savings.md)。

| 工具 | 用途与执行条件 |
| --- | --- |
| `query-my-account` | 只读查询可用、累计、冻结和即将过期积分；用户询问积分或希望比较兑换优惠时使用 |
| `mall-points-products` | 查询可积分兑换或现金购买的商城商品，筛选与本餐匹配的餐品券，不默认查询所有实物 |
| `mall-product-detail` | 核实候选商品积分/现金成本、有效期及适用说明 |
| `mall-create-order` | 兑换会扣减积分或形成商城订单；确认具体商品、数量和成本后执行 |
| `mall-order-list` / `mall-order-detail` | 查商城购买/兑换结果；结果不明确时先核实，不重复兑换 |
| `campaign-calendar` | 按需查询本月活动；活动详情不代替门店可用性与官方报价 |

积分兑换券到账后重新核实门店券、构建完整券购物车并算价。`draw-lottery` 消耗积分且结果不确定，不用于默认省钱；麦金卡/早餐卡随单购买只在用户要求时比较，把购卡费用计入实际支出。

## 调用纪律

1. 菜单、券、报价、下单保持**同一 storeCode/beCode/orderType/beType/时段**上下文。
2. `addressId`、门店、餐品编码、套餐轮次、券编码全部来自真实返回，不虚构。
3. 每分钟 ≤600 请求；McBudget 自身每轮 ≤12 次 calculate-price。
4. 换门店/方式/商品/套餐/优惠 → 报价失效重算；下单前必须重新算价。
