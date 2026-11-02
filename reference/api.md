# 火山方舟 Ark API 参考（即梦同源模型）

> 2026-10 / 已实测。价格与模型 ID 会变，跑之前先看控制台。
> 控制台：<https://console.volcengine.com/ark> ｜ Key：<https://ark.volcengine.com/region:cn-beijing/apiKey>
> 文档索引（URL 后加 `.md` 可得 Markdown 原文）：<https://ark.volcengine.com/llms.txt>

## 1. 两个接口

| 用途 | 方法 | 路径 | 同步性 |
|---|---|---|---|
| 出图（Seedream） | POST | `/api/v3/images/generations` | 同步，直接返回图片 URL |
| 出视频（Seedance） | POST | `/api/v3/contents/generations/tasks` | 异步，返回 task id |
| 查视频任务 | GET | `/api/v3/contents/generations/tasks/{id}` | 轮询直到 `succeeded` |
| 列模型 | GET | `/api/v3/models` | 用于体检/确认模型 ID |

- 国内 Base：`https://ark.cn-beijing.volces.com/api/v3`
- 海外（BytePlus / Dreamina）：`https://ark.ap-southeast.bytepluses.com/api/v3`，接口同构，需 BytePlus 账号
- 鉴权：`Authorization: Bearer $ARK_API_KEY`，`Content-Type: application/json`

## 2. 模型 ID（必须带版本号）

| 别名 | 模型 ID | 用途 | 价格 |
|---|---|---|---|
| `flash` | `doubao-seedream-5-0-flash-260915` | 出图 | 0.12 元/张（1K/1.5K/2K） |
| `pro` | `doubao-seedream-5-0-pro-260628` | 出图（更精细） | 0.30 元/张起，2K 约 0.60 |
| `fast` | `doubao-seedance-2-0-fast-260128` | 出视频，最常用 | 480p 0.37、720p 0.80 元/秒 |
| `vpro` | `doubao-seedance-2-0-260128` | 出视频，高清 | 480p 0.46、720p 0.99、1080p 2.48 元/秒 |
| `mini` | `doubao-seedance-2-0-mini-260615` | 出视频，最便宜 | 480p 0.23、720p 0.50 元/秒 |

不开通会返回 `404 ModelNotOpen`。**Seedance 2.0 系列要求账户余额 > 200 元**
（或买 200 元资源包）；Seedream 需在「开通管理 → 图片生成」勾选。

## 3. 出图参数

```json
POST /api/v3/images/generations
{
  "model": "doubao-seedream-5-0-flash-260915",
  "prompt": "国风2D漫剧，荒原黄昏，人物中景，电影感",
  "size": "1080x1920",
  "output_format": "jpeg",
  "response_format": "url",
  "watermark": false,
  "image": ["data:image/jpeg;base64,..."]
}
```

| 字段 | 说明 |
|---|---|
| `size` | `1K` / `1.5K` / `2K` 或 `宽x高`。**2K 默认可能出横图**，竖屏要显式 `1080x1920`（或 `1440x2560`） |
| `image` | 参考图数组（锁角色/风格）。本地图转 data URI，或公网 URL；≤30MB/张 |
| `response_format` | 固定 `url`（脚本会下载到 `--out`） |
| `watermark` | 显式 `false`，否则可能带平台水印 |
| `output_format` | `jpeg` / `png` |

响应：`{"data": [{"url": "https://..."}]}`。

## 4. 出视频参数

```json
POST /api/v3/contents/generations/tasks
{
  "model": "doubao-seedance-2-0-fast-260128",
  "content": [
    {"type": "text", "text": "镜头缓慢推进，人物在荒原狂奔"},
    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}, "role": "first_frame"}
  ],
  "resolution": "720p",
  "ratio": "9:16",
  "duration": 5,
  "seed": 42,
  "generate_audio": false,
  "watermark": false
}
```

| 字段 | 取值 | 坑 |
|---|---|---|
| `content` | `text` + 0~2 张帧图（`first_frame` / `last_frame`）或 0-9 张 `reference_image` | 首尾帧与多参考图**互斥** |
| `resolution` | `480p` / `720p` / `1080p` | 1080p 仅 `vpro`；fast 只有 480/720 |
| `ratio` | `9:16` / `16:9` / `1:1` / `4:3` / `3:4` / `adaptive` | 不传默认 16:9 |
| `duration` | 4–15 秒（整数） | 传 1 → `InvalidParameter` |
| `seed` | 整数，`-1` 随机 | 复现同一镜头时固定 |
| `generate_audio` | 布尔 | 漫剧一般 `false`，自行配音 |
| `watermark` | 布尔 | 显式 `false` |

响应：`{"id": "cgt-2026..."}`。轮询：

```
GET /api/v3/contents/generations/tasks/{id}
→ {"status": "queued|running|succeeded|failed|cancelled",
   "content": {"video_url": "https://..."},
   "usage": {"completion_tokens": 123456}}
```

`failed` 时看 `error.code/message`；常见于内容审核不通过、输入图过大、图片模式混用。

## 5. 常见错误码

| 错误码 | 含义 | 处理 |
|---|---|---|
| `401 AuthenticationError` | Key 错/过期/没带 Bearer | 重新生成 Key |
| `403 AccessDenied` | 未实名/未开通/无权限 | 控制台完成实名与开通 |
| `404 InvalidEndpointOrModel.NotFound` | 模型 ID 错（多半缺版本号） | 用第 2 节的完整 ID |
| `404 ModelNotOpen` | 模型没开通 | 「开通管理」勾选 |
| `402 Payment Required` | 免费额度/尺寸受限/欠费 | 换尺寸或充值 |
| `InvalidParameter` | 参数非法 | 对照第 3/4 节 |
| `SetLimitExceeded ... Safe Experience Mode` | 开着「安心体验模式」 | 关闭（需实名 + 余额 > 200） |
| `429` | 限流 | 等几十秒；查询接口可指数退避 |

## 6. 成本护栏

```
doctor（免费）→ --dry-run（免费）→ 1 张图 0.12 → 1 条 480p/4s 1.48
→ 满意再 720p → 逐条记 jimeng_cost.jsonl
```

价格随时可能调整，做预算前先核对控制台价目表；脚本的 `--max-cost`（默认 10 元）
只是兜底，不是报价。

## 7. 安全

- Key 只放本地（环境变量 / `_secrets/ark_api_key.txt` / `--key-file`），**不要提交 git**。
- 本仓库 `.gitignore` 已忽略 `_secrets/`、`*.mp4`、`*.jpg`、`jimeng_cost.jsonl`。
- 给别人用：给脚本 + 让对方自己申请 Key，不要共享 Key。
- 定期在控制台轮换 Key。
