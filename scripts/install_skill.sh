#!/usr/bin/env bash
# 把本 skill 安装到本机 Agent 技能目录（默认软链接，仓库更新自动生效）。
#
# 用法：
#   bash scripts/install_skill.sh            # 软链接到已存在的技能目录
#   bash scripts/install_skill.sh --copy     # 复制一份（不跟随仓库）
#   bash scripts/install_skill.sh --uninstall
#
# 自定义目录：SKILLS_DIR="$HOME/my/skills" bash scripts/install_skill.sh
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="$(basename "$SRC")"
MODE="link"

case "${1:-}" in
  --copy) MODE="copy" ;;
  --uninstall) MODE="uninstall" ;;
  "") ;;
  *) echo "未知参数: $1（可用：--copy / --uninstall）" >&2; exit 1 ;;
esac

TARGETS=()
if [ -n "${SKILLS_DIR:-}" ]; then
  TARGETS=("$SKILLS_DIR")
else
  for d in \
    "$HOME/.agents/skills" \
    "$HOME/.dsh/skills" \
    "$HOME/.cursor/skills" \
    "$HOME/.codex/skills" \
    "$HOME/.claude/skills"; do
    [ -d "$d" ] && TARGETS+=("$d")
  done
  if [ ${#TARGETS[@]} -eq 0 ]; then
    TARGETS=("$HOME/.agents/skills")
  fi
fi

echo "skill 源目录: $SRC"
echo "skill 名称  : $NAME"

for dir in "${TARGETS[@]}"; do
  dst="$dir/$NAME"
  if [ "$MODE" = "uninstall" ]; then
    if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$SRC" ]; then
      rm "$dst" && echo "已移除软链接: $dst"
    elif [ -d "$dst" ]; then
      echo "跳过（不是本仓库的软链接，手动确认后再删）: $dst"
    else
      echo "没有安装记录: $dst"
    fi
    continue
  fi

  mkdir -p "$dir"
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    echo "跳过（已存在）: $dst"
    continue
  fi

  if [ "$MODE" = "copy" ]; then
    mkdir -p "$dst"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --exclude '.git' --exclude '__pycache__' "$SRC/" "$dst/"
    else
      cp -R "$SRC/." "$dst/"
      rm -rf "$dst/.git" "$dst/__pycache__"
    fi
    echo "已复制: $dst"
  else
    ln -s "$SRC" "$dst"
    echo "已链接: $dst -> $SRC"
  fi
done

echo
echo "验证：让 Agent 说「用即梦生成一条视频」，或读 $SRC/SKILL.md。"
echo "注意：本机仍需配置 ARK_API_KEY，并已开通 Seedance/Seedream。"
