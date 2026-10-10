<div align="center">

# McBudget · Meal Budget Challenge

**What changes when you add ¥5 to your lunch budget?**

Turn one request into **B−5 / B / B＋5** meal plans, compare payable totals and meal changes, and export a PNG challenge card.

[![Agent Skill: WorkBuddy and Codex](https://img.shields.io/badge/Agent_Skill-WorkBuddy_%C2%B7_Codex-7057D9?style=flat-square)](docs/GETTING_STARTED.md)
[![Tests: 93 passed](https://img.shields.io/badge/Tests-93_passed-208844?style=flat-square)](docs/RELEASE_VALIDATION.md)
[![Demo: online](https://img.shields.io/badge/Demo-online-EA580C?style=flat-square)](https://ryb792.github.io/mcbudget/demo/)
[![License: MIT original code](https://img.shields.io/badge/License-MIT_(original_code)-2563EB?style=flat-square)](LICENSE)

### [▶ Try the demo](https://ryb792.github.io/mcbudget/demo/) · [↓ Download Skill](https://github.com/ryb792/mcbudget/releases/latest/download/mcbudget.zip) · [中文](README.md)

</div>

McBudget is an Agent Skill for office lunch planning. It works with **WorkBuddy, Codex, and other clients supporting local Skills, MCP, and Python execution**. Real mode connects to **McDonald's China MCP** using your own account. The current demo interface and setup guide are in Chinese.

## See it in action

<p align="center"><a href="https://ryb792.github.io/mcbudget/demo/"><img src="assets/readme/budget-ladder.png" alt="Actual McBudget demo showing ¥20, ¥25 and ¥30 budget caps, sample meal details and explanations" width="780"></a></p>

The ¥20 / ¥25 / ¥30 labels are **budget caps**, not mandatory spending. Each plan shows its payable total. If a larger budget does not yield a suitable upgrade, McBudget keeps the previous plan and explains why.

> The demo uses fixed fictional prices and simplified sample discounts, visibly labeled throughout. Real prices and availability come from the official MCP quotation.

## What you get

| Feature | Result |
| --- | --- |
| Three budget tiers | Meals and payable totals for B−5, B and B＋5 |
| Concrete change explanations | Added, removed or replaced items, plus the actual payment difference |
| Preferences | Required items, preferred foods and exclusions |
| Official quotation flow | Store/menu lookup and re-quotation through McDonald's MCP in a connected client |
| Shareable PNG | Budget, meal details and payment breakdown in one card |

## Try without setup

1. Open the [online demo](https://ryb792.github.io/mcbudget/demo/).
2. Choose a budget and food preferences; compare the three tiers.
3. Export a PNG challenge card.

For offline use, [download the ZIP](https://github.com/ryb792/mcbudget/releases/latest/download/mcbudget.zip), extract it and open `demo/index.html` locally. No account or Token is needed for the demo.

## Install the Skill

- **WorkBuddy:** import `mcbudget.zip` using the client's Skill upload entry.
- **Codex:** extract the complete `mcbudget/` folder into `~/.agents/skills/` or your project's `.agents/skills/`. Keep `SKILL.md` and all supporting resources together. Invoke it with `$mcbudget`.
- **Other clients:** use their local Skill import method, preserving the directory structure.

See the [setup guide](docs/GETTING_STARTED.md) for McDonald's MCP configuration. Real mode needs your own Token from [McDonald's China Open Platform](https://open.mcd.cn); keep it in local configuration or an environment variable.

Example request for the current Chinese workflow:

```text
$mcbudget 帮我挑战 25 元午饭，到店取餐，想吃鸡肉汉堡。
给我 B-5 / B / B+5 三档，说明吃什么、应付多少，以及加减 5 元的具体变化。
我选定后，先重新核价，再让我确认下单。
```

After you choose a plan, the assistant re-quotes the cart and asks for your order confirmation. You complete payment using the provided payment link. Delivery budgets include the delivery fee.

## Docs and feedback

- [MCP integration and verification](MCP_INTEGRATION.md)
- [Development](docs/DEVELOPMENT.md) · [Release validation](docs/RELEASE_VALIDATION.md)
- [Latest release](https://github.com/ryb792/mcbudget/releases/latest)
- [Report an issue or suggest a scenario](https://github.com/ryb792/mcbudget/issues/new)
- [Accepted contest entry](https://github.com/M-China/mcd-developer-innovation-challenge/issues/277#issuecomment-6095413505)

If McBudget helps with your lunch planning, a **Star** helps others find it. Contributions and practical meal-planning suggestions are welcome.

Original code is [MIT licensed](LICENSE). This is a contest project and an unofficial product. McDonald's trademarks belong to their respective owners. Actual products, prices and availability are determined by official channels.
