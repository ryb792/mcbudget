<div align="center">

# 🍔 McBudget · Meal Budget Challenge

**What changes when you add ¥5 to your lunch budget?**

💰 Get **B−5 / B / B＋5** meal plans, compare official payable totals and meal changes, then choose your lunch.

[![Agent Skill: WorkBuddy and Codex](https://img.shields.io/badge/Agent_Skill-WorkBuddy_%C2%B7_Codex-7057D9?style=flat-square)](docs/GETTING_STARTED.md)
[![MCD MCP: real flow confirmed by developer](https://img.shields.io/badge/MCD_MCP-real_flow_confirmed-208844?style=flat-square)](MCP_INTEGRATION.md#6-真实验证记录)
[![Tests: 108 passed](https://img.shields.io/badge/Tests-108_passed-208844?style=flat-square)](docs/RELEASE_VALIDATION.md)
[![Web Demo: online](https://img.shields.io/badge/Web_Demo-online-EA580C?style=flat-square)](https://ryb792.github.io/mcbudget/demo/)
[![Release: v0.3.0](https://img.shields.io/badge/Release-v0.3.0-2563EB?style=flat-square)](https://github.com/ryb792/mcbudget/releases/latest)
[![License: MIT original code](https://img.shields.io/badge/License-MIT_(original_code)-2563EB?style=flat-square)](LICENSE)

### [📦 Download the real Skill](https://github.com/ryb792/mcbudget/releases/latest/download/mcbudget.zip) · [🚀 Setup guide](docs/GETTING_STARTED.md) · [▶ Web demo](https://ryb792.github.io/mcbudget/demo/)

[Features](#-what-you-get) · [Get started](#-start-in-three-steps) · [Preview](#-preview-the-experience) · [中文](README.md)

</div>

> **The installed Skill uses real MCP data.** It requires your own McDonald's China MCP connection, real stores and menus, and official quotations. If disconnected, it helps you configure the connection. The independent GitHub web demo uses visibly labeled fictional prices and is excluded from the Skill package.

McBudget is for office lunch planning in **WorkBuddy, Codex, and other clients supporting local Skills, MCP, and script execution**. The current workflow, demo interface and setup guide are in Chinese.

## 💡 What you get

| Your need | Result |
| --- | --- |
| Lunch within a budget | Meal plans and official payable totals for B−5, B and B＋5 |
| Decide whether an upgrade is worthwhile | Added, removed or replaced items, plus the actual payment difference |
| Match your preferences | Required items, preferred foods and exclusions |
| Order a selected plan | Coupon handling, re-quotation, order confirmation and payment-link handoff |
| Share your budget challenge | A PNG card with meals and payment details, without personal information |

Choose pickup, drive-through or delivery first. Delivery budgets include the delivery fee.

## 🚀 Start in three steps

1. Download [mcbudget.zip](https://github.com/ryb792/mcbudget/releases/latest/download/mcbudget.zip) and install it in your AI client.
2. Get your own Token from [McDonald's China Open Platform](https://open.mcd.cn), configure MCP and verify the connection using the [setup guide](docs/GETTING_STARTED.md).
3. Ask for a budget challenge, compare the three tiers, and confirm an order after re-quotation. You complete payment.

| Client | Install |
| --- | --- |
| **WorkBuddy** | Import the ZIP through the Skill upload entry |
| **Codex** | Extract the complete `mcbudget/` folder into `~/.agents/skills/` or the project's `.agents/skills/`; invoke with `$mcbudget` |
| **Other clients** | Use their local Skill import method and configure Streamable HTTP MCP |

### 💬 Example request

```text
$mcbudget 帮我挑战 25 元午饭，到店取餐，想吃鸡肉汉堡。
给我 B-5 / B / B+5 三档，说明吃什么、应付多少，以及加减 5 元的具体变化。
我选定后，先重新核价，再让我确认下单。
```

**Flow:** choose store and fulfillment → fetch menu and coupons → official quotation → compare tiers → confirm order → complete payment yourself.

Coupon claiming changes account state and requires your request or confirmation. The developer has additionally confirmed coupon claiming, order creation and the subsequent payment flow as working; see the [verification sources](MCP_INTEGRATION.md#6-真实验证记录).

## 👀 Preview the experience

Open the [web demo](https://ryb792.github.io/mcbudget/demo/) without an account or Token.

<p align="center"><a href="https://ryb792.github.io/mcbudget/demo/"><img src="assets/readme/budget-ladder.png" alt="McBudget web demo showing ¥20, ¥25 and ¥30 budget caps, fictional meal details and explanations" width="780"></a></p>

The ¥20 / ¥25 / ¥30 labels are **budget caps**, not mandatory spending. If a larger budget does not yield a suitable upgrade, McBudget keeps the previous plan and explains why.

> The web demo uses fixed fictional prices and simplified sample discounts. Real Skill prices, discounts and availability come from the selected store and official quotation.

For a local web preview, download the [repository source](https://github.com/ryb792/mcbudget/archive/refs/heads/main.zip) and open `demo/index.html`. The release ZIP contains the real Skill only.

## ❓ Questions

**Can the installed Skill work without MCP?**  
Configure and verify your connection first. It does not fall back to simulated meals or prices.

**When does it order or pay?**  
After you choose a plan, the assistant re-quotes the cart and asks for confirmation before creating an order. You complete payment through the provided link.

**What appears on a shared card?**  
Budget, meals, payable totals and change explanations. Tokens, phone numbers, addresses, coupon codes, full order IDs and payment links are excluded.

## 📚 Docs and feedback

- [Setup guide](docs/GETTING_STARTED.md) · [Skill workflow](SKILL.md)
- [MCP integration and verification](MCP_INTEGRATION.md)
- [Development](docs/DEVELOPMENT.md) · [Release validation](docs/RELEASE_VALIDATION.md)
- [Latest release](https://github.com/ryb792/mcbudget/releases/latest)
- [Report an issue or suggest a scenario](https://github.com/ryb792/mcbudget/issues/new)
- [Accepted contest entry](https://github.com/M-China/mcd-developer-innovation-challenge/issues/277#issuecomment-6095413505)

If McBudget helps with your lunch planning, a **⭐ Star** helps others find it. Contributions and practical meal-planning suggestions are welcome.

Original code is [MIT licensed](LICENSE). This is a contest project and an unofficial product. McDonald's trademarks belong to their respective owners. Actual products, prices and availability are determined by official channels.
