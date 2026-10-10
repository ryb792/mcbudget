#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""McBudget 真实 MCP 连接检查（首次使用引导，只读、零依赖）。

检测本机麦当劳 MCP 凭据状态，为 WorkBuddy、Codex 等客户端给出安装/绑定引导：
  not_configured        未找到 mcd-mcp 配置 → 引导申请 Token + 配置连接器
  placeholder           配置存在但 Token 仍是占位符 → 引导替换 Token
  configured            配置与 Token 就绪（未验证有效性）
  verified              配置就绪且直连验证通过（--probe）
  invalid               直连返回 401/认证失败 → Token 无效或过期，引导重新申请
  network_error         网络不可达 → 检查网络/代理

检测位置（按序）：
  1. 环境变量 MCD_MCP_TOKEN（跨客户端首选）
  2. --config 指定的 MCP JSON，或兼容回退 ~/.workbuddy/mcp.json
     JSON 凭据字段为 mcpServers.mcd-mcp.headers.Authorization（Bearer xxx）。
     Codex 使用 bearer_token_env_var=MCD_MCP_TOKEN，配置示例见 docs/GETTING_STARTED.md；
     本脚本不自动扫描 Codex TOML，也不判定客户端是否已经加载 MCP 工具。

用法：
  python scripts/check_mcp.py                 # 只查本地配置，不发网络请求
  python scripts/check_mcp.py --probe         # 额外直连 mcp.mcd.cn 验证 Token（一次 now-time-info）
  python scripts/check_mcp.py --config PATH   # 指定 MCP JSON（未指定时兼容 WorkBuddy 路径）

隐私：脚本永不打印 Token 内容，只输出"是否配置/形态是否为占位符"。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

MCP_URL = "https://mcp.mcd.cn"
PLACEHOLDER_PATTERNS = ("${", "YOUR_MCP_TOKEN", "<", "你的", "替换")


def _looks_like_placeholder(token: str) -> bool:
    return any(p in token for p in PLACEHOLDER_PATTERNS)


def load_local_config(config_path: str | None = None) -> dict:
    """返回 {has_config, has_token, token_is_placeholder, source}。不读取 Token 内容到输出。"""
    env = os.environ.get("MCD_MCP_TOKEN", "").strip()
    if env:
        return {
            "has_config": True,
            "has_token": True,
            "token_is_placeholder": _looks_like_placeholder(env),
            "source": "env:MCD_MCP_TOKEN",
        }
    path = Path(config_path) if config_path else Path.home() / ".workbuddy" / "mcp.json"
    if not path.exists():
        return {"has_config": False, "has_token": False, "token_is_placeholder": False, "source": None, "config_path": str(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return {"has_config": True, "has_token": False, "token_is_placeholder": False, "source": None,
                "config_path": str(path), "config_error": f"配置文件解析失败: {e}"}
    entry = (data.get("mcpServers") or {}).get("mcd-mcp") or (data.get("mcpServers") or {}).get("mcd_mcp")
    if not entry:
        return {"has_config": False, "has_token": False, "token_is_placeholder": False, "source": None, "config_path": str(path)}
    auth = (entry.get("headers") or {}).get("Authorization", "")
    m = re.match(r"Bearer\s+(\S+)", auth or "")
    if not m:
        return {"has_config": True, "has_token": False, "token_is_placeholder": False, "source": str(path)}
    token = m.group(1)
    return {
        "has_config": True,
        "has_token": True,
        "token_is_placeholder": _looks_like_placeholder(token),
        "source": str(path),
    }


GUIDE_STEPS = [
    "① 申请 Token：手机号登录 https://open.mcd.cn → 右上角【控制台】→ 激活 → 同意协议 → 一键复制 MCP Token（此步即完成账户绑定）。",
    "② 本地凭据：优先设置环境变量 MCD_MCP_TOKEN，供跨客户端脚本读取；新设置后需重新启动相应终端或客户端。不要将 Token 发到对话或写入代码。",
    "③ 配置客户端：服务地址 https://mcp.mcd.cn。WorkBuddy、Codex 等客户端的配置字段不同，请按 docs/GETTING_STARTED.md 中相应示例操作；Codex 通过 bearer_token_env_var 引用 MCD_MCP_TOKEN。",
    "④ 启用客户端中的麦当劳 MCP 服务，按当前客户端提示完成信任/连接；回到对话确认工具可用。脚本 --probe 只验证凭据与服务响应，不代表客户端已加载工具。",
]
GUIDE_AGENT_NOTE = "请在本机客户端设置或环境变量中配置 Token，不要向对话发送 Token。WorkBuddy JSON 仍可兼容回退；Codex 配置方法见 docs/GETTING_STARTED.md。连接未就绪时先完成配置，再继续真实选餐与核价。"

PROBE_BODY = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": "now-time-info", "arguments": {}}}).encode("utf-8")


def _probe_body_verified(body: str) -> bool:
    """验证 tools/call 的 JSON-RPC 结果，兼容 SSE；HTTP 200 本身不代表成功。"""
    envelopes = []
    try:
        envelopes.append(json.loads(body))
    except (json.JSONDecodeError, TypeError):
        for event in body.replace("\r\n", "\n").split("\n\n"):
            data = "\n".join(line[5:].lstrip() for line in event.splitlines() if line.startswith("data:"))
            if not data:
                continue
            try:
                envelopes.append(json.loads(data))
            except json.JSONDecodeError:
                continue

    def business_failed(value) -> bool:
        if isinstance(value, dict):
            return (value.get("success") is False or bool(value.get("error"))
                    or any(business_failed(v) for v in value.values()))
        if isinstance(value, list):
            return any(business_failed(v) for v in value)
        return False

    verified = False
    decoder = json.JSONDecoder()
    for envelope in envelopes:
        if not isinstance(envelope, dict) or envelope.get("jsonrpc") != "2.0" or envelope.get("id") != 1:
            continue
        if "error" in envelope:
            return False
        result = envelope.get("result")
        if not isinstance(result, dict) or result.get("isError") is True or business_failed(result.get("structuredContent")):
            return False
        content = result.get("content") or []
        if not isinstance(content, list):
            return False
        has_content = bool(result.get("structuredContent"))
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            value = block.get("text")
            if not isinstance(value, str) or not value.strip():
                continue
            has_content = True
            # 官方工具可能把业务 JSON 包在说明文本中，需检查其中的明确失败标记。
            for offset, char in enumerate(value):
                if char not in "{[":
                    continue
                try:
                    decoded, _ = decoder.raw_decode(value[offset:])
                except json.JSONDecodeError:
                    continue
                if business_failed(decoded):
                    return False
        verified = verified or has_content
    return verified


def probe_token(token: str, timeout: int = 20) -> dict:
    """直连一次 now-time-info 验证 Token 与网络。绝不返回 Token 本身。"""
    req = urllib.request.Request(
        MCP_URL, data=PROBE_BODY, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                 "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            code = resp.status
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return {"ok": False, "status": "invalid", "http_code": e.code, "message": "Token 无效或已过期（401），请到 open.mcd.cn 控制台重新申请/复制。"}
        return {"ok": False, "status": "network_error", "http_code": e.code, "message": f"服务返回 HTTP {e.code}，请稍后重试。"}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {"ok": False, "status": "network_error", "http_code": None, "message": f"网络不可达：{str(e)[:120]}。请检查网络或代理后重试。"}
    if code == 200 and _probe_body_verified(body):
        return {"ok": True, "status": "verified", "http_code": 200, "message": "凭据与麦当劳 MCP 服务响应验证通过；还需确认当前客户端已加载麦当劳 MCP 工具。"}
    return {"ok": False, "status": "network_error", "http_code": code, "message": "服务响应异常，请稍后重试。"}


def classify(local: dict, do_probe: bool, config_path: str | None) -> dict:
    out = {"checked": True, **{k: v for k, v in local.items() if k != "source"}, "config_source": local.get("source")}
    if not local["has_config"]:
        out["status"] = "not_configured"
        out["guide"] = GUIDE_STEPS + [GUIDE_AGENT_NOTE]
        return out
    if not local["has_token"] or local["token_is_placeholder"]:
        out["status"] = "placeholder"
        out["guide"] = GUIDE_STEPS
        return out
    if not do_probe:
        out["status"] = "configured"
        out["message"] = "本机已发现 Token（未验证有效性）。加 --probe 可直连验证；还需按 docs/GETTING_STARTED.md 配置当前客户端，并确认对话中可发现麦当劳 MCP 工具。"
        return out
    token = os.environ.get("MCD_MCP_TOKEN", "").strip()
    if not token:
        path = Path(config_path) if config_path else Path.home() / ".workbuddy" / "mcp.json"
        auth = ((json.loads(path.read_text(encoding="utf-8")).get("mcpServers") or {}).get("mcd-mcp") or {}).get("headers", {}).get("Authorization", "")
        token = (re.match(r"Bearer\s+(\S+)", auth or "") or [None, ""])[1]
    probe = probe_token(token)
    out["probe"] = probe
    out["status"] = probe["status"]
    out["message"] = probe["message"]
    if probe["status"] in ("invalid", "network_error"):
        out["guide"] = GUIDE_STEPS
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="McBudget 麦当劳 MCP 连接检查")
    ap.add_argument("--probe", action="store_true", help="直连 mcp.mcd.cn 验证 Token（一次 now-time-info）")
    ap.add_argument("--config", default=None, help="MCP JSON 路径（环境变量优先；默认兼容 ~/.workbuddy/mcp.json；Codex 示例见 docs/GETTING_STARTED.md）")
    args = ap.parse_args()

    local = load_local_config(args.config)
    result = classify(local, args.probe, args.config)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
