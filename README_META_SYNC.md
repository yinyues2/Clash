# Meta 全家桶每日同步（Meta AI 除外）

本项目发布**一条 Meta 非 AI 集合规则**，覆盖 Facebook（含 Reels、Marketplace、Business / Ads）、Instagram、WhatsApp、Messenger、Threads、Meta Quest / Oculus、Meta Horizon、Meta 账号及支持服务，并包含通用 Meta 企业域名、开发者平台和网络资源。新域名覆盖率由持续更新的上游规则决定。

## 订阅地址

Clash / Mihomo（`behavior: classical`）：

```text
https://raw.githubusercontent.com/yinyues2/Clash/main/Meta_No_Resolve.yaml
```

Surge（原生文本）：

```text
https://raw.githubusercontent.com/yinyues2/surge/main/Meta.list
```

在 Clash Verge 的建议匹配优先级：**AI → Google → Meta → 其他分流规则**，具体还应保留原配置中必须更早执行的局域网 / DIRECT 特例。

## 排除 Meta AI

以下明确的 AI 专用根域名及其子域名排除在 Meta 生成规则外：

- `meta.ai`、`metaaiusercontent.com`、`metaaivm.com`
- `llama.com`、`llamameta.net`、`muse.ai`
- 已知 AI 专用子域名 `ai.meta.com`、`aidemos.meta.com`、`ai.developer.meta.com`、`llama.developer.meta.com`

通用企业域名 `meta.com`、`atmeta.com` 及部分共享 IP 不能在域名/IP 级别完美区分 AI 与非 AI。现有 AI 规则也收录 `atmeta.com` 和部分 Meta 子域名，因此应由优先级更高的 AI 规则先命中；请勿把 Meta 置于 AI 之前。此工作流不改变现有 AI、Google 规则。

## GitHub Actions

- 北京时间 **02:10**（前一天 UTC 18:10）：Clash 仓库自动抓取 9 个上游，去重、过滤 Meta AI、校验并生成 `Meta_No_Resolve.yaml` 和 `Surge/Meta.list`。
- 北京时间 **02:30**（前一天 UTC 18:30）：Surge 仓库从 Clash 读取已验证的输出，核对两种格式，然后更新 `Meta.list`。
- 手动运行：两个仓库各自进入 Actions → Sync Meta rules → Run workflow，先 Clash 后 Surge。
- GitHub schedule 不保证准点；如定时任务停止，需在 Actions 中重新启用。没有新建独立的 ChatGPT 定时检查任务。

## 上游、校验和异常保护

使用 [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) 的 meta、facebook、instagram、whatsapp、messenger、threads、oculus geosite/classical 源，及 [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) 的 Facebook、Instagram Clash 规则。来源记录在 `rules/meta_sources.json` 中；新的品牌 / 产品域名将随上游收录而自动合入。

规则仅允许跨客户端兼容的 classical 类型，过滤进程名和正则，所有 IP 类规则使用 `no-resolve`，去除重复并保留来源注释。发布前检查 YAML、Surge 文本一致性、7 项核心域名、至少 500 条规则；如任何源失败、上版总数减少超过 20%、或较大单源减少超过 25%，保留上一版不提交。

只依赖静态域名 / IP 规则，无法确保 Meta AI 所有内嵌功能与共享后台完全隔离。IP 匹配也可能包含共享基础设施。

## 开源许可证

- blackmatrix7/ios_rule_script：GPL-2.0（[原始许可证](https://github.com/blackmatrix7/ios_rule_script/blob/master/LICENSE)）
- MetaCubeX/meta-rules-dat：GPL-3.0（[原始许可证](https://github.com/MetaCubeX/meta-rules-dat/blob/meta/LICENSE)）

相关许可证文本已在 Clash 仓库的 `licenses/ai-sync/` 中存档。
