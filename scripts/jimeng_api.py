#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""jimeng_api.py —— 即梦同源模型单文件调用器（豆包 Seedream 出图 / Seedance 出视频）

即梦 App 没有独立的开放 API；它背后的模型通过「火山方舟 Ark」调用：
  图片：POST {BASE}/images/generations            同步返回 URL
  视频：POST {BASE}/contents/generations/tasks    异步任务，再轮询 /tasks/{id}

零依赖运行；只有拿本地图片当首帧 / 参考图时才需要 Pillow（pip install pillow）。

环境变量：
  ARK_API_KEY     API Key（也可用 --key-file 或 _secrets/ark_api_key.txt）
  ARK_BASE_URL    接口地址。默认国内；海外 BytePlus 用
                  https://ark.ap-southeast.bytepluses.com/api/v3
  JIMENG_LEDGER   成本账本路径，默认 ./jimeng_cost.jsonl（设为空字符串可关闭）

快速开始：
  python3 jimeng_api.py setup      # 第一次：粘贴自己的 Key（不回显、不进仓库）
  python3 jimeng_api.py doctor     # 免费体检
  python3 jimeng_api.py image --prompt "国风2D漫剧，荒原黄昏" --out a.jpg --size 1080x1920
  python3 jimeng_api.py video --prompt "镜头跟随姜焕在荒原狂奔" --image a.jpg --out a.mp4
  python3 jimeng_api.py video --prompt "..." --out b.mp4 --resolution 480p --duration 4
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

BASE = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")

# 火山方舟的模型 ID 必须带版本号，否则 404 InvalidEndpointOrModel.NotFound
MODELS = {
    # 出图（Seedream）
    "flash": "doubao-seedream-5-0-flash-260915",   # 0.12 元/张
    "pro": "doubao-seedream-5-0-pro-260628",       # 0.30 元/张起
    # 出视频（Seedance）
    "fast": "doubao-seedance-2-0-fast-260128",     # 720p 0.80 元/秒
    "vpro": "doubao-seedance-2-0-260128",          # 1080p 2.48 元/秒
    "mini": "doubao-seedance-2-0-mini-260615",     # 720p 0.50 元/秒
}
PRICE_VIDEO = {  # 元/秒
    "doubao-seedance-2-0-fast-260128": {"480p": 0.37, "720p": 0.80},
    "doubao-seedance-2-0-260128": {"480p": 0.46, "720p": 0.99, "1080p": 2.48},
    "doubao-seedance-2-0-mini-260615": {"480p": 0.23, "720p": 0.50},
}
PRICE_IMG = {
    "doubao-seedream-5-0-flash-260915": 0.12,
    "doubao-seedream-5-0-pro-260628": 0.30,
}
DEFAULT_MAX_COST = 10.0  # 单次任务默认费用上限（元），0 = 不限
LEDGER = os.environ.get("JIMENG_LEDGER", os.path.join(os.getcwd(), "jimeng_cost.jsonl"))


# ------------------------------------------------------------------ 基础
def get_key(args):
    """读取 Key：--key-file → ARK_API_KEY → ./_secrets/ark_api_key.txt → ~/.ark_key → ~/.config/jimeng/ark_api_key.txt

    第一次使用（包括别人下载这个 skill 后）：运行 `python3 scripts/jimeng_api.py setup`，
    交互式粘贴自己的 Key，脚本会写到 ~/.config/jimeng/ark_api_key.txt（权限 600）。
    """
    if getattr(args, "key_file", None):
        with open(args.key_file, encoding="utf-8") as f:
            return f.read().strip()
    if os.environ.get("ARK_API_KEY", "").strip():
        return os.environ["ARK_API_KEY"].strip()
    for p in (
        os.path.join(os.getcwd(), "_secrets", "ark_api_key.txt"),
        os.path.expanduser("~/.ark_key"),
        os.path.expanduser("~/.config/jimeng/ark_api_key.txt"),
    ):
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                v = f.read().strip()
            if v:
                return v
    die(
        "找不到 API Key。先运行（推荐，一次即可）：\n"
        "  python3 scripts/jimeng_api.py setup\n"
        "其他方式：\n"
        "  export ARK_API_KEY=ark-xxx\n"
        "  echo 'ark-xxx' > _secrets/ark_api_key.txt\n"
        "  python3 scripts/jimeng_api.py --key-file /path/to/key.txt image ...\n"
        "Key 去 https://ark.volcengine.com/region:cn-beijing/apiKey 生成；"
        "每个使用者用自己的 Key，不要提交到 git、不要发在聊天里。"
    )


def die(msg):
    print("错误: " + msg, file=sys.stderr)
    sys.exit(1)


def api(method, path, payload=None, key=None, timeout=180, retries=3):
    """调 Ark API；对 429/5xx/网络错误做指数退避重试。返回 (status_code, dict)。"""
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(
            BASE + path,
            data=body,
            method=method,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                data = json.loads(raw)
            except Exception:
                data = {"raw": raw[:500]}
            if e.code == 429 or e.code >= 500:
                last = (e.code, data)
                time.sleep(2 ** attempt)
                continue
            return e.code, data
        except Exception as e:  # 网络错误
            last = (-1, {"error": repr(e)[:300]})
            time.sleep(2 ** attempt)
    return last


def err_text(j):
    e = j.get("error") or {}
    return "%s: %s" % (e.get("code") or j.get("code") or "error", (e.get("message") or "")[:200])


def data_uri(path, max_side=1440, quality=88):
    """本地图片 → data URI；也接受 http(s) URL 原样返回。"""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not os.path.exists(path):
        die("图片不存在: " + path)
    try:
        from PIL import Image
    except ImportError:
        die("用本地图片需要 Pillow：pip install pillow（或改用可公网访问的图片 URL）")
    import io

    im = Image.open(path).convert("RGB")
    w, h = im.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def download(url, out):
    d = os.path.dirname(os.path.abspath(out))
    os.makedirs(d or ".", exist_ok=True)
    urllib.request.urlretrieve(url, out)
    size = os.path.getsize(out)
    print("已保存: %s (%.2f MB)" % (out, size / 1024 / 1024), file=sys.stderr)
    return out


def log_cost(kind, model, units, cost, note=""):
    """写成本账本，返回累计花费。"""
    if not LEDGER:
        return 0.0
    row = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "kind": kind,
        "model": model,
        "units": units,
        "cost_yuan": round(cost, 2),
        "note": note,
    }
    d = os.path.dirname(os.path.abspath(LEDGER))
    os.makedirs(d or ".", exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    total = 0.0
    with open(LEDGER, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    total += float(json.loads(line).get("cost_yuan", 0))
                except Exception:
                    pass
    return total


def resolve_model(alias, kind):
    model = MODELS.get(alias)
    if not model:
        die("未知模型别名 %r；可选：%s" % (alias, ", ".join(MODELS)))
    if not model.startswith("doubao-seedream" if kind == "image" else "doubao-seedance"):
        die("模型 %r 不是%s模型" % (alias, "出图" if kind == "image" else "出视频"))
    return model


def estimate_video_cost(model, resolution, duration):
    prices = PRICE_VIDEO.get(model, {})
    if resolution not in prices:
        die(
            "%s 不支持 resolution=%s；可选：%s"
            % (model, resolution, ", ".join(sorted(prices)) or "无")
        )
    return prices[resolution] * duration


# ------------------------------------------------------------------ setup
def cmd_setup(args):
    """首次配置：把 API Key 写进 ~/.config/jimeng/ark_api_key.txt（权限 600）。

    别人下载 skill 后只需要跑一次：交互式粘贴自己的 Key，不会回显、不会进 shell 历史，
    也不会写进仓库（该路径在仓库之外）。
    """
    target = args.key_file or os.path.expanduser("~/.config/jimeng/ark_api_key.txt")
    if args.show_path:
        print(target)
        return 0

    print("Key 申请/复制：https://ark.volcengine.com/region:cn-beijing/apiKey")
    if os.path.exists(target):
        print("注意：将覆盖已有 Key：%s" % target.replace(os.path.expanduser("~"), "~"))
    if args.stdin:
        key = sys.stdin.read().strip()
    else:
        import getpass
        key = getpass.getpass("粘贴你的 Ark API Key（输入不回显，回车确认）: ").strip()

    if not key:
        die("没有读到 Key，未写入任何文件。")
    if not key.startswith("ark-"):
        print("警告：Ark Key 一般以 `ark-` 开头，请确认是否复制完整。", file=sys.stderr)
    if len(key) < 20:
        print("警告：Key 只有 %d 个字符，疑似不完整。" % len(key), file=sys.stderr)

    d = os.path.dirname(os.path.abspath(target))
    os.makedirs(d, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(key + "\n")
    os.chmod(target, 0o600)
    print("已保存: %s（权限 600，仅本用户可读）" % target.replace(os.path.expanduser("~"), "~"))
    print("读取顺序：--key-file → ARK_API_KEY → ./_secrets/ark_api_key.txt → ~/.ark_key → 本文件")

    if args.no_verify:
        return 0
    print("正在验证 Key…")
    code, j = api("GET", "/models", key=key, timeout=30, retries=1)
    if code == 200:
        print("验证通过 ✓ 接下来运行: python3 scripts/jimeng_api.py doctor")
        return 0
    print("验证失败 ✗ HTTP %s %s" % (code, err_text(j)), file=sys.stderr)
    print("Key 已保存但可能无效：请到控制台重新生成后再次运行 setup。", file=sys.stderr)
    return 1


# ------------------------------------------------------------------ doctor
def cmd_doctor(args):
    key = get_key(args)
    print("接口: " + BASE)
    print("Key : %s***（%d 字符）" % (key[:4], len(key)))
    code, j = api("GET", "/models", key=key, timeout=30, retries=1)
    if code != 200:
        print("鉴权: ✗ HTTP %s %s" % (code, err_text(j)))
        print("提示：重新配置 Key → python3 scripts/jimeng_api.py setup")
        return 1
    print("鉴权: ✓")

    ids = {m.get("id") for m in j.get("data", []) if isinstance(m, dict)}
    print("模型目录: %d 个" % len(ids))
    checks = [
        ("image", MODELS["flash"]),
        ("image", MODELS["pro"]),
        ("video", MODELS["fast"]),
        ("video", MODELS["vpro"]),
    ]
    all_ok = True
    for kind, mid in checks:
        if mid not in ids:
            print("  ✗ %-38s 目录中不存在（模型 ID 可能已更新）" % mid)
            all_ok = False
            continue
        # 故意传错参数：拿到 InvalidParameter 说明模型已开通，且该请求不计费
        if kind == "image":
            c, r = api(
                "POST",
                "/images/generations",
                {"model": mid, "prompt": "x", "size": "bad-probe",
                 "output_format": "jpeg", "response_format": "url"},
                key=key,
                timeout=60,
                retries=1,
            )
        else:
            c, r = api(
                "POST",
                "/contents/generations/tasks",
                {"model": mid, "content": [{"type": "text", "text": "x"}],
                 "resolution": "720p", "ratio": "9:16", "duration": 1},
                key=key,
                timeout=60,
                retries=1,
            )
        ec = (r.get("error") or {}).get("code")
        ok = ec == "InvalidParameter"  # 参数校验错误 = 模型已开通
        print("  %s %-38s %s" % ("✓" if ok else "✗", mid, ec or ("HTTP %s" % c)))
        all_ok = all_ok and ok
    if not all_ok:
        print("\n有模型不可用：去控制台「开通管理」勾选（Seedance 2.0 需余额 > 200 元）。")
        print("详见 reference/api.md 的「开通与余额」一节。")
    return 0


# ------------------------------------------------------------------ 出图
def cmd_image(args):
    key = get_key(args)
    model = resolve_model(args.model, "image")
    payload = {
        "model": model,
        "prompt": args.prompt,
        "size": args.size,
        "output_format": args.format,
        "response_format": "url",
        "watermark": False,
    }
    if args.refs:
        payload["image"] = [data_uri(p, max_side=2048, quality=92) for p in args.refs]

    preview = dict(payload)
    if "image" in preview:
        preview["image"] = ["<%s>" % p for p in args.refs]
    if args.dry_run:
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    print("出图: %s → %s（约 ¥%.2f）" % (model, args.out, PRICE_IMG.get(model, 0.3)),
          file=sys.stderr)
    # 出图/建任务用 retries=1：网络超时重试可能重复计费，宁可让用户手动重跑
    code, j = api("POST", "/images/generations", payload, key=key, timeout=300, retries=1)
    if code != 200:
        print("出图失败 HTTP %s :: %s" % (code, err_text(j)), file=sys.stderr)
        return 1
    try:
        url = j["data"][0]["url"]
    except Exception:
        print("返回里没有图片 URL: " + json.dumps(j, ensure_ascii=False)[:400], file=sys.stderr)
        return 1
    download(url, args.out)
    cost = PRICE_IMG.get(model, 0.3)
    total = log_cost("image", model, 1, cost, os.path.basename(args.out))
    print(json.dumps({"out": args.out, "model": model, "cost": cost,
                      "total": round(total, 2)}, ensure_ascii=False))
    return 0


# ------------------------------------------------------------------ 出视频
def _video_content(args):
    content = [{"type": "text", "text": args.prompt}]
    if args.image:
        content.append({"type": "image_url", "image_url": {"url": data_uri(args.image)},
                        "role": "first_frame"})
    if args.last:
        content.append({"type": "image_url", "image_url": {"url": data_uri(args.last)},
                        "role": "last_frame"})
    for p in (args.refs or []):
        content.append({"type": "image_url", "image_url": {"url": data_uri(p)},
                        "role": "reference_image"})
    return content


def _wait_task(task_id, key, out, args, model, resolution, duration):
    t0 = time.time()
    while time.time() - t0 < args.timeout:
        code, r = api("GET", "/contents/generations/tasks/" + task_id, key=key, timeout=60, retries=1)
        if code != 200:
            # 4xx 是确定性错误（任务不存在/Key 失效），重试没意义；5xx/网络错误才继续等
            if 400 <= code < 500 and code != 429:
                print("查询任务失败 HTTP %s :: %s" % (code, err_text(r)), file=sys.stderr)
                return 1
            print("  查询失败 HTTP %s（%s 秒后重试）" % (code, args.interval), file=sys.stderr)
            time.sleep(args.interval)
            continue
        status = r.get("status")
        print("  [%4ds] %s" % (int(time.time() - t0), status), file=sys.stderr)
        if status == "succeeded":
            try:
                url = r["content"]["video_url"]
            except Exception:
                print("任务成功但没有 video_url: " + json.dumps(r, ensure_ascii=False)[:400],
                      file=sys.stderr)
                return 1
            if out:
                download(url, out)
            cost = estimate_video_cost(model, resolution, duration)
            total = log_cost("video", model, duration, cost, os.path.basename(out or task_id))
            print(json.dumps({
                "out": out,
                "task_id": task_id,
                "url": url,
                "model": model,
                "resolution": resolution,
                "duration": duration,
                "cost": round(cost, 2),
                "total": round(total, 2),
                "usage_tokens": (r.get("usage") or {}).get("completion_tokens"),
            }, ensure_ascii=False))
            return 0
        if status in ("failed", "cancelled"):
            print("任务%s :: %s" % (status, json.dumps(r.get("error") or r, ensure_ascii=False)[:400]),
                  file=sys.stderr)
            return 1
        time.sleep(args.interval)
    print("超时，任务仍在跑。稍后用续查：\n  python3 jimeng_api.py task --id %s --out %s"
          % (task_id, out or "out.mp4"), file=sys.stderr)
    return 1


def cmd_video(args):
    key = get_key(args)
    model = resolve_model(args.model, "video")
    if args.duration < 4 or args.duration > 15:
        die("duration 必须在 4-15 秒之间（Seedance 2.0 系列），当前 %s" % args.duration)
    if args.image and args.last and args.refs:
        die("首尾帧模式与多参考图模式互斥：--image/--last 与 --refs 不要同时用")

    cost_est = estimate_video_cost(model, args.resolution, args.duration)
    if args.max_cost and cost_est > args.max_cost:
        die("预计 ¥%.2f 超过 --max-cost ¥%.2f。确认要花这笔钱就加大 --max-cost（0 = 不限）。"
            % (cost_est, args.max_cost))

    if args.task_id:  # 续查已存在的任务
        return _wait_task(args.task_id, key, args.out, args,
                          model, args.resolution, args.duration)

    content = _video_content(args)
    payload = {
        "model": model,
        "content": content,
        "resolution": args.resolution,
        "ratio": args.ratio,
        "duration": args.duration,
        "generate_audio": bool(args.audio),
        "watermark": False,
    }
    if args.seed >= 0:
        payload["seed"] = args.seed

    if args.dry_run:
        preview = dict(payload)
        preview["content"] = [
            {"type": c["type"],
             **({"role": c["role"]} if "role" in c else {}),
             **({"text": c["text"]} if "text" in c else {}),
             **({"image_url": "<%s>" % (args.image or args.last or "ref")}
                if "image_url" in c else {})}
            for c in content
        ]
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        print("# 预计费用 ¥%.2f（%s @ %s × %ds）" % (cost_est, model, args.resolution, args.duration),
              file=sys.stderr)
        return 0

    print("创建视频任务: %s @ %s / %s / %ds / %s（预计 ¥%.2f）"
          % (model, args.resolution, args.ratio, args.duration, args.out or "不下载", cost_est),
          file=sys.stderr)
    # retries=1：创建任务不自动重试，避免重复建单/重复计费
    code, j = api("POST", "/contents/generations/tasks", payload, key=key, timeout=180, retries=1)
    if code != 200:
        print("创建任务失败 HTTP %s :: %s" % (code, err_text(j)), file=sys.stderr)
        print("常见原因见 reference/api.md「常见错误码」。", file=sys.stderr)
        return 1
    task_id = j.get("id")
    if not task_id:
        print("返回里没有任务 ID: " + json.dumps(j, ensure_ascii=False)[:400], file=sys.stderr)
        return 1
    print("task: " + task_id, file=sys.stderr)

    if args.no_wait:
        print(json.dumps({"task_id": task_id, "status": "submitted",
                          "cost_est": round(cost_est, 2)}, ensure_ascii=False))
        return 0
    return _wait_task(task_id, key, args.out, args,
                      model, args.resolution, args.duration)


# ------------------------------------------------------------------ 续查任务
def cmd_task(args):
    key = get_key(args)
    model = resolve_model(args.model, "video")
    return _wait_task(args.id, key, args.out, args,
                      model, args.resolution, args.duration)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(
        description="即梦同源模型调用器：Seedream 出图 / Seedance 出视频（火山方舟 Ark）",
        epilog="文档：reference/api.md（参数与坑）｜reference/prompting.md（提示词写法）",
    )
    ap.add_argument("--key-file", help="Key 文件路径（优先级最高）")

    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("setup", help="首次配置：保存你自己的 API Key（写入 ~/.config/jimeng/ark_api_key.txt）")
    s.add_argument("--stdin", action="store_true",
                   help="从 stdin 读 Key（自动化用；手工配置不要加，避免进 shell 历史）")
    s.add_argument("--show-path", action="store_true", help="只打印 Key 文件路径，不读取/写入 Key")
    s.add_argument("--no-verify", action="store_true", help="保存后不调用接口验证")
    s.set_defaults(func=cmd_setup)

    d = sub.add_parser("doctor", help="体检：Key 是否有效、哪些模型已开通（免费）")
    d.set_defaults(func=cmd_doctor)

    im = sub.add_parser("image", help="出图（Seedream）")
    im.add_argument("--prompt", required=True)
    im.add_argument("--out", required=True)
    im.add_argument("--model", default="flash", choices=["flash", "pro"])
    im.add_argument("--size", default="2K", help="1K / 1.5K / 2K，或 1080x1920 这类宽x高")
    im.add_argument("--refs", nargs="*", help="参考图（锁角色/风格），本地路径或 URL")
    im.add_argument("--format", default="jpeg", choices=["jpeg", "png"])
    im.add_argument("--dry-run", action="store_true", help="只打印请求，不调用、不计费")
    im.set_defaults(func=cmd_image)

    v = sub.add_parser("video", help="出视频（Seedance，异步任务）")
    v.add_argument("--prompt", required=True)
    v.add_argument("--out", help="输出 mp4 路径；配合 --no-wait 可省略")
    v.add_argument("--model", default="fast", choices=["fast", "vpro", "mini"])
    v.add_argument("--image", help="首帧图片（图生视频，最稳）")
    v.add_argument("--last", help="尾帧图片（首尾帧生视频）")
    v.add_argument("--refs", nargs="*", help="参考图 0-9 张（锁角色/风格）")
    v.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p"])
    v.add_argument("--ratio", default="9:16", help="9:16 / 16:9 / 1:1 / 4:3 / 3:4 / adaptive")
    v.add_argument("--duration", type=int, default=5, help="4-15 秒")
    v.add_argument("--seed", type=int, default=-1, help="固定种子便于复现；-1 = 随机")
    v.add_argument("--audio", action="store_true", help="生成带音频的视频（默认无声）")
    v.add_argument("--max-cost", type=float, default=DEFAULT_MAX_COST,
                   help="单次费用上限（元），默认 %s；0 = 不限" % DEFAULT_MAX_COST)
    v.add_argument("--no-wait", action="store_true", help="提交后立刻返回 task_id，不等待")
    v.add_argument("--task-id", help="续查已提交的任务（不新建）")
    v.add_argument("--interval", type=int, default=10, help="轮询间隔秒")
    v.add_argument("--timeout", type=int, default=2400, help="最长等待秒数")
    v.add_argument("--dry-run", action="store_true", help="只打印请求，不调用、不计费")
    v.set_defaults(func=cmd_video)

    t = sub.add_parser("task", help="按 task id 续查/下载已提交的视频任务")
    t.add_argument("--id", required=True)
    t.add_argument("--out", help="下载到该路径（不给则只打印状态）")
    t.add_argument("--model", default="fast", choices=["fast", "vpro", "mini"],
                   help="仅用于费用估算")
    t.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p"])
    t.add_argument("--duration", type=int, default=5)
    t.add_argument("--interval", type=int, default=10)
    t.add_argument("--timeout", type=int, default=2400)
    t.set_defaults(func=cmd_task)

    a = ap.parse_args()
    return a.func(a) or 0


if __name__ == "__main__":
    sys.exit(main())
