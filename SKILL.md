---
name: jimeng-video-skill
description: 调用即梦同源模型（火山方舟 Seedream 出图 / Seedance 出视频）生成图片和视频。当用户说「用即梦生成视频」「Seedance 文生视频 / 图生视频 / 首帧生视频」「用豆包出图 / 锁角色出图」「调用即梦 API」时使用。
disable-model-invocation: false
---

# 即梦视频 / 图片生成（Seedance + Seedream）

即梦 App 没有独立开放 API。所谓「即梦 API」= 火山方舟 Ark 上的两个模型：
`Seedream`（出图，同步）和 `Seedance`（出视频，异步任务）。本 skill 把鉴权、出图、
出视频、轮询、下载、成本记账都收在一个零依赖脚本里：`scripts/jimeng_api.py`。

**核心原则**：先 `doctor`（免费）→ 再 `--dry-run`（免费）→ 最后真跑；单次花费默认有
10 元上限，超过会拒绝执行。

## 一次性配置（每台新机器）

每个人用自己的 Ark API Key（<https://ark.volcengine.com/region:cn-beijing/apiKey>），
费用记在各自账户。**永远不要把 Key 写进 git、贴在聊天里、或让 Agent 回显。**

1. 交互式保存 Key（推荐，输入不回显、不进 shell 历史、不写仓库）：
   ```bash
   python3 scripts/jimeng_api.py setup
   ```
   它会写到 `~/.config/jimeng/ark_api_key.txt`（权限 600）并自动调接口验证；
   `setup --show-path` 可看路径，换 Key 就再跑一次。
2. 或者用环境变量 / 指定文件（优先级见下）：
   ```bash
   export ARK_API_KEY=ark-xxxxxxxx        # 当前终端
   python3 scripts/jimeng_api.py --key-file /path/to/key.txt doctor
   ```
3. 装可选依赖（只有用本地图片当首帧/参考图时才需要）：
   ```bash
   pip install pillow
   ```
4. 体检（免费，验证 Key + 模型是否已开通）：
   ```bash
   python3 scripts/jimeng_api.py doctor
   ```

**Key 读取优先级**：`--key-file` → `ARK_API_KEY` → `./_secrets/ark_api_key.txt` →
`~/.ark_key` → `~/.config/jimeng/ark_api_key.txt`。

**当用户还没配 Key 时（Agent 必读）**：
- 不要索要 Key 明文，也不要让用户把 Key 发在对话里（会留痕）。
- 请用户在他自己的终端里运行 `python3 scripts/jimeng_api.py setup`，完成后你跑 `doctor` 确认。
- 用户坚持用环境变量时，让他自己 `export`，你不要读取/打印变量值。
- 始终不要在输出、命令回显、README、commit 里出现 Key。

想把 skill 装进本机 agent 技能目录（可选）：
```bash
bash scripts/install_skill.sh        # 链接到 ~/.agents/skills/ 等目录，已存在则跳过
```

## 标准工作流

```
任务进度：
- [ ] 1. doctor 通过（Key 有效、seedream/seedance 已开通）
- [ ] 2. 写提示词（见 reference/prompting.md）
- [ ] 3. 需要人物一致 → 先出首帧图，再图生视频
- [ ] 4. --dry-run 检查请求与预估费用
- [ ] 5. 真跑，确认产物能播放、时长正确
- [ ] 6. 把花费记在 jimeng_cost.jsonl（脚本自动写）
```

### 1) 出图（Seedream，0.12 元/张）

```bash
python3 scripts/jimeng_api.py image \
  --prompt "国风2D漫剧，姜焕在荒原狂奔，黄昏逆光，镜头中景" \
  --out first.jpg --size 1080x1920
```

锁角色/风格（参考图）：

```bash
python3 scripts/jimeng_api.py image --prompt "..." --out shot1.jpg \
  --refs 角色参考.jpg 场景参考.jpg --size 1080x1920
```

`--size` 传 `1K/1.5K/2K` 或 `宽x高`；**竖屏一定显式写 `1080x1920`**，否则 2K 常给横图。

### 2) 出视频（Seedance，异步）

```bash
# 首帧生视频（最稳，推荐）
python3 scripts/jimeng_api.py video \
  --prompt "镜头缓慢推进，姜焕在荒原狂奔，尘土飞扬，衣摆与头发飘动，电影感" \
  --image first.jpg --out shot1.mp4 --resolution 720p --duration 5 --ratio 9:16

# 纯文生视频
python3 scripts/jimeng_api.py video --prompt "..." --out shot2.mp4

# 首尾帧（转场/动作衔接）
python3 scripts/jimeng_api.py video --prompt "..." --image a.jpg --last b.jpg --out shot3.mp4

# 多参考图锁角色（0-9 张）
python3 scripts/jimeng_api.py video --prompt "..." --refs ref1.jpg ref2.jpg --out shot4.mp4
```

省钱路径：`--resolution 480p --duration 4`（fast 模型约 1.48 元/条）→ 满意再上 720p。

### 3) 长任务 / 断线续查

```bash
# 提交后立刻拿 task_id（不阻塞）
python3 scripts/jimeng_api.py video --prompt "..." --out a.mp4 --no-wait

# 之后按 id 续查并下载
python3 scripts/jimeng_api.py task --id <task_id> --out a.mp4
```

### 4) 只检查不花钱

```bash
python3 scripts/jimeng_api.py image --prompt "..." --out a.jpg --dry-run
python3 scripts/jimeng_api.py video --prompt "..." --out a.mp4 --dry-run
```

## 默认值与护栏

| 项 | 默认 | 说明 |
|---|---|---|
| 画面比例 | `9:16` | 竖屏短剧；横屏传 `16:9` |
| 分辨率 | `720p` | 480p 省钱试片；1080p 只有 `vpro` 支持 |
| 时长 | `5s` | Seedance 2.0 只接受 4–15 秒 |
| 音频 | 关 | 漫剧通常自己配音，保持无声 |
| 水印 | 关 | 脚本已显式 `watermark: false` |
| 单次费用上限 | 10 元 | `--max-cost 0` 关闭；超限直接拒绝 |
| 成本账本 | `./jimeng_cost.jsonl` | 可用 `JIMENG_LEDGER` 改路径 |

**硬规则**

- 模型 ID 必须带版本号（脚本已内置），自己拼 ID 会 `404 InvalidEndpointOrModel.NotFound`。
- `--image/--last`（首尾帧）与 `--refs`（多参考图）**互斥**，别混用。
- 出图/出视频的 POST 不自动重试——网络超时重试可能重复计费，需人工确认后再跑。
- 每次真跑前看 stderr 的预估费用；超过 10 元先问用户。
- 别把 Key 写进提示词、命令历史、README 或 commit。

## 出错怎么办

| 现象 | 原因 | 处理 |
|---|---|---|
| `401 AuthenticationError` | Key 错/过期 | 重新生成 Key 放环境变量 |
| `404 InvalidEndpointOrModel.NotFound` | 模型 ID 错/缺版本号 | 用脚本内置别名 |
| `404 ModelNotOpen` | 模型没开通 | 控制台「开通管理」勾选；Seedance 2.0 需余额 > 200 元 |
| `402 Payment Required` | 额度/尺寸受限 | 换 1K/1.5K/2K 或充值 |
| `InvalidParameter` | 参数非法（如 duration=1、首帧+参考图混用） | 按上表改 |
| `429` | 限流 | 等几十秒重跑（GET 查询脚本会自动退避） |
| 视频任务 `failed` | 图片过大/模式冲突/内容审核 | 缩图到 1440 长边、只留一种图片模式、改提示词 |

完整接口、参数、错误码与价格见 [reference/api.md](reference/api.md)。

## 提示词

视频提示词公式、镜头语言、首帧工作流、避坑清单见
[reference/prompting.md](reference/prompting.md)。

## 产物检查

```bash
ffprobe -v error -show_entries format=duration,size -of default=nw=1 out.mp4
```

确认时长接近 `--duration`、能正常播放后再交付；批量生成时逐条记录 `task_id`，
失败任务单独重跑，不要整批重来。
