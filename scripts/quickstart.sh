#!/usr/bin/env bash
# 一键完成：检查环境 → 配置 Key（已配则跳过）→ doctor 验证 →（可选）装成 Agent Skill
#
# 用法：
#   bash scripts/quickstart.sh                 # 基础流程
#   bash scripts/quickstart.sh --with-skill    # 顺便装成 Agent Skill
#   bash scripts/quickstart.sh --with-pillow   # 顺便安装 Pillow（本地图片当首帧时需要）
#   bash scripts/quickstart.sh --skip-setup    # 跳过 Key 配置（已配置或 CI）
#   bash scripts/quickstart.sh --skip-doctor   # 跳过 doctor 验证
#
# 环境变量：PYTHON=python3.11（指定解释器）｜SKILLS_DIR=...（配合 --with-skill）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-python3}"
WITH_SKILL=0
WITH_PILLOW=0
SKIP_SETUP=0
SKIP_DOCTOR=0

for arg in "$@"; do
  case "$arg" in
    --with-skill) WITH_SKILL=1 ;;
    --with-pillow) WITH_PILLOW=1 ;;
    --skip-setup) SKIP_SETUP=1 ;;
    --skip-doctor) SKIP_DOCTOR=1 ;;
    -h | --help)
      sed -n '2,10p' "$0"
      exit 0
      ;;
    *)
      echo "未知参数: $arg（可用 --with-skill / --with-pillow / --skip-setup / --skip-doctor）" >&2
      exit 1
      ;;
  esac
done

echo "=============================================="
echo " 即梦视频 Skill · 一键配置"
echo " 目录: $ROOT"
echo "=============================================="

# ---------- 1/4 检查 Python ----------
echo
echo "[1/4] 检查 Python…"
if ! command -v "$PY" >/dev/null 2>&1; then
  for cand in python3 python py; do
    if command -v "$cand" >/dev/null 2>&1; then
      PY="$cand"
      break
    fi
  done
fi
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "✗ 找不到 Python。请先安装 Python 3.8+：https://www.python.org/downloads/" >&2
  exit 1
fi
if ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
  echo "✗ Python 版本过低：$("$PY" -V 2>&1)，需要 3.8+" >&2
  exit 1
fi
echo "✓ $("$PY" -V 2>&1)（$PY）"

# ---------- 2/4 配置 Key ----------
echo
echo "[2/4] 检查 API Key…"
key_found=0
if [ -n "${ARK_API_KEY:-}" ] \
  || [ -f "$ROOT/_secrets/ark_api_key.txt" ] \
  || [ -f "$HOME/.ark_key" ] \
  || [ -f "$HOME/.config/jimeng/ark_api_key.txt" ]; then
  key_found=1
fi

if [ "$key_found" = "1" ]; then
  echo "✓ 已检测到 API Key，跳过配置（想换 Key 就运行：$PY scripts/jimeng_api.py setup）"
elif [ "$SKIP_SETUP" = "1" ]; then
  echo "! 已指定 --skip-setup，但没检测到 Key，doctor 大概率会失败"
else
  echo "还没有 API Key。下面会提示你粘贴（输入不回显，不会进 shell 历史）。"
  echo "申请地址：https://ark.volcengine.com/region:cn-beijing/apiKey"
  "$PY" scripts/jimeng_api.py setup
fi

# ---------- 3/4 可选依赖 ----------
echo
echo "[3/4] 检查可选依赖 Pillow…"
if "$PY" -c 'import PIL' >/dev/null 2>&1; then
  echo "✓ Pillow 已安装（本地图片当首帧/参考图时需要，已具备）"
elif [ "$WITH_PILLOW" = "1" ]; then
  echo "… 安装 Pillow"
  "$PY" -m pip install --upgrade pillow || echo "! Pillow 安装失败：仅影响「用本地图片当首帧」，纯文生视频不受影响"
else
  echo "· 未安装 Pillow（可选）。用本地图片当首帧时再装：$PY -m pip install pillow，或加 --with-pillow"
fi

# ---------- 4/4 doctor ----------
echo
echo "[4/4] 验证 Key 与模型开通状态（免费）…"
if [ "$SKIP_DOCTOR" = "1" ]; then
  echo "! 已指定 --skip-doctor，跳过"
else
  if ! "$PY" scripts/jimeng_api.py doctor; then
    echo
    echo "✗ 验证未通过。常见原因：" >&2
    echo "  - Key 无效/过期 → 重新运行: $PY scripts/jimeng_api.py setup" >&2
    echo "  - 模型未开通 → 控制台「开通管理」勾选（Seedance 2.0 需余额 > 200 元）" >&2
    echo "  - 网络问题 → 检查代理/重试" >&2
    exit 1
  fi
fi

# ---------- 可选：安装成 Agent Skill ----------
if [ "$WITH_SKILL" = "1" ]; then
  echo
  echo "[+] 安装成 Agent Skill…"
  bash scripts/install_skill.sh
fi

# ---------- 完成 ----------
cat <<EOF

==============================================
 ✓ 配置完成
==============================================

第一条视频（480p/4s，约 1.6 元）：

  $PY scripts/jimeng_api.py image \\
    --prompt "国风2D漫剧，少年在荒原回头，黄昏逆光，中景" \\
    --out first.jpg --size 1080x1920

  $PY scripts/jimeng_api.py video \\
    --prompt "镜头缓慢推进，衣摆和头发被风吹动，尘土轻扬" \\
    --image first.jpg --out shot.mp4 \\
    --resolution 480p --duration 4

先看请求不花钱：任何命令加 --dry-run
完整说明：DOWNLOAD.md ｜ 接口参数：reference/api.md
EOF
