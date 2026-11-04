# Finance（交易所、钱包与跨境支付）自动分流集合

只维护一条金融规则，包含用户确认的交易所、Web3 钱包和跨境支付/稳定币卡；不包括中国大陆银行、支付宝、微信支付及其它本地银行。

- Clash/Mihomo (classical YAML): https://raw.githubusercontent.com/yinyues2/Clash/main/Finance_No_Resolve.yaml
- iOS Surge: https://raw.githubusercontent.com/yinyues2/surge/main/Finance.list
- Clash 仓库内同步生成 Surge/Finance.list，Surge 仓库按计划镜像发布到原订阅仓库根目录。
- 每天北京时间 03:00 生成（UTC cron 0 19 * * *），Surge 03:20 镜像；支持 Actions 手动运行。

## 收录范围

不收录已经停运或宣布停止运营的交易所。

收录 Binance、OKX、Bybit、Gate、Bitget、MEXC、HTX、KuCoin、BingX、Pionex、Crypto.com；PayPal、RedotPay、Wise、Revolut、Payoneer、Wirex、KAST；imToken、TokenPocket、Trust Wallet、MetaMask、SafePal、OneKey、Phantom、Rabby、TronLink。Binance Wallet、OKX Wallet 和 Bitget Wallet 并入所属交易所。


## 来源、许可及安全边界

平台与审核域名白名单：rules/finance_sources.json。每天从 MetaCubeX/meta-rules-dat 的 cryptocurrency、交易所、钱包、Wise、PayPal 规则，及 blackmatrix7/ios_rule_script 的 Crypto、Binance、PayPal _No_Resolve.yaml 拉取，筛选、去重并生成两个输出。来源见清单。

仅合并审核过的主域名和其子域名；上游其他交易所、相似钓鱼域名、广告 SDK、共享 CDN、银行、第三方身份验证或支付网关、IP 段、ASN、进程规则及 DOMAIN-KEYWORD 均不自动收录。每个服务经过核对的官方主域名作为保底规则。对于只有主域名来源的平台，不承诺 App 的所有第三方请求均能命中；新增跨域后端必须核对归属才能进入白名单。

规则原作者：blackmatrix7 (GPL-2.0) 与 MetaCubeX (GPL-3.0)；版权归原作者。许可证副本见 licenses/ai-sync/GPL-2.0.txt 与 licenses/ai-sync/GPL-3.0.txt。

验证：PYTHONPATH=scripts python -m unittest discover -s tests -p 'test_sync_finance_rules.py' -v ，再运行 python scripts/sync_finance_rules.py 。下载/解析失败、输出不一致、总数或单源异常缩减时停止覆盖，无变化则不提交，提交前检查 main 是否变化。

## 客户端配置

Clash 增加一个 classical rule-provider 指向上述 YAML，并只引用一条 RULE-SET,Finance,你的稳定策略组。Surge 在 [Rule] 里引用 RULE-SET,https://raw.githubusercontent.com/yinyues2/surge/main/Finance.list,你的稳定策略组 。Finance 应在 Global/Final 等兜底规则之前；不要因切换不同国家节点而频繁改变金融 App 出口 IP。两仓库规则不会修改客户端 DNS 或其它策略组，且不能绕过服务的 KYC 和地区限制。
