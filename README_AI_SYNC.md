# AI 规则自动同步

本仓库通过 GitHub Actions 定期汇总 AI 上游规则和本地自定义规则，从同一份规范化清单生成 `AI_No_Resolve.yaml` 与 `Surge/AI.list`。客户端继续只需一个 AI 规则集、一个 AI 策略组。Clash 现有规则订阅地址保持不变：

```text
https://raw.githubusercontent.com/yinyues2/Clash/main/AI_No_Resolve.yaml
```

该文件供 Clash / Mihomo 的 `behavior: classical`、`format: yaml` 规则集使用。Surge 沿用正在使用的原订阅地址：

```text
https://raw.githubusercontent.com/yinyues2/surge/main/AI.list
```

本仓库的 `Surge/AI.list` 是生成产物，由 [yinyues2/surge](https://github.com/yinyues2/surge) 的同步工作流校验并发布到根目录 `AI.list`，无需更换客户端已有的 Surge 订阅链接。

GitHub 更新文件后，客户端仍按自己的规则集刷新周期拉取；需要立即使用新规则时，可在客户端手动更新规则集。

## 运行时间与触发方式

- **每天北京时间 01:00**：GitHub 工作流使用 UTC cron `0 17 * * *`，拉取、合并并提交两种格式。
- **每天北京时间 01:20**：`yinyues2/surge` 的镜像工作流读取本仓库生成结果，校验 Clash/Surge 规则集合一致、检查异常减少后，更新原地址的 `AI.list`。两仓库各使用自己的 GitHub Token，不需要跨仓库 PAT。
- **每天北京时间 02:00**：另外配置的 ChatGPT 计划任务检查两个仓库的工作流及规则，确认 Surge 原地址已同步，必要时在既有授权范围内补救。该检查任务不在本仓库运行。
- **手动运行**：打开仓库 **Actions → Sync AI rules → Run workflow**，选择 `main`。
- **修改同步配置后自动运行**：向 `main` 推送上游清单、自定义规则、同步脚本、依赖、测试或该工作流的改动时触发。

仅修改 `AI_No_Resolve.yaml`、`Surge/AI.list` 或本文档不会触发同步，避免输出文件反复触发生成。手动选择其他分支时，发布任务会跳过。定时触发还要求工作流位于仓库默认分支；此仓库的同步目标固定为 `main`。

GitHub 的定时任务可能排队延迟，并不是精确到分钟的定时服务。**公共仓库连续 60 天没有活动时，GitHub 会自动停用定时工作流**；上游长期无变化、仓库也没有其他活动时，应留意这一限制。可在 Actions 中重新启用该工作流，再手动运行一次。此方案不会制造空提交来保活。参见 [GitHub 定时工作流说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。

ChatGPT 检查任务正常成功时静默；遇到无法安全修复、需要处理权限或连接的问题时，在原聊天中说明失败环节、旧规则是否保留、运行链接和需要处理的一步。可在 **Scheduled（计划任务）** 查看任务与运行记录。网页端 **Settings → Notifications → Manage tasks** 可进入任务管理；推送、邮件等渠道依账号和设置而定，本仓库不配置邮箱或推送服务。参见 [ChatGPT 计划任务](https://learn.chatgpt.com/docs/automations) 与 [通知设置](https://learn.chatgpt.com/docs/notifications)。

## 日常维护改哪里

| 文件 | 用途 | 是否手动编辑 |
| --- | --- | --- |
| `rules/ai_sources.json` | 要同步的上游规则来源及其配置 | 是，增加或移除上游时修改 |
| `rules/ai_custom.yaml` | 需要长期保留的自定义 AI 规则 | 是，补充自己的规则时修改 |
| `scripts/sync_ai_rules.py` | 下载、校验、合并、去重和生成逻辑 | 仅修改同步行为时编辑 |
| `requirements-ai-sync.txt` | 同步脚本的 Python 依赖 | 更新依赖时修改 |
| `tests/test_sync_ai_rules.py` | 同步与异常处理的单元测试 | 修改生成逻辑时同步维护 |
| `.github/workflows/sync-ai-rules.yml` | 定时、测试及提交流程 | 修改调度或运行环境时编辑 |
| `AI_No_Resolve.yaml` | 对外提供的生成结果 | 通常不直接编辑 |
| `Surge/AI.list` | 同一集合的 Surge 纯文本结果 | 通常不直接编辑 |

自定义规则应写入 `rules/ai_custom.yaml`，不要只写进生成结果；下次同步会根据输入重新生成输出。修改来源时，以现有清单结构和脚本支持的规则格式为准，不要把代理节点订阅当作规则集。

## 上游与覆盖（仅限已确认的 AI 服务）

2026-11-04 根据明确使用名单，改为 **12 份独立上游**、三个项目，继续仅使用一个 AI 策略组。

| 上游 | 规则 | 涵盖的目标服务 |
| --- | --- | --- |
| [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) | OpenAI、Claude、Gemini、Copilot 的 `_No_Resolve.yaml` | ChatGPT / Codex / Images、Claude / Claude Code、Gemini、微软 Copilot |
| [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) | Anthropic、Google Gemini、xAI、Cursor、GitHub Copilot、Windsurf | Claude、Gemini / Nano Banana / AI Studio、Grok、Antigravity、Jules、Veo/Flow、AI 编程 |
| [VPSDance/ai-proxy-rules](https://github.com/VPSDance/ai-proxy-rules) | Meta AI、OpenCode 专用文本 | Meta AI / Muse（包括 `muse.ai`）、OpenCode |

现有自动源清单由 [`rules/ai_sources.json`](rules/ai_sources.json) 管理；未使用 Sukka 的宽泛 AI 合集、Perplexity、Poe、ElevenLabs、Hugging Face、Manus 等不需要的规则源。

**无手动规则：** `rules/ai_custom.yaml` 目前为 `payload: []`。原来自己维护的 Meta AI / Muse 主域名现在由第三方专用源维护；Grok 主域名由 MetaCubeX 的 xAI 源维护。原手写的 Google Analytics、广告、共享 CDN、YouTube 图片、Apple IP 等条目并非专属 AI 请求，未混入本组。

**精确范围：** 各上游原文件可能夹带无关应用或泛域名。为确保只收录点名的服务，部分来源设置 `include_domains`（上游条目选择边界，不会凭空造新规则），并设置 `required_domains` 核对核心入口。通用 CDN、宽泛 ASN、Google NotebookLM、Opal、Stitch、Grokipedia 等均被排除；新根域名需要审核才扩大范围，已允许域下新增的上游规则会自动收录。

**完整性边界：** 可检查主站和主要 API 的覆盖，无法从静态规则承诺所有登录验证、安装更新、跨厂商模型 API 100% 命中。特别是 OpenCode 使用未列入的模型提供商时，这些请求会按正常分流走 `Final`，不会自动并入 AI。需要补充时，应先核对真实访问与可靠上游，不把整个公共网络服务误归类为 AI。

初次精简从 233 条减少到约 109 条，主要是移除不使用的产品及共享域名，不是丢失已确认主站。只在此次审核过的基线迁移允许明确的数量收缩；后续继续执行异常骤减保护、完整校验、双格式一致性和无变化不提交。IP 类型若未来确由已核准上游提供，仍由脚本规范化为带 `no-resolve` 的条目。

## Surge 引用与格式

在 Surge 的 `[Rule]` 中引用：

```ini
RULE-SET,https://raw.githubusercontent.com/yinyues2/surge/main/AI.list,AI,no-resolve
```

`AI` 指自己的已有策略/策略组，按实际名称替换，并保留原有规则优先级。外部文件为纯文本，每行一条规则，不含 `payload:`、YAML 列表前缀或策略目标。IPv6 保留 `IP-CIDR6`，ASN 使用 `IP-ASN`，IP 类规则统一保留一个 `no-resolve`。参见 [Surge RULE-SET](https://manual.nssurge.com/rules/ruleset.html) 和 [IP 规则](https://manual.nssurge.com/rules/ip.html)。

Clash 已有的 AI provider 继续使用原 YAML 地址与 `classical` 格式即可；无需拆成多条产品分流规则。此同步功能不修改客户端 DNS 或其他策略组。

## 每次运行会做什么

1. 检出最新 `main`，使用 Python 3.13 安装依赖。
2. 运行单元测试；测试失败则停止。
3. 执行 `python scripts/sync_ai_rules.py`，下载并严格校验所有输入，去重后生成两种格式，并验证两者规则集合完全相同；IP 规则携带 `no-resolve`。
4. 仅当输出内容发生变化时，以 `github-actions[bot]` 身份将 `AI_No_Resolve.yaml` 与 `Surge/AI.list` 的变更放入同一次提交。
5. 确认生成期间 `main` 没有前进后，使用普通 Git push 写回 `main`。

输出不包含为了制造变化而加入的运行时间戳；相同输入生成相同内容，没有变化就不会提交。任一来源下载、解析或校验失败时，本次同步失败，不发布部分成功的结果，也不会覆盖已发布的规则文件。

脚本先校验全部输入并准备两份内容，再替换本地文件；逐个替换不是跨文件的文件系统事务。对外版本一致性由**脚本成功后同一次 Git 提交**保证。任何生成步骤失败，后续提交步骤都不会执行，GitHub 已发布版本不变。

每个远程源必须有非空规则。总规则数量减少超过 20%，或单个源减少至少 10 条且超过其原有数量的 25% 时，同步会停止并要求核对。只有确认上游进行了合理的大规模清理后，才在本地使用 `python scripts/sync_ai_rules.py --allow-large-removal` 接受该变化；日常工作流不使用这个覆盖选项。自定义文件可以明确写成 `payload: []`，但不能缺失。

同一同步工作流采用串行运行，并保留正在运行的任务。人工或其他工作流仍可能同时更新 `main`：若检测到分支已经变化，或最终 push 因竞争被拒绝，本次任务会失败，重新运行即可。它不会强制推送，也不会把基于旧输入生成的结果自动变基后覆盖新提交。

## 权限与运行限制

工作流使用 GitHub 自动提供的 `GITHUB_TOKEN`，只给发布任务授予本仓库所需的 `contents: write`，**正常情况下无需创建 PAT，也无需添加额外 Secrets**。参见 [GitHub Token 权限说明](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)。

组织策略、仓库权限或主分支保护如果禁止直接写入，提交步骤会正常失败。工作流不会修改这些设置；应按仓库现有策略处理权限，或将发布流程调整为经过审查的 Pull Request。

整个任务最长运行 15 分钟，提交步骤最长 3 分钟；依赖安装使用有限重试，单次请求超时为 30 秒。上游下载的超时和重试由同步脚本控制，失败会保留现有输出，等待下一次定时或手动运行。

官方 Actions 已固定到完整提交 SHA，版本注释为 [checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) 和 [setup-python v7.1.0](https://github.com/actions/setup-python/releases/tag/v7.1.0)。后续更新应先核实对应官方发布的 SHA，再修改工作流。

## 在本地验证

使用 Python 3.13，建议在虚拟环境中安装依赖。在仓库根目录运行：

```bash
python -m pip install -r requirements-ai-sync.txt
python -m unittest discover -s tests -p 'test_sync_ai_rules.py' -v
python scripts/sync_ai_rules.py
git diff -- AI_No_Resolve.yaml Surge/AI.list
```

最后一条命令用于查看输出变化。同步脚本本身不会执行 Git 提交或推送。

离线复核可传 `--source-dir`，其中按来源名称保存 `<name>.yaml` 或 `<name>.txt` 快照。

## 排查常见情况

| 现象 | 处理方式 |
| --- | --- |
| 任务成功，但没有新提交 | 查看日志或运行摘要；上游与自定义规则没有导致输出变化时，这是正常结果。 |
| 上游下载或解析失败 | 在失败步骤中确认具体来源，修复 `rules/ai_sources.json` 或等待上游恢复，然后手动重跑。已发布文件保持原样。 |
| 提示 `main changed` 或 push 被拒绝 | 检查是否有并发提交，直接重新运行以使用最新 `main`；不需要强推。 |
| 报权限或分支保护错误 | 核查仓库/组织策略和保护规则，按现有权限流程处理。 |
| 到点没有运行记录 | 确认工作流已在默认分支启用、未因 60 天无活动被停用，并考虑 GitHub 排队延迟。 |
| GitHub 已更新，Clash 中规则还没变 | 手动刷新该规则集，并检查客户端规则下载日志；GitHub 定时同步和客户端刷新是两个独立周期。 |
