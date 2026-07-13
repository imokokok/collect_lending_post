"""配置文件"""

# ============ 搜索关键词 ============
# 围绕借贷协议风险管理场景设计
# 目标是找到正在讨论清算、健康因子、仓位管理、杠杆策略的帖子

# 1) 借贷协议名称
PROTOCOL_KEYWORDS = [
    "Aave",
    "Compound",
    "MakerDAO",
    "Spark",
    "Morpho",
    "Radiant",
    "Venus",
    "JustLend",
    "Benqi",
    "Curve",
    "crvUSD",
    "Euler",
    "Silo",
    "Ajna",
    "Kamino",
    "Solend",
]

# 2) 风险管理 / 清算 / 健康因子（高价值获客场景）
RISK_KEYWORDS = [
    "liquidation",
    "清算",
    "health factor",
    "HF",
    "健康因子",
    "健康度",
    "collateral ratio",
    "抵押率",
    "LTV",
    "liquidation price",
    "清算价格",
    "爆仓",
    "被清算",
    "清算风险",
    "风险管理",
    "risk management",
    "仓位安全",
    "position management",
    "仓位管理",
    "借贷监控",
    "自动平仓",
    "自动保护",
    "safety",
]

# 3) 预言机 / 价格 / 坏账（你的工具核心差异点）
ORACLE_KEYWORDS = [
    "oracle",
    "预言机",
    "oracle manipulation",
    "price oracle",
    "喂价",
    "价格偏差",
    "bad debt",
    "坏账",
    "insolvency",
]

# 4) 用户行为 / 策略讨论（潜在需求场景）
STRATEGY_KEYWORDS = [
    "leverage",
    "杠杆",
    "去杠杆",
    "deleverage",
    "borrowing",
    "借款",
    "贷款",
    "lending strategy",
    "借贷策略",
    "循环贷",
    "杠杆挖矿",
    "yield farming",
    "挖矿",
    "stablecoin",
    "USDC",
    "USDT",
    "DAI",
    "ETH collateral",
    "WBTC collateral",
    "闪电贷",
]

# 5) MEV / OEV（预言机可提取价值，和借贷清算强相关）
MEV_OEV_KEYWORDS = [
    "MEV",
    "OEV",
    "oracle extractable value",
    "Oracle MEV",
    "预言机套利",
    "清算套利",
    "liquidation bot",
    "liquidation bots",
    "searcher",
    "searchers",
    "flashbots",
    "builder",
    "block builder",
    "mev blocker",
    "MEVBlocker",
    "cow protocol",
    "intent",
    "preconfirmation",
]

# 6) 中文泛 DeFi 讨论词
CHINESE_KEYWORDS = [
    "DeFi借贷",
    "抵押借贷",
    "链上借贷",
    "稳定币借贷",
    "借贷协议",
]

# 聚合所有关键词（去重）
KEYWORDS = list(dict.fromkeys(
    PROTOCOL_KEYWORDS + RISK_KEYWORDS + ORACLE_KEYWORDS + STRATEGY_KEYWORDS + MEV_OEV_KEYWORDS + CHINESE_KEYWORDS
))

# ============ 高价值场景词（用于相关性打分） ============
HIGH_INTENT_KEYWORDS = [
    "liquidation", "清算", "health factor", "健康因子", "健康度",
    "爆仓", "被清算", "清算价格", "清算风险", "爆仓价",
    "collateral", "抵押", "LTV", "HF ", " HF",
    "oracle", "预言机", "价格偏差", "bad debt", "坏账",
    "position", "仓位", "风险管理", "自动平仓", "自动保护",
    "MEV", "OEV", "oracle extractable value", "预言机套利", "清算套利",
    "liquidation bot", "searcher", "flashbots", "block builder", "mev blocker",
]

# ============ X (Twitter) 关注账号 ============
# 使用 Syndication API 获取这些账号的最新推文（免费，无需 API Key）
X_ACCOUNTS = [
    # 主流借贷协议官方
    "Aave",
    "compoundfinance",
    "MakerDAO",
    "VenusProtocol",
    "SparkProtocol",
    "morpholabs",
    "RDNTCapital",
    "CurveFinance",
    "SiloFinance",

    # 风险管理 / 安全
    "HypernativeHQ",
    "ChaosLabs",
    "Gauntlet_Network",
    "LlamaRisk",
    "BlockAnalitica",

    # MEV / OEV / 预言机生态
    "Flashbots",
    "libevm",
    "EigenPhi",
    "FlashbotsProtect",
    "MEVBlocker",
    "MEVwatch",
    "RelayScan",
    "RedstoneOracles",
    "API3DAO",
    "PythNetwork",
    "Chainlink",
    "UMAprotocol",

    # 链上数据 / 中文社区
    "Lookonchain",
    "Wublockchain12",
    "Defi_Mochi",
    "DeFi_Cheetah",
]

# ============ 币安广场搜索关键词 ============
# 币安广场以中文讨论为主，关键词更贴近中文社区表达习惯
BINANCE_PRIORITY_KEYWORDS = [
    "Aave",
    "Compound",
    "清算",
    "爆仓",
    "健康因子",
    "健康度",
    "抵押率",
    "借贷协议",
    "DeFi借贷",
    "杠杆",
    "预言机",
    "仓位管理",
    "风险管理",
    "稳定币借贷",
    "MEV",
    "OEV",
    "预言机套利",
    "清算套利",
    "Flashbots",
]

# ============ 数据存储配置 ============
DATA_DIR = "data"  # 数据存储目录
RETENTION_DAYS = 7  # 数据保留天数（延长至一周，方便沉淀获客线索）
MAX_POST_AGE_DAYS = 3  # 只收集最近 N 天内发布的帖子

# ============ 定时任务配置 ============
COLLECT_INTERVAL_HOURS = 1  # 收集间隔（小时）

# ============ 相关性阈值 ============
# 只保留至少命中一个高价值场景词或两个普通关键词的帖子
MIN_RELEVANCE_SCORE = 2
