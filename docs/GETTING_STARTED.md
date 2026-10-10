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

在当前客户端确认麦当劳工具可调用。客户端已暴露麦当劳 MCP 工具时，技能直接使用这些工具。

也可以在技能目录运行本地检查：

```bash
python scripts/check_mcp.py
python scripts/check_mcp.py --probe
```

第一条检查配置状态，不发网络请求；`--probe` 额外调用一次只读 `now-time-info` 验证 Token。检查脚本不会回显 Token 内容。

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

技能按 [SKILL.md](../SKILL.md) 查询真实门店、菜单和优惠，再官方核价。你选定后再次核价、确认订单，由你通过交付的支付链接完成支付。领券仅在你请求或确认后执行；调整预算、浏览方案和生成卡片不会创建订单。

生成挑战卡时可补充“把我选定的方案生成 PNG 挑战卡”。卡片只使用本轮成功核价的结果，不含 Token、地址或支付链接。

遇到问题请[提交 Issue](https://github.com/ryb792/mcbudget/issues/new)，附上客户端名称、使用步骤和脱敏报错；不要提交 Token、手机号、地址或支付链接。
