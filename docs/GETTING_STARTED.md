# 安装与开始使用

[返回项目首页](../README.md) · [在线演示](https://ryb792.github.io/mcbudget/demo/) · [下载技能包](https://github.com/ryb792/mcbudget/releases/latest/download/mcbudget.zip)

先用演示页体验预算阶梯和 PNG 挑战卡。演示使用固定虚构价格，无需账户或 Token。真实模式需要自己的麦当劳账户与 MCP 连接。


### 第 0 步 · 首次使用检查（没有 MCP/Token 也能用）

不想配置？打开[在线演示](https://ryb792.github.io/mcbudget/demo/)或下载后打开 `demo/index.html`。想真实点餐？在对话里直接发起预算挑战，技能会自动检测连接状态并给出引导；也可以手动运行检查：

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

打开 WorkBuddy → 左侧边栏【专家·技能·连接器】→【技能】→ 添加技能 → **上传技能** → 选择 `mcbudget.zip`→ 导入后保持启用。

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

未连接 MCP 时使用演示模式；连接后按 [SKILL.md](../SKILL.md) 的流程走真实点餐。

## 试着这样说

```text
帮我挑战 25 元午饭，到店取餐，想吃鸡肉汉堡。
给我 B-5 / B / B+5 三档，说明餐品、优惠后应付金额和加减 5 元的变化。
选定后先重新核价，再让我确认下单。
```

外送时可以说“总预算 35 元，配送费也算进去，不要咖啡”。支付由用户通过支付链接完成。

遇到问题请[提交 Issue](https://github.com/ryb792/mcbudget/issues/new)，附上客户端名称、使用步骤和脱敏报错；不要提交 Token、手机号、地址或支付链接。
