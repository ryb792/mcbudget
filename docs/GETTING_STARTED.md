# 🚀 安装与开始真实使用

[返回项目首页](https://github.com/ryb792/mcbudget) · [下载真实 Skill](https://github.com/ryb792/mcbudget/releases/latest/download/mcbudget.zip)

McBudget Skill 使用麦当劳 MCP 的真实门店、菜单、优惠和官方核价。首次使用需安装技能并连接你自己的账户；未连接时先完成配置，技能不会用模拟数据替代真实结果。

## 第 1 步 · 安装技能

### WorkBuddy

打开 WorkBuddy →【专家·技能·连接器】→【技能】→ 添加技能 → **上传技能** → 选择 `mcbudget.zip`，导入后保持启用。

### Codex

解压 `mcbudget.zip`，把完整的 `mcbudget/` 文件夹放到用户技能目录 `~/.agents/skills/mcbudget/`，或当前项目的 `.agents/skills/mcbudget/`。目录内应直接包含 `SKILL.md`；不要只复制该文件。

若技能没有出现在列表中，重新打开会话或重启客户端。目录与调用方式见 [Codex 官方 Skill 文档](https://learn.chatgpt.com/docs/build-skills)。

### 其他支持 Skill 的客户端

按客户端的技能导入方式安装同一文件夹，保持 `SKILL.md` 与资源的相对路径。客户端需支持 Streamable HTTP MCP 和本地 Python 脚本执行。

## 第 2 步 · 申请 Token 并绑定账户

1. 手机号登录 [麦当劳开放平台](https://open.mcd.cn)，绑定你的麦当劳账户。
2. 进入【控制台】，按页面指引激活 MCP 并复制自己的 Token。

## 第 3 步 · 配置 MCP 连接

### WorkBuddy

进入【专家·技能·连接器】→【连接器】→【自定义连接器】→【配置 MCP】，粘贴 `mcp-config.example.json` 中的 `mcpServers` 内容，在本机把 `${MCD_MCP_TOKEN}` 替换为实际 Token 后保存，启用 `mcd-mcp`。

### Codex

把 `mcp-config.codex.example.toml` 的配置表加入 `~/.codex/config.toml` 或项目的 `.codex/config.toml`，保留已有配置：

```toml
[mcp_servers.mcd-mcp]
url = "https://mcp.mcd.cn"
bearer_token_env_var = "MCD_MCP_TOKEN"
```

在启动 Codex 前，让其进程能读取本机环境变量 `MCD_MCP_TOKEN`，值为 Token 本体，不带 `Bearer ` 前缀。设置后重启客户端；CLI 可通过 `codex mcp list` 查看配置，在会话中通过 `/mcp` 查看连接。配置字段见 [Codex 官方 MCP 文档](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。

### 其他 MCP 客户端

使用服务地址 `https://mcp.mcd.cn`、Streamable HTTP 和 `Authorization: Bearer <Token>`。JSON 示例为 `mcp-config.example.json`；传输类型名称和环境变量展开方式按客户端要求调整。

Token 仅保存在本机客户端配置或环境变量中，不放入对话、Git、截图和分享卡。

## 第 4 步 · 验证连接

在当前客户端确认麦当劳工具可调用。客户端已暴露麦当劳 MCP 工具时，技能直接使用这些工具；同一会话中无需每次重复发现工具、检查配置或探测连接。连接失败、认证失效或配置变化时再检查。

也可以在技能目录运行本地检查：

```bash
python scripts/check_mcp.py
python scripts/check_mcp.py --probe
```

第一条检查配置状态，不发网络请求；`--probe` 额外调用一次只读 `now-time-info` 验证 Token。检查脚本不会回显 Token 内容。

连接检查用于首次配置或排查故障；日常预算挑战不运行 `real_smoke.py`、开发测试或打包检查。

| 状态 | 处理 |
| --- | --- |
| `not_configured` / `placeholder` | 申请 Token 并配置连接 |
| `configured` | 已发现本地凭据，继续验证连接 |
| `verified` | 直连验证通过，可以开始挑战 |
| `invalid` | 更新无效或失效的 Token |
| `network_error` | 检查网络或代理后重试 |

脚本优先读取环境变量 `MCD_MCP_TOKEN`，兼容 WorkBuddy 本地 JSON 配置。其他客户端可使用环境变量，或通过 `--config` 指定兼容的 JSON；脚本不会自动读取 Codex 的 TOML 配置。脚本未找到凭据不等同于客户端原生 MCP 未连接，先检查当前会话实际暴露的工具。

## 💬 开始第一次预算挑战

```text
帮我挑战 25 元午饭，到店取餐，想吃鸡肉汉堡。
给我 B-5 / B / B+5 三档，说明餐品、官方应付金额和加减 5 元的变化。
选定后先重新核价，再让我确认下单。
```

在 Codex 中可加 `$mcbudget` 调用。外送时可以说：“总预算 35 元，配送费也算进去，不要咖啡。”

技能按 [SKILL.md](../SKILL.md) 查询真实门店、菜单和优惠，再官方核价。你选定后再次核价、确认订单，由你通过交付的支付链接完成支付。领券按你的请求或已开启的自动领免费券偏好执行；调整预算、浏览方案和生成卡片不会创建订单。

订单创建成功后，只交付餐品与数量、应付金额、门店与取餐方式或简短收餐地址、支付链接。异常或订单发生变化时补充相关提示。

## 💰 使用省钱模式

```text
开启省钱模式，自动领取免费券，按我选的门店核价。
比较我的积分能换哪些适合这顿饭的餐券；兑换前让我确认商品、积分和数量。
```

开启后，同一会话最多领取一次免费券，再刷新当前门店的可用券。你想使用积分时，技能先只读查询余额、商城兑换商品与详情，比较积分消耗、使用条件和餐品适用性；确认具体商品、积分与数量后才兑换。兑换成功后核实实际发券及门店适用性，再重新核价。现金应付取官方算价，积分单独展示；不会默认购买付费卡或抽奖。

流程依据[官方 MCP 工具列表](https://github.com/M-China/mcd-mcp-server#3-工具列表)；客户端操作约定见[省钱流程](../references/savings.md)。

## ⚡ 减少等待

- **默认快速推荐**：先核价最多 6 个候选，覆盖三个预算档附近的组合与较低估算候选。想比较更多时说“多比较一些方案”，最多扩展到 12 个；三档结果共享同一批成功报价。
- **沿用当前选择**：同一会话中可继续使用已选门店、方式和口味。可以说“预算改到 30 元，沿用刚才的门店和口味”。
- **只改预算，先本地重排**：优先使用 5 分钟内、完整购物车和业务上下文一致的已核价结果，缺少候选再补充核价。门店、方式、时段、地址、餐品选项或券状态变化时重新查询相关数据。
- **按需输出**：普通推荐先给餐单和金额；需要分享再说“生成 PNG 挑战卡”，需要支付二维码再提出。
- **按需省钱**：自动领免费券在已授权会话中最多一次；积分余额和兑换详情仅在你要求使用积分或已开启相关偏好时查询，不在普通推荐中遍历商城。

首次使用通常要完成门店、菜单和详情查询。默认核价候选上限从 12 个降到 6 个，减少官方请求和客户端逐次处理；实际耗时仍取决于官方服务与网络响应。任何展示报价都不能代替下单前的重新核价与确认。

生成挑战卡时可补充“把我选定的方案生成 PNG 挑战卡”。卡片只使用本轮成功核价的结果，不含 Token、地址或支付链接。

遇到问题请[提交 Issue](https://github.com/ryb792/mcbudget/issues/new)，附上客户端名称、使用步骤和脱敏报错；不要提交 Token、手机号、地址或支付链接。
