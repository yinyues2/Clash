# Google 全家桶规则每日同步

本项目只发布**一条 Google 集合规则**，覆盖 Google 常规产品和 YouTube 全家桶（包含 YouTube Music）。独立的 Google AI / Gemini 已由排在前面的 AI 规则处理。规则来源是第三方维护的集合，不是逐项手写软件域名名单。

## 原仓库中使用的新订阅链接

Clash / Mihomo，`behavior: classical`：

```text
https://raw.githubusercontent.com/yinyues2/Clash/main/Google_No_Resolve.yaml
```

Surge（独立仓库镜像的原生文本）：

```text
https://raw.githubusercontent.com/yinyues2/surge/main/Google.list
```

Clash 策略组名称、rules 的排列顺序、`path` 和 `interval` 不必改，只需将 Google rule-provider 的 `url` 切到上述自己的仓库。**继续让 AI 优先于 Google。** 单独的 AI 专用域名从 Google 生成规则中排除；`DOMAIN-KEYWORD,google`、`DOMAIN-SUFFIX,google.com` 和 `DOMAIN-SUFFIX,googleapis.com` 属于通用 Google 匹配项，无法仅凭域名静态规则保证 AI 请求完全无重叠，必须依赖 AI 优先匹配。不要把 Google 放到 AI 前面。

## 维护方式

- 每天北京时间 **01:30**：Clash 仓库 GitHub Actions `Sync Google rules` 获取上游、验证和合并，生成 `Google_No_Resolve.yaml` 与 `Surge/Google.list`，如有变化才提交。
- 每天北京时间 **01:50**：Surge 仓库 `Sync Google rules` 读取上述输出，检查两端规则一致性，镜像到原生的 `surge/main/Google.list`。
- 手动触发：打开两个仓库各自的 Actions → Sync Google rules → Run workflow，先 Clash 后 Surge。
- GitHub `schedule` 可能排队或延迟，非严格准点；公共仓库连续 60 天没有活动时，定时 workflow 也可能被自动停用，应在 Actions 查看并重新启用。
- GitHub Actions 的运行记录用于确认同步状态；**目前没有专门为 Google 规则新增 ChatGPT 02:00 自动检查提醒**。

## 汇总上游

`rules/google_sources.json` 中的 9 个可靠来源是：

| 上游 | 内容 |
| --- | --- |
| blackmatrix7/ios_rule_script | Google 通用、YouTube、YouTubeMusic、GoogleDrive、GoogleEarth、GoogleFCM、GoogleSearch、GoogleVoice |
| MetaCubeX/meta-rules-dat | google geosite classical 补充规则 |

所有输入保留来源 URL 和分组注释，去掉完全重复项、操作系统进程名和跨客户端不兼容的正则规则；IP 网段自动带 `no-resolve`。Google 系统推送 FCM 的 IP 地址规则也包括在内。每次运行检查 YAML、文本格式、核心服务域名以及两格式规则一致性。**若任何来源获取失败、格式错误、总条数减少超过 20% 或某个较大上游减少超过 25%，立即停止发布、保留上一版本。** 这样避免一次错误下载破坏正常代理。

Google 集合不保证能自动收录未来所有新产品的专有域名；如出现全新域名且上游均未收录，需先更新上游来源或经审核补充。没有使用 Google/YouTube 的整个 AS 编号做代理，以免误匹配其他流量。

## 开源许可与归属

规则源仍属于原作者，非本仓库原创：

- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)，GPL-2.0，[原始许可证](https://github.com/blackmatrix7/ios_rule_script/blob/master/LICENSE)，[仓库中已有许可证副本](licenses/ai-sync/GPL-2.0.txt)
- [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat)，GPL-3.0，[原始许可证](https://github.com/MetaCubeX/meta-rules-dat/blob/meta/LICENSE)，[仓库中已有许可证副本](licenses/ai-sync/GPL-3.0.txt)

此自动化不会编辑既有 AI 规则文件、AI 源清单、DNS 设置或客户端策略组。
