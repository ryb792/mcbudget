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

真实引擎通过 `build_ladder(ctx, quote_fn=...)` 接收当前官方核价回调。它不自行连接 MCP，不以菜单估算替代核价，也不支持无报价回调的计算入口。客户端完成真实工具调用与完整购物车构建，详细契约见 [数据约定](../references/data_conventions.md)。

真实卡片使用 `scripts/render_card.py` 与 `assets/result_template.html`。只接受成功核价的所选方案及核价时间，生成本地 HTML 后通过浏览器导出 PNG；卡片不需要 Token，也不调用 MCP。

`scripts/real_smoke.py` 仅做真实门店、菜单、官方算价的只读检查，不领券、不创建订单。当前真实流程验证来源见 [MCP 接入第 6 节](../MCP_INTEGRATION.md#6-真实验证记录)。

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
│   ├── budget_engine.py           # 真实候选、官方报价与预算阶梯
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
│   └── data_conventions.md        # 真实数据契约
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

108 项回归与 4 组演示一致性检查已通过。历史版本与本次发布的其他验收分别记录在 [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md)，真实订单流程的开发者补充确认记录在 MCP 接入说明中。
