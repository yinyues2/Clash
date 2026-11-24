# AI 规则上游来源与许可

Clash 和 Surge AI 文件只使用 `rules/ai_sources.json` 中经过审核的上游项目的已核准服务规则，均保留原作者归属、原始上游 URL、许可文本。范围过滤只保留明确匹配点名 AI 的上游条目，不声称原创。

| 项目 | 采用的规则 | 原始许可 | 仓库副本 |
| --- | --- | --- | --- |
| [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) | OpenAI、Claude、Gemini、Copilot、Tencent（WorkBuddy 范围） | [GPL-2.0](https://github.com/blackmatrix7/ios_rule_script/blob/master/LICENSE) | [GPL-2.0.txt](licenses/ai-sync/GPL-2.0.txt) |
| [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) | Anthropic、Google Gemini、xAI、Cursor、GitHub Copilot、Windsurf、国产 AI（WorkBuddy 范围） | [GPL-3.0](https://github.com/MetaCubeX/meta-rules-dat/blob/master/LICENSE) | [GPL-3.0.txt](licenses/ai-sync/GPL-3.0.txt) |
| [VPSDance/ai-proxy-rules](https://github.com/VPSDance/ai-proxy-rules) | Meta AI / Muse、OpenCode | [MIT](https://github.com/VPSDance/ai-proxy-rules/blob/main/LICENSE) | [MIT.txt](licenses/ai-sync/MIT.txt) |

已停止引用 Sukka 综合 AI 源；仓库中若仍存有此前的 AGPL 许可证副本，仅作为历史留存。

WorkBuddy 新增公开域名来源：[stanasischan/surge WorkBuddy](https://github.com/stanasischan/surge/blob/master/rules/WorkBuddy.list)（仅采用域名事实，未发现明确许可）；[geek5nan/rules china_max](https://github.com/geek5nan/rules/blob/main/public/surge/custom/china_max/part-23.list)（仅提取 tencentbuddy.com 域名事实，未发现明确许可）。腾讯公共后缀仅与已审核 WorkBuddy 子域范围相交，不导入整个腾讯域名。国际版来源排除腾讯云通用官网。
