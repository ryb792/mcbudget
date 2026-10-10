#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""McBudget 支付辅助：把 create-order 返回的 payH5Url 生成本地二维码 PNG。

为什么本地生成：payH5Url 含订单号，不允许上传到任何第三方二维码服务（隐私约束，
见 SKILL.md / data_conventions.md），因此二维码必须离线生成。

可选依赖：qrcode + pillow（本技能唯一可选增强依赖，标准库之外）。
  安装：pip install qrcode pillow
未安装时本脚本打印替代方案（链接直接打开 / 麦当劳 App 待支付订单），不报错退出。

用法：
  python scripts/make_qr.py "https://mcd.cn/mcp/scanToPay?orderId=..." -o pay_qr.png

注意：二维码只用于把链接带到手机，实际支付一律由用户在麦当劳收银页/App 内完成；
本脚本不访问网络、不存储链接内容之外的任何信息。
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description="生成支付链接的本地二维码（可选增强）")
    ap.add_argument("url", help="create-order 返回的 payH5Url")
    ap.add_argument("-o", "--out", default="pay_qr.png", help="输出 PNG 路径（默认 pay_qr.png）")
    args = ap.parse_args()

    url = args.url.strip()
    if not url.lower().startswith(("http://", "https://")):
        print("错误：url 必须是 http(s) 链接")
        return 2

    try:
        import qrcode  # noqa: PLC0415 —— 可选依赖，运行时检测
    except ImportError:
        print("未安装可选依赖 qrcode。两种替代方式：")
        print("  方式A（推荐）：把 payH5Url 链接发到手机，直接在手机浏览器/微信中打开即可到达麦当劳收银页，无需扫码；")
        print("  方式B：打开麦当劳 App（登录下单用的手机号）→ 我的订单 → 待支付订单 → 付款。")
        print("如仍需二维码图片，请先安装：pip install qrcode pillow")
        return 1

    import qrcode.constants  # noqa: PLC0415
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    try:
        img = qr.make_image(fill_color="#2B2320", back_color="white")
    except Exception:  # 无 pillow 时的兜底
        img = qr.make_image()
    img.save(args.out)
    print(f"已生成 {args.out}")
    print("使用提示：手机扫码将直接打开麦当劳收银页（H5）。若页面引导跳转 App，也可直接在")
    print("麦当劳 App『我的订单 → 待支付』中付款（登录下单所用手机号即可看到该订单）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
