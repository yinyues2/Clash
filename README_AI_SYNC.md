# AI 规则自动同步

本仓库通过 GitHub Actions 定期汇总 AI 上游规则和本地自定义规则，生成 `AI_No_Resolve.yaml`。现有规则订阅地址保持不变：

```text
https://raw.githubusercontent.com/yinyues2/Clash/main/AI_No_Resolve.yaml
```

该文件供 Clash / Mihomo 的 `behavior: classical` 规则集使用。GitHub 更新文件后，客户端仍按自己的规则集刷新周期拉取；需要立即使用新规则时，可在客户端手动更新规则集。

## 运行时间与触发方式

- **每天北京时间 08:17**：工作流使用 UTC cron `17 0 * * *`。
- **手动运行**：打开仓库 **Actions → Sync AI rules → Run workflow**，选择 `main`。
- **修改同步配置后自动运行**：向 `main` 推送上游清单、自定义规则、同步脚本、依赖、测试或该工作流的改动时触发。

仅修改 `AI_No_Resolve.yaml` 或本文档不会触发同步，避免输出文件反复触发生成。手动选择其他分支时，发布任务会跳过。定时触发还要求工作流位于仓库默认分支；此仓库的同步目标固定为 `main`。

GitHub 的定时任务可能排队延迟，并不是精确到分钟的定时服务。**公共仓库连续 60 天没有活动时，GitHub 会自动停用定时工作流**；上游长期无变化、仓库也没有其他活动时，应留意这一限制。可在 Actions 中重新启用该工作流，再手动运行一次。此方案不会制造空提交来保活。参见 [GitHub 定时工作流说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。

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

自定义规则应写入 `rules/ai_custom.yaml`，不要只写进生成结果；下次同步会根据输入重新生成输出。修改来源时，以现有清单结构和脚本支持的规则格式为准，不要把代理节点订阅当作规则集。

当前自动来源为 blackmatrix7 的 OpenAI、Claude、Gemini、Copilot 四份 `_No_Resolve.yaml`。Grok、Meta AI 和原有 Gemini 扩展规则等手工补充保留在 `rules/ai_custom.yaml`。迁移时仅从原有条目中移除了由当前上游精确提供的重复项；首次合并得到 127 条唯一规则，保留了原文件的全部 101 条。

当前验证器支持这些输入实际使用的 `DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`、`IP-CIDR`、`IP-CIDR6`、`IP-ASN`。若上游以后引入其他类型，会停止并保留旧文件，待补齐相应的正确验证后再接纳，不会跳过未知规则后发布残缺结果。

这是规则集合的汇总，不会在客户端创建多个 AI 策略组。Copilot 来源指微软/Bing Copilot 相关集合，并含部分共享服务地址，不是 GitHub Copilot 专用表。

## 每次运行会做什么

1. 检出最新 `main`，使用 Python 3.13 安装依赖。
2. 运行单元测试；测试失败则停止。
3. 执行 `python scripts/sync_ai_rules.py`，下载并严格校验所有输入，去重后按确定顺序生成规则；IP 规则携带 `no-resolve`。
4. 仅当 `AI_No_Resolve.yaml` 的内容发生变化时，以 `github-actions[bot]` 身份提交这一个文件。
5. 确认生成期间 `main` 没有前进后，使用普通 Git push 写回 `main`。

输出不包含为了制造变化而加入的运行时间戳；相同输入生成相同内容，没有变化就不会提交。任一来源下载、解析或校验失败时，本次同步失败，不发布部分成功的结果，也不会覆盖已发布的规则文件。

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
git diff -- AI_No_Resolve.yaml
```

最后一条命令用于查看输出变化。同步脚本本身不会执行 Git 提交或推送。

## 排查常见情况

| 现象 | 处理方式 |
| --- | --- |
| 任务成功，但没有新提交 | 查看日志或运行摘要；上游与自定义规则没有导致输出变化时，这是正常结果。 |
| 上游下载或解析失败 | 在失败步骤中确认具体来源，修复 `rules/ai_sources.json` 或等待上游恢复，然后手动重跑。已发布文件保持原样。 |
| 提示 `main changed` 或 push 被拒绝 | 检查是否有并发提交，直接重新运行以使用最新 `main`；不需要强推。 |
| 报权限或分支保护错误 | 核查仓库/组织策略和保护规则，按现有权限流程处理。 |
| 到点没有运行记录 | 确认工作流已在默认分支启用、未因 60 天无活动被停用，并考虑 GitHub 排队延迟。 |
| GitHub 已更新，Clash 中规则还没变 | 手动刷新该规则集，并检查客户端规则下载日志；GitHub 定时同步和客户端刷新是两个独立周期。 |
