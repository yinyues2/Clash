# AI 规则上游来源与许可

`AI_No_Resolve.yaml` 与 `Surge/AI.list` 汇总以下项目公开发布的规则数据。各来源作者及贡献者保留其原有权利；来源的许可文本随仓库保留，原项目说明和依赖的规则来源请见对应仓库。

| 原项目 | 本仓库使用范围 | 上游许可原文 | 本地原文副本 |
| --- | --- | --- | --- |
| [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) | OpenAI、Claude、Gemini、Copilot | [GPL-2.0](https://github.com/blackmatrix7/ios_rule_script/blob/master/LICENSE) | [GPL-2.0.txt](licenses/ai-sync/GPL-2.0.txt) |
| [SukkaW/Surge](https://github.com/SukkaW/Surge)，Sukka 及贡献者 | 发布的 Mihomo AI classical 文本 | [AGPL-3.0](https://github.com/SukkaW/Surge/blob/master/LICENSE) | [AGPL-3.0.txt](licenses/ai-sync/AGPL-3.0.txt) |
| [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) 及其规则上游贡献者 | 清单中列出的十份独立 AI classical 列表 | [GPL-3.0](https://github.com/MetaCubeX/meta-rules-dat/blob/master/LICENSE) | [GPL-3.0.txt](licenses/ai-sync/GPL-3.0.txt) |

来源清单及下载 URL 见 [`rules/ai_sources.json`](rules/ai_sources.json)。生成文件按来源标记；重复条目仅保留首次出现的位置，并不表示排除其他来源对相同条目的贡献。

本仓库对规则进行格式校验、IP 规范化、添加 `no-resolve`、精确去重和 Clash / Surge 格式转换。所有转换代码和手工补充均随仓库公开。没有将上游规则标记为本仓库原创，也没有为仓库其他既有文件改写许可声明。
