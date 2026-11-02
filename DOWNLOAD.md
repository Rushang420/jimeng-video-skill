# 完整下载与安装流程（从零到第一条视频）

> 适用于 **macOS / Windows / Linux**。照着复制命令即可，不需要懂代码。
> 全程约 5 分钟，其中 2 分钟是去控制台申请 Key。

```
① 下载仓库 → ② 配置自己的 API Key → ③ doctor 验证 → ④ 生成第一条视频 → ⑤（可选）装成 Agent Skill
```

---

## 第 0 步：准备（1 分钟）

**需要三样东西：**

| 准备项 | 怎么判断有没有 | 没有怎么办 |
|---|---|---|
| Python 3.8+ | 终端运行 `python3 --version`（Windows 试 `python --version`） | 去 <https://www.python.org/downloads/> 安装，Windows 安装时勾选 *Add Python to PATH* |
| 火山方舟账号 | 能登录 <https://console.volcengine.com/ark> | 注册 + 实名认证 |
| Ark API Key | 有 `ark-` 开头的一串字符 | 见下方「申请 Key」 |
| （可选）git | `git --version` | 不装也行，用第 1 步的 ZIP 方式 |

**申请 Key（一次性）：**

1. 打开 <https://ark.volcengine.com/region:cn-beijing/apiKey> 并登录（需实名）。
2. 控制台左侧「开通管理」→ 勾选 **Seedream（图片生成）** 和 **Seedance（视频生成）**。
3. 给账户充值：**Seedance 2.0 系列要求余额 > 200 元**（或购买 200 元资源包）。
4. 回到「API Key」→ 创建 → 复制 `ark-` 开头的一整串（**只显示一次**）。
5. 费用参考：出图 0.12 元/张；视频 480p 约 0.37 元/秒、720p 约 0.80 元/秒。
   5 秒 720p 约 4 元，第一次建议用 `480p / 4s` 试片（约 1.48 元）。

> ⚠️ Key 等于你的账户扣费权限：不要贴到群里、issue、聊天记录，也不要提交 git。
> 本项目不会收集、上传你的 Key。

---

## 第 1 步：下载（1 分钟，三选一）

### 方式 A：git clone（推荐，方便更新）

```bash
git clone https://github.com/Rushang420/jimeng-video-skill.git
cd jimeng-video-skill
```

### 方式 B：下载 ZIP（不用装 git）

1. 打开仓库主页：<https://github.com/Rushang420/jimeng-video-skill>
2. 点绿色 **Code** 按钮 → **Download ZIP**
3. 解压，得到一个文件夹（名字可能是 `jimeng-video-skill-main`）
4. 终端进入该文件夹：

```bash
cd ~/Downloads/jimeng-video-skill-main      # macOS / Linux，按实际路径改
# Windows PowerShell：
# cd $env:USERPROFILE\Downloads\jimeng-video-skill-main
```

### 方式 C：固定版本（要可复现时用）

到 <https://github.com/Rushang420/jimeng-video-skill/releases> 下载最新 Release 的
**Source code (zip)**，或：

```bash
git clone --branch v1.2.0 --depth 1 https://github.com/Rushang420/jimeng-video-skill.git
cd jimeng-video-skill
```

### 确认下载完整

```bash
ls
# 应该看到：LICENSE  README.md  SKILL.md  reference  requirements.txt  scripts
```

---

## 第 2 步：配置你自己的 API Key（1 分钟）

**在仓库目录里**运行：

```bash
python3 scripts/jimeng_api.py setup
```

Windows 如果 `python3` 不存在，把命令里的 `python3` 换成 `python` 或 `py -3`：

```powershell
py -3 scripts\jimeng_api.py setup
```

会看到：

```text
Key 申请/复制：https://ark.volcengine.com/region:cn-beijing/apiKey
粘贴你的 Ark API Key（输入不回显，回车确认）:        ← 粘贴后按回车，屏幕上不会显示
已保存: ~/.config/jimeng/ark_api_key.txt（权限 600，仅本用户可读）
正在验证 Key…
验证通过 ✓ 接下来运行: python3 scripts/jimeng_api.py doctor
```

Key 保存位置：`~/.config/jimeng/ark_api_key.txt`（Windows 是 `C:\Users\你\.config\jimeng\ark_api_key.txt`）。

**为什么这样做是安全的：**

- 输入不回显（`getpass`），旁边的人看不到；
- 不是命令行参数，**不会进 shell 历史**（`history` 里查不到）；
- 文件在仓库之外，**不可能被 commit**，权限 600 只有本用户可读。

**不想用 `setup` 也可以**（优先级从高到低）：

```bash
python3 scripts/jimeng_api.py --key-file /path/to/key.txt doctor   # 1. 临时指定文件
export ARK_API_KEY=ark-xxxxxxxx                                    # 2. 环境变量（当前终端）
echo 'ark-xxx' > _secrets/ark_api_key.txt                          # 3. 仓库内（已 gitignore）
echo 'ark-xxx' > ~/.ark_key                                        # 4. 家目录
~/.config/jimeng/ark_api_key.txt                                   # 5. setup 的默认位置
```

---

## 第 3 步：验证（10 秒，免费）

```bash
python3 scripts/jimeng_api.py doctor
```

预期输出（模型开通情况因账号而异）：

```text
接口: https://ark.cn-beijing.volces.com/api/v3
Key : ark-***（46 字符）
鉴权: ✓
模型目录: 138 个
  ✓ doubao-seedream-5-0-flash-260915       InvalidParameter
  ✗ doubao-seedream-5-0-pro-260628         ModelNotOpen
  ✓ doubao-seedance-2-0-fast-260128        InvalidParameter
  ✗ doubao-seedance-2-0-260128             ModelNotOpen
```

- **鉴权 ✓** = Key 有效，可以用了。
- **模型 ✗ ModelNotOpen** = 该模型没开通，不影响默认的 `flash` / `fast`；
  要高清档去控制台「开通管理」勾选（Seedance 2.0 还需余额 > 200 元）。
- **鉴权 ✗ 401** = Key 错或过期 → 重新 `setup` 覆盖。

---

## 第 4 步：生成第一条视频（约 1.6 元）

先出首帧图，再用首帧图生视频（最稳，人物不跑偏）：

```bash
# ① 出图：0.12 元
python3 scripts/jimeng_api.py image \
  --prompt "国风2D漫剧，少年在荒原回头，黄昏逆光，中景" \
  --out first.jpg --size 1080x1920

# ② 图生视频：480p × 4s ≈ 1.48 元
python3 scripts/jimeng_api.py video \
  --prompt "镜头缓慢推进，衣摆和头发被风吹动，尘土轻扬，电影感" \
  --image first.jpg --out shot.mp4 \
  --resolution 480p --duration 4 --ratio 9:16
```

运行时会看到费用预估、任务状态轮询、下载进度；成功后得到 `shot.mp4`，直接双击播放。

其他常用写法：

```bash
# 纯文生视频（不需要首帧图）
python3 scripts/jimeng_api.py video --prompt "雨夜霓虹街道，镜头缓慢横移" --out b.mp4

# 先看请求、不花钱
python3 scripts/jimeng_api.py video --prompt "..." --out c.mp4 --dry-run

# 提交后不等待（长任务），之后再续查下载
python3 scripts/jimeng_api.py video --prompt "..." --out d.mp4 --no-wait
python3 scripts/jimeng_api.py task --id <task_id> --out d.mp4
```

> 省钱顺序：`dry-run`（免费）→ 480p/4s（≈1.48 元）→ 满意再 720p。
> 单次费用默认上限 10 元，超了会直接拒绝执行（`--max-cost` 可调，0 = 不限）。

---

## 第 5 步（可选）：装成 Agent Skill，让 AI 直接调用

装好后，以后对 AI 说「**用即梦生成一条视频**」它就会按 `SKILL.md` 的流程执行。

```bash
bash scripts/install_skill.sh
```

它会自动探测并链接到这些目录（存在才装）：

```
~/.agents/skills/    ~/.dsh/skills/    ~/.cursor/skills/
~/.codex/skills/     ~/.claude/skills/
```

- 想复制一份而不是软链接（仓库删了也能用）：`bash scripts/install_skill.sh --copy`
- 卸载：`bash scripts/install_skill.sh --uninstall`
- Windows 没有 bash 时，手动把整个文件夹复制到
  `%USERPROFILE%\.agents\skills\jimeng-video-skill`（用资源管理器或 PowerShell
  `Copy-Item -Recurse`）。

装完**新开一个 AI 会话**，输入：

> 用即梦生成一条视频，主题：雨夜霓虹街道，镜头缓慢横移，9:16，先 480p 试片

---

## 第 6 步（可选）：一键脚本

不想一步步敲，可以用一键脚本（完成第 2–4 步；加 `--with-skill` 连第 5 步也做了）：

```bash
bash scripts/quickstart.sh                  # 检测环境 → 配 Key（已配则跳过）→ doctor
bash scripts/quickstart.sh --with-skill     # 额外安装成 Agent Skill
bash scripts/quickstart.sh --with-pillow    # 顺便装 Pillow（用本地图当首帧时需要）
```

---

## 第 7 步：更新 / 换 Key / 卸载

| 想做 | 命令 |
|---|---|
| 更新到最新版 | `cd jimeng-video-skill && git pull`（软链接安装自动生效；`--copy` 装的要重跑 install_skill.sh） |
| 换 Key | `python3 scripts/jimeng_api.py setup`（覆盖） |
| 看 Key 存哪 | `python3 scripts/jimeng_api.py setup --show-path` |
| 删除 Key | `rm ~/.config/jimeng/ark_api_key.txt` |
| 卸载 skill | `bash scripts/install_skill.sh --uninstall` |
| 彻底删除 | 删掉下载的仓库文件夹即可，Key 文件在 `~/.config/jimeng/` 需要单独删 |

---

## 常见问题（按阶段）

**下载阶段**

| 现象 | 原因 | 解决 |
|---|---|---|
| `git: command not found` | 没装 git | 用第 1 步方式 B（ZIP）；或安装 git |
| GitHub 打不开/很慢 | 网络 | 多试几次；或让能访问的朋友帮下 ZIP；必要时配代理（`HTTPS_PROXY`） |
| 解压后终端 `cd` 报错 | 路径含空格/中文 | 用引号包住路径：`cd "$HOME/Downloads/我的 文件夹"` |

**配置阶段**

| 现象 | 原因 | 解决 |
|---|---|---|
| `python3: command not found` | Windows 常见 | 命令换成 `python` 或 `py -3` |
| `Permission denied` | 直接执行脚本 | 用 `python3 scripts/jimeng_api.py ...` 或 `bash scripts/xxx.sh` |
| 找不到 API Key | 没配置 | `python3 scripts/jimeng_api.py setup` |
| `401 AuthenticationError` | Key 错/过期/多空格 | 重新 `setup`；确认复制完整、没带引号 |

**运行阶段**

| 现象 | 原因 | 解决 |
|---|---|---|
| `404 ModelNotOpen` | 模型没开通 | 控制台「开通管理」勾选；Seedance 2.0 需余额 > 200 元 |
| `402 Payment Required` | 欠费/尺寸受限 | 充值或换 `1K` / `480p` |
| `InvalidParameter` | 参数不合法（如时长 1 秒、首尾帧+参考图混用） | 时长 4–15 秒；图片模式只选一种 |
| `429` / 网络超时 | 限流/网络抖动 | 等 30–60 秒重跑；查询接口会自动退避 |
| 任务 `failed` | 输入图太大/模式冲突/内容审核 | 图缩到 1440 长边；只用 `--image` 或只用 `--refs`；换提示词 |
| 视频没声音 | 默认无声 | 加 `--audio`（漫剧一般自己配音，保持无声） |
| 提示 `PIL` / Pillow 缺失 | 用了本地图片 | `pip install pillow`（或改用图片 URL） |

**还没解决？** 把**报错原文**（不要带 Key）发 issue：
<https://github.com/Rushang420/jimeng-video-skill/issues>

---

## 完整命令清单（复制即用）

```bash
# ═══ 1. 下载 ═══
git clone https://github.com/Rushang420/jimeng-video-skill.git
cd jimeng-video-skill

# ═══ 2. 配 Key（粘贴自己的 ark- Key，不回显）═══
python3 scripts/jimeng_api.py setup

# ═══ 3. 验证 ═══
python3 scripts/jimeng_api.py doctor

# ═══ 4. 第一条视频（约 1.6 元）═══
python3 scripts/jimeng_api.py image --prompt "国风2D漫剧，少年在荒原回头，黄昏逆光，中景" \
  --out first.jpg --size 1080x1920
python3 scripts/jimeng_api.py video --prompt "镜头缓慢推进，衣摆和头发被风吹动，尘土轻扬" \
  --image first.jpg --out shot.mp4 --resolution 480p --duration 4

# ═══ 5.（可选）装成 Agent Skill ═══
bash scripts/install_skill.sh
```

---

## 让 AI Agent 帮你装（把下面这段发给它）

```text
请帮我安装并使用这个即梦视频 skill：
仓库：https://github.com/Rushang420/jimeng-video-skill
1. 先读 SKILL.md 和 README.md，按里面的流程操作；
2. 检查 python3 是否可用，把仓库 clone 或解压到合适位置；
3. 识别到我还没有 API Key 时，请让我自己在终端运行
   `python3 scripts/jimeng_api.py setup`（不要让我把 Key 发在对话里）；
4. 我配置完后再运行 `python3 scripts/jimeng_api.py doctor` 确认鉴权；
5. 先用 `--dry-run` 让我确认请求和费用，再生成一条 480p/4s 的测试视频；
6. 如果你支持 skills 目录，最后执行 `bash scripts/install_skill.sh` 把它装好。
注意：不要打印、回显或记录我的 API Key。
```

---

## 安全清单

- ✅ Key 用 `setup` 存进 `~/.config/jimeng/`（600 权限），不进仓库、不进历史
- ✅ 每个人用**自己的** Key，费用记在自己账户
- ✅ 不把 Key 贴在聊天/issue/截图里；要撤销就去控制台重新生成，再 `setup` 覆盖
- ✅ 生成产物（`*.mp4`/`*.jpg`）和成本账本 `jimeng_cost.jsonl` 已在 `.gitignore`
- ❌ 不要把 Key 硬编码进命令、脚本、README 或提交

---

其他文档：[README](README.md)｜[SKILL.md](SKILL.md)｜[接口与价格](reference/api.md)｜[提示词写法](reference/prompting.md)
