# Bills 账户体系重构设计

## 背景

Bills 是面向个人财务管理和 Fava 分析的 Beancount 账本。重构前基线为
822 条 entries、66 个 open 账户、0 个 Beancount 错误，3 项订阅配置有效。

现有账户已经具备资产、负债、收入和支出的基本层级，但存在以下问题：

- `General`、`Other`、`LocalServices` 等兜底账户边界不清。
- 部分账户把经济用途、供应商和产品混在同一层级。
- `Transport:Local`、`Household:Supplies`、`Electronics:Accessories`
  和 `Health:Supplements` 聚合了分析价值明显不同的支出。
- 两笔滴滴出行和一笔零食消费误入
  `Expenses:Technology:Network:Proxy`。
- 四个账户没有实际过账，其中
  `Expenses:Technology:Subscriptions:General` 仅被预算引用。

## 目标

1. 账户更干净：删除无用账户和含义模糊的兜底账户，避免新旧名称并存。
2. 账户更专业：账户路径表达经济实质，并稳定区分机构、产品和用途。
3. 保持较细颗粒度：拆分对预算和复盘有价值的类别，但不按临时商户建账户。
4. 保证账本数据不乱：历史金额、币种、日期、正负号、成本、价格、交易平衡和过账数量不得变化。

## 非目标

- 不修改交易对手、说明、订单元数据或真实发生日期。
- 不补造礼品卡面值、汇率、成本基础或其他缺失数据。
- 不把 2,600 CNY 电动车擅自资本化，也不引入折旧政策。
- 不重写预算金额、订阅金额或订阅日期。
- 不按每个一次性商户建立账户。

## 分类原则

### 用途优先

支出账户首先表达经济用途。供应商只在技术订阅、云服务、金融机构、
银行卡和投资产品等稳定且有独立分析价值的场景作为叶子保留。

### 层级约束

- 常规账户保持 3 至 5 层。
- 更深层级只用于稳定产品，例如
  `Expenses:Technology:AI:Google:GoogleOnePro`。
- 禁止继续使用 `Fix`、`FIXME`、`General`、`Other` 和
  `LocalServices` 等模糊叶子。
- 同一经济用途只保留一条规范路径。

### 历史一致性

所有历史流水、预算、自定义指令和订阅配置同步迁移。全局改名保留原
open 日期；拆分账户使用来源账户的 open 日期，保证不晚于首次使用。

## 目标账户结构

资产、负债和权益结构已经清晰，本次只删除未使用收入账户，不重排
资产、负债和权益路径。重点调整后的支出结构如下：

```text
Expenses
├── Communication
│   └── Mobile
│       ├── Domestic
│       ├── International
│       └── ServiceFees
├── Education
│   └── ProfessionalDevelopment
├── Electronics
│   ├── Batteries
│   ├── CablesAndChargers
│   ├── CareAndCleaning
│   └── MobileAccessories
├── Entertainment
│   └── Subscriptions
│       └── Music
├── Family
│   ├── Housing
│   │   └── PropertyManagement
│   ├── Insurance
│   │   └── Mom
│   ├── Support
│   └── Utilities
│       └── Electricity
├── Financial
│   └── BankFees
├── Food
│   ├── Groceries
│   ├── Meals
│   └── Snacks
├── Health
│   └── Supplements
│       ├── Mixed
│       ├── Protein
│       └── VitaminsAndMinerals
├── Household
│   ├── CleaningSupplies
│   ├── DrinkingWater
│   ├── HomeFragrance
│   └── Kitchenware
├── Personal
│   ├── Accessories
│   ├── Care
│   │   ├── Haircut
│   │   └── Toiletries
│   ├── Stationery
│   └── Wellness
│       └── SleepAids
├── Professional
│   └── Resources
├── Services
│   ├── Administrative
│   ├── EquipmentRental
│   │   └── PowerBank
│   └── Logistics
├── Technology
│   ├── AI
│   │   ├── Google
│   │   │   └── GoogleOnePro
│   │   ├── JetBrains
│   │   │   └── AIPro
│   │   └── OpenAI
│   │       └── Codex
│   ├── CloudInfrastructure
│   ├── CloudStorage
│   │   └── Apple
│   │       └── ICloud
│   ├── DeveloperTools
│   ├── DigitalGoods
│   │   └── GiftCards
│   ├── Domains
│   ├── Network
│   │   └── Proxy
│   └── Software
│       ├── Applications
│       └── Productivity
└── Transport
    ├── Micromobility
    ├── PublicTransit
    ├── RideHailing
    └── Vehicle
        └── Purchase
```

## 迁移规则

### 全局改名

| 旧账户 | 新账户 |
|---|---|
| `Expenses:Entertainment:Subscriptions:DigitalMedia` | `Expenses:Entertainment:Subscriptions:Music` |
| `Expenses:Family:Support:Transfers` | `Expenses:Family:Support` |
| `Expenses:Financial:Fees` | `Expenses:Financial:BankFees` |
| `Expenses:Services:LocalServices` | `Expenses:Services:Administrative` |
| `Expenses:Technology:Services:Office` | `Expenses:Technology:Software:Productivity` |
| `Expenses:Technology:AI:Google` | `Expenses:Technology:AI:Google:GoogleOnePro` |
| `Expenses:Technology:AI:JetBrains` | `Expenses:Technology:AI:JetBrains:AIPro` |
| `Expenses:Technology:AI:OpenAI` | `Expenses:Technology:AI:OpenAI:Codex` |
| `Expenses:Technology:CloudStorage:ICloud` | `Expenses:Technology:CloudStorage:Apple:ICloud` |

以下 open 指令删除：

- `Expenses:Services:General`
- `Income:Interest:Investment`
- `Income:Interest:Bank:ICBC`

`Expenses:Technology:Subscriptions:General` 的 50 CNY 月预算改挂
`Expenses:Technology:Network:Proxy`，预算数值和月份不变，然后删除原
open 指令。

### 交通

`Expenses:Transport:Local` 全部拆分，同时修正误入 Proxy 的三笔交易：

| 识别条件 | 新账户 | 合计 |
|---|---|---:|
| 滴滴出行，包括误入 Proxy 的两笔 | `Expenses:Transport:RideHailing` | 45.85 CNY |
| 南阳市公共交通集团 | `Expenses:Transport:PublicTransit` | 1.00 CNY |
| 松果出行、哈啰骑行 | `Expenses:Transport:Micromobility` | 13.90 CNY |
| “转账,电动车” | `Expenses:Transport:Vehicle:Purchase` | 2,600.00 CNY |
| 2026-07-11 零食很忙，原误入 Proxy | `Expenses:Food:Snacks` | 13.15 CNY |

迁移后交通合计为 2,660.75 CNY；Proxy 扣除 42.99 CNY
错分后为 386.16 CNY。Expenses 根级合计不变。

### 家居及个人用品

原 `Expenses:Household:Supplies` 的 213.34 CNY 按用途拆分：

| 内容 | 新账户 | 合计 |
|---|---|---:|
| 笔记本、文具店消费 | `Expenses:Personal:Stationery` | 19.84 CNY |
| 隔音睡眠耳塞 | `Expenses:Personal:Wellness:SleepAids` | 34.80 CNY |
| 员工离岗文档模板 | `Expenses:Professional:Resources` | 35.00 CNY |
| 冷萃杯 | `Expenses:Household:Kitchenware` | 55.00 CNY |
| 冰箱除味剂、咖啡茶渍清洁剂 | `Expenses:Household:CleaningSupplies` | 30.30 CNY |
| 香氛片、固体香薰 | `Expenses:Household:HomeFragrance` | 38.40 CNY |

### 电子配件

原 `Expenses:Electronics:Accessories` 的 119.27 CNY 拆分：

| 内容 | 新账户 | 合计 |
|---|---|---:|
| 手机壳、手机膜 | `Expenses:Electronics:MobileAccessories` | 17.17 CNY |
| 两笔电池 | `Expenses:Electronics:Batteries` | 27.00 CNY |
| 屏幕清洁湿巾、纳米布 | `Expenses:Electronics:CareAndCleaning` | 36.69 CNY |
| Type-C 数据线 | `Expenses:Electronics:CablesAndChargers` | 38.41 CNY |

### 营养补充

原 `Expenses:Health:Supplements` 的 529.35 CNY 拆分：

| 内容 | 新账户 | 合计 |
|---|---|---:|
| 同时包含氨糖、蛋白粉、镁和维生素的混合订单 | `Expenses:Health:Supplements:Mixed` | 174.40 CNY |
| 蛋白粉、酵母蛋白及蛋白粉退款 | `Expenses:Health:Supplements:Protein` | 87.03 CNY |
| 维生素、鱼油、辅酶 Q10 | `Expenses:Health:Supplements:VitaminsAndMinerals` | 267.92 CNY |

### 技术服务和礼品卡

- Apple Gift Card 相关的 34.50 CNY 和 13.00 USD 改记
  `Expenses:Technology:DigitalGoods:GiftCards`。
- 手机套餐办理服务 7.88 CNY 改记
  `Expenses:Communication:Mobile:ServiceFees`。
- 数码荔枝 Office/生产力软件 99.00 CNY 改记
  `Expenses:Technology:Software:Productivity`。
- 其他 `Expenses:Technology:Software:Applications` 交易保持不变。

礼品卡仍保留在 Expenses 根下，因为原流水没有明确美元面值和成本基础。
本次不推断汇率，也不把 CNY 支出转换成 USD 资产。

## 配套引用

账户路径发生变化时同步更新：

- `accounts/data/expenses.bean` 和 `accounts/data/income.bean`
- `journal/2025/*.bean` 与 `journal/2026/*.bean`
- `budgets/data/2026.bean`
- `plugins/auto_subscriptions.json`
- 任何 accrual、assertion、init 或文档中的实际账户引用

订阅配置中的 Google 和 OpenAI 账户改为产品级新路径。所有订阅金额、
币种、账单日和起止日期保持原值。

## 防止账户再次变乱

扩展 `tools/validate_ledger.py`：

- 检查 open 账户是否至少被交易、余额、pad、close 或 custom 指令引用。
- 禁止账户路径包含 `Fix`、`FIXME`、`General`、`Other` 或
  `LocalServices` 模糊段。
- 保留现有的缺少 open、open 晚于首次使用、货币和 metadata 检查。

预算 custom 指令属于有效引用，因此预算账户不会被误报为未使用。

## 金额与语义保护

实施前从干净 Git 基线创建只读临时副本。迁移后使用 Beancount 对象级
比较，逐条验证：

1. Transaction、Balance、Pad、Close 和 Custom 指令数量一致。
2. 每笔交易的日期、flag、payee、narration、tags、links 和业务 metadata
   一致。
3. 每个 posting 的 units、currency、cost、price、flag 和 metadata 一致。
4. posting 数量和顺序一致，只有 account 字段允许按本设计变化。
5. Assets、Liabilities、Equity、Income、Expenses 各根账户分币种合计一致。
6. 所有账户变化都落在本设计允许的旧账户到新账户集合内。

账户 open 指令单独比较：允许按设计改名、拆分或删除未使用账户，但
币种约束和现有 metadata 不得丢失。

任何比较失败都立即停止，不继续格式化或提交。

## 验证流程

1. 创建迁移前临时副本并记录根账户分币种合计。
2. 修改账户定义及全部引用。
3. 运行对象级迁移比较。
4. 运行 `make validate`。
5. 运行 `git diff --check`。
6. 搜索旧账户、模糊账户和占位账户，结果必须为空。
7. 使用 Beanquery 对比迁移前后各根账户与新叶子账户的金额。
8. 仅在全部检查通过后提交账本变更。

## 验收标准

- 账本加载错误为 0，订阅配置有效。
- 不存在旧账户和新账户混用。
- 不存在 `Fix`、`FIXME`、`General`、`Other` 或 `LocalServices`
  模糊账户。
- 不存在无引用 open 账户。
- 明显错分的两笔滴滴和一笔零食已修正。
- 交通、家居、电子配件、营养补充和技术服务达到设计颗粒度。
- 所有历史金额、币种、交易日期、过账数量和交易平衡与迁移前完全一致。
