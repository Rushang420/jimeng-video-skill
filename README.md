# 即梦视频生成 Skill（Seedance + Seedream）

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Release](https://img.shields.io/github/v/release/Rushang420/jimeng-video-skill)](https://github.com/Rushang420/jimeng-video-skill/releases)

一个**零依赖、单文件**的即梦同源模型调用器，同时是一个可被 AI Agent 直接调用的 Skill。
下载后配好 Key 就能：**文生视频 / 图生视频 / 首帧生视频 / 首尾帧生视频 / 出图锁角色**，
自带轮询、下载、费用预估与成本账本。

> **先澄清**：即梦 App（jimeng.jianying.com）没有对外 API。所谓「即梦 API」= 火山方舟 Ark 上的
> **Seedream（出图）/ Seedance（出视频）**。本项目调的就是这两个官方模型。
> 网上「即梦逆向 API」有封号与合规风险，本项目不使用。

> 📥 **第一次用？看 [完整下载与安装流程（DOWNLOAD.md）](DOWNLOAD.md)**：
> 从 GitHub 下载（git 或 ZIP）→ 配置自己的 API Key → `doctor` 验证 → 第一条视频 →
> （可选）装成 Agent Skill。含 Windows 命令、预期输出样例、按阶段排错表和「让 AI 帮你装」提示词。

## 能做什么

| 能力 | 命令 | 说明 |
|---|---|---|
| 出图 | `image` | Seedream 5.0 flash，0.12 元/张，可传参考图锁角色 |
| 出视频 | `video` | Seedance 2.0，异步任务 + 自动轮询 + 下载 |
| 图生视频 | `video --image` | 首帧生视频，最稳，漫剧/短剧首选 |
| 首尾帧 | `video --image --last` | 转场、动作衔接 |
| 多参考图 | `video --refs` | 0-9 张，锁角色/风格 |
| 任务续查 | `task --id` | 长任务断线后继续，可下载 |
| 免费体检 | `doctor` | 验证 Key + 模型开通状态，不产生费用 |
| 费用护栏 | `--max-cost` | 默认单次 10 元上限，超限拒绝执行 |
| 成本账本 | 自动 | 每次成功记录到 `jimeng_cost.jsonl` |

## 快速开始（3 分钟）

> 不想用 git？在仓库页点 **Code → Download ZIP**，解压后同样使用（脚本零依赖，不需要安装）。
>
> 想一条命令跑完「检查环境 → 配 Key → 验证」？下载后运行 `bash scripts/quickstart.sh`
> （加 `--with-skill` 顺便装成 Agent Skill）。详见 [DOWNLOAD.md](DOWNLOAD.md)。

```bash
git clone https://github.com/Rushang420/jimeng-video-skill.git
cd jimeng-video-skill

# 1) 配置你自己的 Key（交互式粘贴，输入不回显，不会进 shell 历史）
python3 scripts/jimeng_api.py setup

# 2) 免费体检：Key 是否有效、模型是否已开通
python3 scripts/jimeng_api.py doctor

# 3) 第一条视频（首帧生视频，720p/5s 约 4 元；先试 480p/4s 约 1.48 元）
python3 scripts/jimeng_api.py image --prompt "国风2D漫剧，少年在荒原回头，黄昏逆光" \
  --out first.jpg --size 1080x1920
python3 scripts/jimeng_api.py video --prompt "镜头缓慢推进，衣摆与头发被风吹动，尘土轻扬" \
  --image first.jpg --out shot.mp4 --resolution 480p --duration 4
```

没有 Key？去 <https://ark.volcengine.com/region:cn-beijing/apiKey> 生成（每个使用者用自己的 Key，
费用记在自己的火山方舟账户）。**Seedance 2.0 系列要求账户余额 > 200 元**（或 200 元资源包）；
Seedream 需在控制台勾选开通。

## 别人下载后：怎么配自己的 API Key

仓库里**不含任何 Key**，每个使用者第一次用时自己配置一次即可。推荐用内置的 `setup`：

```bash
python3 scripts/jimeng_api.py setup
# 去 https://ark.volcengine.com/region:cn-beijing/apiKey 复制 Key → 粘贴 → 回车
# 保存到 ~/.config/jimeng/ark_api_key.txt（权限 600），并自动调接口验证
```

三点保证：输入**不回显**（getpass）、**不进 shell 历史**（不是命令行参数）、**不在仓库内**
（写到用户家目录），所以不会被 commit 或误分享。保存后直接 `doctor` 确认即可。

不想用 `setup` 也可以用环境变量或指定文件，优先级从高到低：

```bash
python3 scripts/jimeng_api.py --key-file /path/to/key.txt doctor  # 1. 命令行指定
export ARK_API_KEY=ark-xxxxxxxx                                   # 2. 环境变量
echo 'ark-xxx' > _secrets/ark_api_key.txt                         # 3. 当前目录（已 gitignore）
echo 'ark-xxx' > ~/.ark_key                                       # 4. 家目录
~/.config/jimeng/ark_api_key.txt                                  # 5. setup 的默认位置
```

- 换 Key / 轮换：重新跑一次 `setup` 覆盖即可。
- 删除 Key：`rm ~/.config/jimeng/ark_api_key.txt`。
- 查看 Key 存哪：`python3 scripts/jimeng_api.py setup --show-path`。
- 各自申请各自的 Key，不要共用；把 Key 给 Agent 时也只需让它在**本机终端**运行 `setup`，
  **不要把 Key 明文发进对话**（会留在聊天记录里）。

## 安装成 Agent Skill

下载后把整个目录放进你的 Agent 技能目录即可：

```bash
# 自动探测并链接到 ~/.agents/skills、~/.dsh/skills、~/.cursor/skills、~/.codex/skills、~/.claude/skills
bash scripts/install_skill.sh

# 复制安装（不跟随仓库更新）、卸载
bash scripts/install_skill.sh --copy
bash scripts/install_skill.sh --uninstall

# 或手动
cp -R . ~/.agents/skills/jimeng-video-skill
```

Windows 没有 bash 时，用资源管理器把整个文件夹复制到
`%USERPROFILE%\.agents\skills\jimeng-video-skill` 即可。

装好后在对话里说「用即梦生成一条视频」即可触发；Agent 会读 `SKILL.md` 并按里面的
工作流（doctor → dry-run → 真跑 → 验片）执行。适用于 Codex / Claude Code / Cursor / DSH 等
支持 `SKILL.md` 的 Agent。完整步骤见 [DOWNLOAD.md 第 5 步](DOWNLOAD.md#第-5-步可选装成-agent-skill让-ai-直接调用)。

## 命令速查

```bash
# 首次配置 / 换 Key（交互式，不回显）
python3 scripts/jimeng_api.py setup
python3 scripts/jimeng_api.py setup --show-path   # 看 Key 存在哪

# 体检（免费）
python3 scripts/jimeng_api.py doctor

# 出图
python3 scripts/jimeng_api.py image --prompt "..." --out a.jpg --size 1080x1920
python3 scripts/jimeng_api.py image --prompt "..." --out b.jpg --refs 角色.jpg --size 1080x1920

# 视频（首帧 / 文生 / 首尾帧 / 参考图）
python3 scripts/jimeng_api.py video --prompt "..." --image a.jpg --out a.mp4
python3 scripts/jimeng_api.py video --prompt "..." --out b.mp4 --ratio 16:9
python3 scripts/jimeng_api.py video --prompt "..." --image a.jpg --last b.jpg --out c.mp4
python3 scripts/jimeng_api.py video --prompt "..." --refs r1.jpg r2.jpg --out d.mp4

# 省钱试片 / 不阻塞 / 续查
python3 scripts/jimeng_api.py video --prompt "..." --out e.mp4 --resolution 480p --duration 4
python3 scripts/jimeng_api.py video --prompt "..." --out f.mp4 --no-wait
python3 scripts/jimeng_api.py task --id <task_id> --out f.mp4

# 只检查请求，不花钱
python3 scripts/jimeng_api.py video --prompt "..." --out g.mp4 --dry-run
```

完整参数与坑见 [reference/api.md](reference/api.md)；提示词与镜头写法见
[reference/prompting.md](reference/prompting.md)。

## 价格（2026-10，官方价目）

| 用途 | 模型 | 单价 |
|---|---|---|
| 出图 | Seedream 5.0 flash | 0.12 元/张 |
| 出图 | Seedream 5.0 pro | 0.30 元/张起 |
| 视频 | Seedance 2.0 fast | 720p 0.80 元/秒（480p 0.37） |
| 视频 | Seedance 2.0 | 1080p 2.48 元/秒（720p 0.99） |
| 视频 | Seedance 2.0 mini | 720p 0.50 元/秒（480p 0.23） |

5 秒 720p fast ≈ 4 元。脚本每次真跑前会在 stderr 打印预估费用，并有 10 元默认上限。

## 常见问题

**Q：为什么不用即梦账号直接调？**
即梦 App 未开放 API。其背后模型通过火山方舟（Ark）开放，需要 Ark API Key。

**Q：视频任务一直 `running` / 中断了怎么办？**
任务在云端跑，本机断线不影响。用 `task --id <id>` 续查下载；脚本超时也会打印这条命令。

**Q：人物脸一直变？**
先出首帧图并锁角色参考图，再用 `--image` 图生视频，提示词只写运动，详见
[reference/prompting.md](reference/prompting.md)。

**Q：报 `ModelNotOpen`？**
控制台「开通管理」勾选模型；Seedance 2.0 还需要余额 > 200 元。

**Q：第一次安装的完整步骤在哪？**
见 [DOWNLOAD.md](DOWNLOAD.md)（下载 → 配 Key → 验证 → 第一条视频 → 装成 Agent Skill → 排错）。

**Q：别人怎么用自己的 Key？**
运行 `python3 scripts/jimeng_api.py setup`，粘贴自己的 Key 即可（存到家目录 `~/.config/jimeng/`，
不进仓库、不进 shell 历史）。详见上文「别人下载后：怎么配自己的 API Key」。

**Q：能商用吗？**
生成内容的使用范围以火山方舟/即梦的服务条款为准，本项目只做 API 调用封装。

## 安全

- 仓库不含 Key；每个使用者用自己的 Key（`setup` 写到 `~/.config/jimeng/ark_api_key.txt`，权限 600）。
- 也可以用环境变量 `ARK_API_KEY` 或项目内 `_secrets/ark_api_key.txt`（已 gitignore）。
- 不要把 Key 写进提示词、README、issue、commit 或聊天记录；也不要把带 Key 的终端截图发出去。
- 给别人用请让对方自己申请 Key；想撤销时就地重新生成，再跑一次 `setup` 覆盖。

## 目录结构

```
jimeng-video-skill/
├── SKILL.md                  # Agent 读取的技能说明（工作流 + 护栏）
├── README.md                 # 人类读的说明（本文件）
├── DOWNLOAD.md               # 完整下载/安装流程（从零到第一条视频）
├── scripts/
│   ├── jimeng_api.py         # 单文件调用器：setup/出图/出视频/续查/doctor
│   ├── install_skill.sh      # 链接到本机 Agent 技能目录
│   └── quickstart.sh         # 一键：检查环境 → 配 Key → doctor（可选装 skill）
├── reference/
│   ├── api.md                # 接口、参数、错误码、价格
│   └── prompting.md          # 视频/图片提示词写法与示例
├── requirements.txt          # 可选依赖（Pillow）
├── LICENSE                   # MIT
└── .gitignore
```

## License

MIT，见 [LICENSE](LICENSE)。
