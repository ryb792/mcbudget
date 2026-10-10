# 开发与验证

[返回首页](../README.md) · [MCP 接入](../MCP_INTEGRATION.md) · [发布验证记录](RELEASE_VALIDATION.md)

## 本地检查

在仓库根目录执行：

```bash
python scripts/run_tests.py
python scripts/test_engine_parity.py
python scripts/build_demo.py
node scripts/verify_demo.js --browser <已有浏览器的可执行文件>
python scripts/package_skill.py
```

浏览器检查需要已有 `playwright-core` 和 Chromium/Chrome，可通过 `NODE_PATH` 指向已有依赖。打包采用公开资源白名单，排除个人配置和本地订单快照。

## 仓库结构


```
mcbudget/
├── SKILL.md                  # 技能主文件：流程与硬约束
├── scripts/
│   ├── budget_engine.py      # 确定性引擎：金额/候选/阶梯/解释 + MCP 数据适配器（纯标准库）
│   ├── check_mcp.py          # 首次使用连接检查与安装/绑定引导（只读，Token 不回显）
│   ├── engine.js             # 同一算法的 JS 实现（演示页内嵌）
│   ├── run_tests.py          # 93 项引擎与连接检查回归测试
│   ├── test_engine_parity.py # Python/JS 引擎一致性测试
│   ├── real_smoke.py         # 真实 MCP 到店/得来速只读冒烟（门店/菜单/算价）
│   ├── verify_demo.js        # 演示页浏览器交互验收（Playwright + 系统 Chrome）
│   ├── make_qr.py            # 支付链接本地二维码（可选依赖 qrcode+pillow）
│   └── build_demo.py         # 从模板构建自包含演示页
├── references/
│   ├── mcp_tools.md          # MCP 工具参数表 + 金额单位陷阱
│   └── data_conventions.md   # 演示/真实共享的数据契约
├── assets/
│   ├── sample_data.json      # 演示样例数据（明确标注虚构）
│   └── demo_template.html    # 演示页模板
├── demo/index.html           # 自包含演示页（双击打开）
├── MCP_INTEGRATION.md        # MCP 工具、数据流、验证状态
├── CONTEST_DECLARATION.md    # 参赛声明（官方原文，未改动）
├── mcp-config.example.json   # MCP 配置示例（仅环境变量占位符）
├── mcp-config.codex.example.toml # Codex 配置示例（环境变量引用）
├── workbuddy.md              # WorkBuddy 开发过程记录
└── LICENSE                   # MIT（原创代码）
```

## 已验证能力

**已验证（本地自动化测试）**：

- 金额单位转换（菜单/订单元字符串 ↔ 算价整数分）、报价恒等式校验（防重复扣减）；
- 预算阶梯边界：恰好等于预算、超一分钱、配送费导致超预算（报告差额而非编造）；
- 券使方案跨入预算档位、券失效回退、同一券不重复扣减（样例规则与真实模式"以算价为准"同一口径）；
- 候选 ≤30、真实报价 ≤12、购物车签名去重、低预算无方案、高档沿用、排除项/必选项生效；
- 未核价/核价失败方案不冒充已核价；同输入同数据结果完全一致（确定性）；
- 连接检查五状态判定（not_configured/placeholder/configured/verified/invalid）与引导输出、Token 不回显；
- 套餐优先/性价比排序（偏好主餐口径、同族词扩展、覆盖度计件）、25/30/35 元真实菜单行为符合"加 5 元吃套餐"语义；
- Python 与 JS 引擎 4 组用例输出字节级一致；演示页从解压技能包可运行。

