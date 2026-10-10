<div align="center">

# 麦麦预算挑战 · McBudget

**今天午饭 25 元，加 5 元能升级什么？**

把一句话变成 **B−5 / B / B＋5** 三档餐单，看清应付金额、餐品变化，生成可分享的预算挑战卡。

[![Agent Skill: WorkBuddy and Codex](https://img.shields.io/badge/Agent_Skill-WorkBuddy_%C2%B7_Codex-7057D9?style=flat-square)](docs/GETTING_STARTED.md)
[![MCD MCP: read-only verified](https://img.shields.io/badge/MCD_MCP-read--only_verified-208844?style=flat-square)](MCP_INTEGRATION.md#6-真实验证状态如实声明)
[![Tests: 93 passed](https://img.shields.io/badge/Tests-93_passed-208844?style=flat-square)](docs/RELEASE_VALIDATION.md)
[![Demo: online](https://img.shields.io/badge/Demo-online-EA580C?style=flat-square)](https://ryb792.github.io/mcbudget/demo/)
[![Release: v0.2.2](https://img.shields.io/badge/Release-v0.2.2-2563EB?style=flat-square)](https://github.com/ryb792/mcbudget/releases/latest)
[![License: MIT original code](https://img.shields.io/badge/License-MIT_(original_code)-2563EB?style=flat-square)](LICENSE)
[![Contest: accepted](https://img.shields.io/badge/Contest-accepted-7057D9?style=flat-square)](https://github.com/M-China/mcd-developer-innovation-challenge/issues/277#issuecomment-6095413505)

### [▶ 在线试玩](https://ryb792.github.io/mcbudget/demo/)　·　[↓ 下载 Skill](https://github.com/ryb792/mcbudget/releases/latest/download/mcbudget.zip)　·　[安装指引](docs/GETTING_STARTED.md)

[English](README.en.md) · [反馈问题](https://github.com/ryb792/mcbudget/issues/new) · [参赛作品](https://github.com/M-China/mcd-developer-innovation-challenge/issues/277)

</div>

## 先看一次 25 元挑战

下面是演示页实际生成的预算阶梯：**20 / 25 / 30 元是预算上限，卡片显示的是应付金额**。展开餐单可看套餐组成、优惠和剩余预算；高一档沿用当前方案时，也会说明原因。

<p align="center">
  <a href="https://ryb792.github.io/mcbudget/demo/"><img src="assets/readme/budget-ladder.png" alt="McBudget 实际演示：20、25、30 元三档预算、餐品明细与变化解释，价格为虚构样例" width="780"></a>
</p>

> 演示页使用固定虚构价格和简化优惠规则，始终标记“演示样例价格”。真实门店、餐品与优惠以麦当劳官方核价结果为准。

## 你可以用它做什么

| 想解决的事 | McBudget 给你的结果 |
| --- | --- |
| 午饭有预算，但不知道怎么搭配 | B−5 / B / B＋5 三档餐单与应付金额 |
| 想知道加 5 元值不值 | 列出增加、减少或替换的餐品，以及实际付款差额 |
| 想吃鸡肉，不要咖啡 | 根据偏好、必选餐品和排除项生成候选 |
| 需要真实点餐 | 在已连接的客户端中使用麦当劳 MCP，查询门店与菜单、处理优惠并重新核价 |
| 想分享今天的预算挑战 | 导出 PNG 卡片，展示预算、餐单和金额明细 |

适合有午饭预算的办公用户，也适合在 **WorkBuddy、Codex 等支持 Skill、MCP 和脚本执行的工具**中使用。默认面向单人点餐，外送预算包含配送费。

## 30 秒试玩

1. 打开 **[在线演示](https://ryb792.github.io/mcbudget/demo/)**，把预算设为 **25 元**。
2. 选择“想吃：鸡肉”，查看三档餐单和加减预算的变化。
3. 点“生成挑战卡（PNG）”，保存并分享。

也可以[下载技能包](https://github.com/ryb792/mcbudget/releases/latest/download/mcbudget.zip)，解压后双击 `demo/index.html`，离线体验同一演示。

<details>
<summary>查看生成的挑战卡</summary>

<p align="center"><img src="assets/readme/challenge-card.png" alt="McBudget PNG 挑战卡：预算 25 元、样例应付 22.5 元、套餐和优惠明细" width="375"></p>

</details>

## 在 AI 工具中使用

先下载 **[mcbudget.zip](https://github.com/ryb792/mcbudget/releases/latest/download/mcbudget.zip)**，再按你使用的工具安装：

| 工具 | 安装入口 | 详细步骤 |
| --- | --- | --- |
| WorkBuddy | 技能 → 添加技能 → 上传技能包 | [WorkBuddy 安装](docs/GETTING_STARTED.md#第-2-步--安装技能) |
| Codex | 把完整 `mcbudget/` 放到 `~/.agents/skills/` 或项目 `.agents/skills/` | [Codex 安装与 MCP 配置](docs/GETTING_STARTED.md) |
| 其他客户端 | 使用客户端的本地 Skill 导入方式，保留完整目录 | [通用接入](docs/GETTING_STARTED.md) |

真实模式：在 [麦当劳开放平台](https://open.mcd.cn) 申请自己的 MCP Token，按[配置指引](docs/GETTING_STARTED.md#第-3-步--配置-mcp-连接真实模式)连接服务。Token 保存在本机。

安装后直接说：

```text
帮我挑战 25 元午饭，到店取餐，想吃鸡肉汉堡。
给我 B-5 / B / B+5 三档，说明吃什么、应付多少，以及加减 5 元的具体变化。
我选定后，先重新核价，再让我确认下单。
```

在 Codex 中可加 `$mcbudget` 调用技能。外送时可以说：“外送到我的办公室，总预算 35 元，配送费也算进去，不要咖啡。”

## 常见问题

**需要登录才能试玩吗？** 演示无需登录或 Token；真实模式使用你自己的麦当劳账户与 MCP 连接。

**加 5 元一定会多买东西吗？** 预算上限增加不等于实际多付 5 元。没有符合条件的升级时，会沿用当前方案并解释原因。

**什么时候下单和支付？** 选定方案后重新核价，展示订单信息并由你确认；支付通过交付的支付链接由你完成。

## 文档与参与

| 入口 | 内容 |
| --- | --- |
| [安装与配置](docs/GETTING_STARTED.md) | WorkBuddy、Codex 与通用客户端开始使用 |
| [技能流程](SKILL.md) · [MCP 接入](MCP_INTEGRATION.md) | 真实模式流程、数据契约与验证记录 |
| [开发与验证](docs/DEVELOPMENT.md) · [发布检查](docs/RELEASE_VALIDATION.md) | 本地运行、检查与打包 |
| [最新版本](https://github.com/ryb792/mcbudget/releases/latest) | 技能包与更新记录 |
| [反馈或提建议](https://github.com/ryb792/mcbudget/issues/new) | 使用问题、新的预算挑战场景 |
| [参赛声明](CONTEST_DECLARATION.md) · [WorkBuddy 开发记录](workbuddy.md) | 官方声明与开发过程 |

如果它帮你解决了午饭预算问题，欢迎 **Star**，也欢迎在 Issue 中分享你希望支持的点餐场景。

原创代码使用 [MIT 许可](LICENSE)。本项目为麦当劳程序员创意开发大赛参赛作品，非麦当劳官方产品；相关商标归其权利人所有。餐品、价格与供应状态以官方渠道实时结果为准。
