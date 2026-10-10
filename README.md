# 麦麦预算挑战 McBudget

**给定预算，看看今天怎么吃。** 用户用一句话描述预算与口味，McBudget 生成 B-5 / B / B+5 三档预算阶梯方案：每档吃什么（含套餐组成）、用当前优惠后实付多少、加 5 元或减 5 元的具体变化，并可一键导出 PNG 挑战卡；连接麦当劳 MCP 后还能完成领券、算价与真实下单。

- 目标用户：普通办公用户，以及 WorkBuddy、Codex 等 AI 工具用户。
- 形态：通用 Agent Skill（`SKILL.md` + `scripts/` + `references/` + `assets/` + `demo/`），适用于支持本地 Skill、MCP 和脚本执行的客户端；参赛仓库与技能包同构。
- V1 范围：单人到店取餐与普通外送；预算是应付总额上限（外送计入配送费）；支持必选餐品、口味偏好、排除项；不做健康评估。

## 获取技能

- 项目：https://github.com/ryb792/mcbudget
- 技能包：https://github.com/ryb792/mcbudget/releases/download/v0.2.1/mcbudget.zip
- 发布检查：[docs/RELEASE_VALIDATION.md](docs/RELEASE_VALIDATION.md)

## 30 秒上手（演示，无需任何配置）

双击打开 **`demo/index.html`**——零外网依赖、零配置：

1. 拖动预算滑块到 **25 元**，点"想吃：鸡肉"，看三档方案怎么变；
2. 切到 **B+5**（30 元档），页面直接解释"多花 5 元买到了什么"；
3. 点 **"生成挑战卡（PNG）"**，保存你的麦麦预算挑战卡。

> 页面永久标记"演示样例价格"：餐品参考常见品类，价格与优惠规则为固定虚构样例，不发起任何真实领券、下单或支付。

## 在 WorkBuddy、Codex 等工具中使用

### 第 0 步 · 首次使用检查（没有 MCP/Token 也能用）

不想配置？直接跳到下方"30 秒上手"用演示页。想真实点餐？在对话里直接发起预算挑战，技能会自动检测连接状态并给出引导；也可以手动运行检查：

```bash
python scripts/check_mcp.py          # 检查本机配置状态与引导（不发网络请求）
python scripts/check_mcp.py --probe  # 额外直连验证 Token 有效性（一次 now-time-info）
```

状态与处理：`not_configured`（未配置）/ `placeholder`（Token 仍是占位符）→ 按脚本输出的 guide 步骤申请并配置；`configured` → 已发现本地凭据，仍需验证连接；`verified` → 直连验证通过；`invalid` → Token 失效重新申请；`network_error` → 检查网络/代理。检查脚本永不回显 Token 内容。

脚本优先读取环境变量 `MCD_MCP_TOKEN`，也兼容 WorkBuddy 本地 JSON 配置。其他客户端可使用环境变量，或通过 `--config` 指定兼容的 JSON 配置；脚本不会自动读取 Codex 的 TOML 配置。客户端已暴露麦当劳 MCP 工具时，技能优先直接使用这些工具。

### 第 1 步 · 申请 Token 并绑定账户（一次性）

1. 手机号登录 https://open.mcd.cn （此步即完成麦当劳账户绑定）；
2. 右上角【控制台】→ 激活 → 同意服务协议 → 一键复制 MCP Token。

### 第 2 步 · 安装技能

**WorkBuddy**

打开 WorkBuddy → 左侧边栏【专家·技能·连接器】→【技能】→ 添加技能 → **上传技能** → 选择 `mcbudget.zip`（打包方式见下）→ 导入后保持启用。

**Codex**

解压 `mcbudget.zip`，把完整的 `mcbudget/` 文件夹放到用户技能目录 `~/.agents/skills/mcbudget/`，或当前项目的 `.agents/skills/mcbudget/`。目录内应直接包含 `SKILL.md`；不要只复制该文件。随后在 Codex 中输入：

```text
$mcbudget 帮我挑战 25 元午饭，到店取餐，想吃鸡肉汉堡。
```

若技能没有出现在列表中，重新打开会话或重启客户端。目录与调用方式见 [Codex 官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills)。

**其他支持 Skill 的客户端**

按客户端的技能导入方式安装同一文件夹，保持 `SKILL.md` 与资源的相对路径。真实模式还需支持 Streamable HTTP MCP 和本地 Python 脚本执行；演示页可独立打开。

技能包打包（本仓库根目录即技能包根目录）：

```bash
# 在仓库根目录执行，产出 dist/mcbudget.zip
python scripts/package_skill.py
```

### 第 3 步 · 配置 MCP 连接（真实模式）

**WorkBuddy**：进入【专家·技能·连接器】→【连接器】→【自定义连接器】→【配置 MCP】，粘贴 `mcp-config.example.json` 中的 `mcpServers` 内容，在本机把 `${MCD_MCP_TOKEN}` 替换为实际 Token 后保存，启用 `mcd-mcp`。

**Codex**：把 `mcp-config.codex.example.toml` 的配置表加入 `~/.codex/config.toml` 或项目的 `.codex/config.toml`，保留已有配置：

```toml
[mcp_servers.mcd-mcp]
url = "https://mcp.mcd.cn"
bearer_token_env_var = "MCD_MCP_TOKEN"
```

在启动 Codex 前，让其进程能读取本机环境变量 `MCD_MCP_TOKEN`，值为 Token 本体，不带 `Bearer ` 前缀。设置后重启客户端；CLI 可通过 `codex mcp list` 查看配置，在会话中通过 `/mcp` 查看连接。配置字段见 [Codex 官方 MCP 文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。

**其他 MCP 客户端**：使用服务地址 `https://mcp.mcd.cn`、Streamable HTTP 和 `Authorization: Bearer <Token>`。JSON 示例为 `mcp-config.example.json`；传输类型名称和环境变量展开方式按客户端要求调整。

Token 仅保存在本机客户端配置或环境变量中，不放入对话、Git、截图和分享卡。完成配置后，在当前客户端确认麦当劳工具可调用。

未连接 MCP 时技能自动工作在演示模式；连接后按 SKILL.md 的流程走真实点餐。

## 使用示例（真实模式）

1. "帮我挑战 25 元午饭，到店取餐，想吃鸡肉汉堡。"（用户请求或确认领券后领取并核价，套餐优先推荐）
2. "外送到我的办公室，总预算 35 元，配送费也算进去，不要咖啡。"
3. "加 5 元能升级什么？保持当前门店和取餐方式。"
4. "就选这套，重新算价后让我确认下单。"

推荐策略：**领券后重新核价**（用户请求或确认后领取），**性价比导向、套餐优先**（同偏好下预算内优先推荐套餐，套餐不可行时回落覆盖最高的单点组合），偏好按主餐口径匹配（"想吃鸡肉"可命中鸡腿堡类命名）。

支付方式：下单后默认交付**支付链接**（复制到手机，微信/浏览器打开即付，模板内置"麦当劳 App → 我的订单 → 待支付"兜底）；二维码仅在用户主动要求时本地生成。支付一律由用户完成。

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

## 许可与声明

原创代码 MIT（见 `LICENSE`）；`CONTEST_DECLARATION.md` 为官方参赛声明原文（未改动）。麦当劳及相关标识为麦当劳公司商标，本项目为大赛参赛作品，非麦当劳官方产品。餐品、价格与供应状态以麦当劳官方渠道实时结果为准。
