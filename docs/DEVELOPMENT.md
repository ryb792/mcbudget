# 🛠️ 开发与验证

[返回首页](../README.md) · [MCP 接入](../MCP_INTEGRATION.md) · [发布验证记录](RELEASE_VALIDATION.md)

仓库包含真实 Skill 与独立的 GitHub 网页演示。发布的 `mcbudget.zip` 只保留真实 MCP 流程及其必要资源；演示网页、固定样例数据和测试文件不进入安装包。

## 本地检查与打包

在仓库根目录执行：

```bash
python scripts/run_tests.py
python scripts/test_engine_parity.py
python scripts/build_demo.py
node scripts/verify_demo.js --browser <已有浏览器的可执行文件>
python scripts/package_skill.py
```

浏览器检查需要已有 `playwright-core` 和 Chromium/Chrome，可通过 `NODE_PATH` 指向已有依赖。打包产物为 `dist/mcbudget.zip`，通过真实资源白名单排除演示、测试、个人配置和订单快照。

## 真实 Skill

真实引擎将规划、报价与本地选餐分开：

1. `plan_quotes(ctx)` 输出核价短名单；默认 6 个候选，`quote_limit=12` 扩展到最多 12 个，候选总数最多 30。
2. 客户端只为短名单补齐真实详情，构建完整购物车，调用官方 `calculate-price` 并适配报价。
3. `select_priced_ladder(ctx, quotes_by_sig)` 校验报价并在本地生成三档餐单，不发远程请求。改预算时优先复用有效同上下文报价，再补充不足候选。

`build_ladder(ctx, quote_fn=...)` 保留直接回调接入。引擎不自行连接 MCP，不以菜单估算替代核价；规划阶段也不提供可下单金额。客户端负责完整业务上下文、5 分钟内的会话展示缓存与下单前重新核价，详细契约见 [数据约定](../references/data_conventions.md)。

真实卡片使用 `scripts/render_card.py` 与 `assets/result_template.html`。用户需要时才生成；只接受成功核价的所选方案及实际核价时间，生成本地 HTML 后通过浏览器导出 PNG。卡片不需要 Token，也不调用 MCP。

省钱模式按需读取 [references/savings.md](../references/savings.md)：用户已授权的免费券在每个会话最多领取一次；积分先只读查询和比较，确认具体商品、积分和数量后才兑换。新券必须核实门店适用性、刷新报价缓存并重新官方核价。官方能力依据 [麦当劳 MCP 工具列表](https://github.com/M-China/mcd-mcp-server#3-工具列表)；现有真实写操作确认不包含商城积分兑换。

食品订单创建成功后，内部核对完整返回，用户交付只保留餐品与数量、应付金额、门店和取餐方式或简短收餐地址、支付链接。额外字段仅在需要取餐、处理变化或异常时展示。

`scripts/real_smoke.py` 仅做真实门店、菜单、官方算价的只读检查，不领券、不创建订单。它与测试、打包脚本用于开发或排障，不在每次预算挑战中运行。当前真实流程验证来源见 [MCP 接入第 6 节](../MCP_INTEGRATION.md#6-真实验证记录)。

## GitHub 网页演示

网页演示独立保留于仓库和 [GitHub Pages](https://ryb792.github.io/mcbudget/demo/)，不随 Skill 发布。获取完整仓库源码后可双击 `demo/index.html` 查看。

- `assets/sample_data.json` 提供固定虚构菜单和简化优惠规则。
- `scripts/demo_engine.py` 是仓库开发专用的 Python 演示入口。
- `scripts/engine.js` 与 `assets/demo_template.html` 用于生成自包含的网页。
- `scripts/test_engine_parity.py` 检查 Python/JavaScript 演示输出一致性。
- 演示价格永久标记“演示样例价格”，网页不连接餐饮 MCP、不产生真实账户状态变化。
- 原始支付链接、地址、手机号和订单数据不用于截图或分享素材。

演示规则仅帮助理解展示方式。真实引擎仅接受官方核价回调，两个入口不能相互替代。

## 仓库结构

```text
mcbudget/
├── SKILL.md                       # 真实 Skill 主流程与约束
├── scripts/
│   ├── budget_engine.py           # 核价短名单、真实报价校验与本地预算阶梯
│   ├── check_mcp.py               # 配置检查与只读连接探测
│   ├── real_smoke.py              # 真实到店/得来速只读端到端检查
│   ├── render_card.py             # 已核价真实结果的本地卡片
│   ├── make_qr.py                 # 用户主动要求时本地生成支付二维码
│   ├── package_skill.py           # 真实 Skill 资源白名单打包
│   ├── run_tests.py               # 108 项回归；仅仓库保留
│   ├── demo_engine.py             # 仓库专用演示适配层
│   ├── engine.js                  # 网页演示引擎
│   ├── test_engine_parity.py       # 4 组演示一致性检查
│   ├── verify_demo.js             # 浏览器交互验收
│   └── build_demo.py              # 构建网页
├── references/
│   ├── mcp_tools.md               # 真实工具与字段参考
│   ├── data_conventions.md        # 真实数据契约
│   └── savings.md                 # 免费券、积分餐券比较与兑换流程
├── assets/
│   ├── result_template.html       # 真实卡片模板；随 Skill 提供
│   ├── sample_data.json           # 虚构数据；仅 GitHub 保留
│   ├── demo_template.html         # 网页模板；仅 GitHub 保留
│   └── readme/                    # 首页截图与分享素材
├── demo/index.html                # 独立网页演示；仅 GitHub 保留
├── docs/GETTING_STARTED.md         # 真实安装与连接指引；随 Skill 提供
├── MCP_INTEGRATION.md              # 真实工具流与验证来源
├── CONTEST_DECLARATION.md          # 官方参赛声明
├── mcp-config.example.json         # JSON 配置占位符
├── mcp-config.codex.example.toml   # Codex 环境变量引用
├── workbuddy.md                   # 原开发过程摘要；仅 GitHub 保留
└── LICENSE                        # 原创代码 MIT
```

## 验证范围

本地回归覆盖金额单位与恒等式、预算边界、候选与报价数量上限、核价失败、确定性排序、套餐与口味、连接错误处理及真实引擎拒绝非官方报价路径。离线测试使用隔离凭据的测试数据，不调用真实餐饮写操作。

性能检查分别记录候选规划和本地筛选耗时、默认及扩展报价回调次数，不把本地模拟回调时间当作真实 MCP 网络耗时。默认上限从 12 次变为 6 次，只能说明报价调用上限减半；总体等待还包含菜单、详情、优惠查询及客户端处理。

108 项原回归、65 项性能与选餐策略回归（合计 173 项 Python 检查）与 4 组演示一致性检查已通过。性能检查入口为 `python scripts/test_performance.py`。历史版本与本次发布的其他验收分别记录在 [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md)，真实订单流程的开发者补充确认记录在 MCP 接入说明中。
