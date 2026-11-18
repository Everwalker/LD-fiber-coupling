> 版本：v3（974 nm 楔形圆弧纤端一体化单体模型），修订日期 2026-11-11。范围与采样数量变更受 ADR-003 约束；保留的原数值阈值一律不改。

# 持续推进、独立审查与恢复（v3）

执行循环、独立审查合同、job/内存/失败处理与交班字段沿用 v2；本版只改 S00–S09 的阶段语义与依赖，ID 与 gate 分类仍与 common 一致。

## 1. v3 阶段语义（ID 不变）

| 阶段 | v3 语义 | 状态类型 |
|---|---|---|
| S00 | 环境/MCP/许可能力实证 + 读写重开 smoke（同 v2） | 必需 |
| S01 | 输入冻结：U1/U2 原字节与哈希、v3 参数表（新增 lens_geometry 分支：alpha/Rtip/gap，grade A+D/E）、命令契约（python -m tools.preflight；python -m unittest discover -s tests -v）接入 | 必需 |
| S02 | 974 nm 模态：HE11 子空间 + 高阶候选分类；F_CUTOFF 族定义冻结不求解 | 必需 |
| S03 | 974 nm S_FF 代表源：空域角谱、功率归一、FWHM 检查；S_MFD 两分支定义冻结 | 必需 |
| S04 | 局部入纤基准（B1/B2/B3）与端口/投影标定；可微背景场选型实验 | 必需 |
| S05 | 单域模型的受控源注入与全域可行性验证（G17）必需；仅在经批准的分段方案中激活跨接口 G10/G11a/G11b，保留触发证据 | 必需；分段条件 |
| S06 | 由两透镜完整光路改为楔形圆弧纤端：单体模型 ld974_lensfiber_ewfd.mph 构建、求解、全账本导出 | 必需（本包核心） |
| S07 | 公差/装调：后移（DEFERRED_AFTER_ACCEPTANCE），不删要求、不改阈值、不执行 | 后移 |
| S08 | 宽谱/截止端点：后移；967/970/973、10/15/20 nm、890/930/970 分支定义全部冻结保留 | 后移 |
| S09 | 发布：BASE 与 LAT1 两点清空解重算（G15 limit 不变）、独立审查、单模型制品取回（G20 改名语义） | 必需 |

依赖：S00 与 S01 的独立工作可并行；两者均通过后推进 {S02,S03}→S04→S05→S06→S09。S05 的跨接口检查仅在分段方案激活，单域注入验证仍必需。S07/S08 位于 S06 之后、本版后移。阶段状态、审查状态、同步状态独立记录。

## 2. 并行草稿区与单写入者

共享工程并行使用分支或独立目录，由主 Agent 统一整合；同一 .mph/同一 COMSOL server 会话只允许一个写入者。其他 agent 可独立分析或读冻结制品，但不得并发写同一模型与会话。

## 3. 执行循环与命令契约

每次启动先读 PROJECT_STATE/NEXT（整合后由主 Agent 维护），核查实际 Git/文件/job 状态，再选最小已满足依赖的工作。包级命令（均不启动 COMSOL）：

    python -m tools.preflight
    python -m unittest discover -s tests -v

preflight 失败时不得进行 MCP 建模。COMSOL 动作一律走 MCP 并记调用日志；超时先查既有 job，不重提交；取消只作用于本项目已确认 job。单 job RAM 目标≤物理 RAM 70%；预计 DOF/文件量先估后跑；内存受阻→登记证据→受控分段 fallback（见 COMSOL64_IMPLEMENTATION 第 3 节 C），不预防性分段、不偷工网格。

## 4. 独立审查合同（不变，再强调）

实现者提供 candidate_manifest 不可变 SHA、requirements 映射、源码 diff、模型与 raw field、gate 结果与失败表；独立子 agent 先读规范与原始证据再读作者解释；审查者不写同一 mph。review 记录 reviewer_run_id/implementer_run_id/candidate_sha256/所读 artifact IDs/缺陷严重度/决定。实现者改场/功率定义的后处理也算候选改变，需按新 hash 重审。无真实子 agent 入口时标 REVIEW_BLOCKED，不自批。独立审查与远端同步相互独立。

## 5. 失败分类与停止规则

失败类别：LICENSE、VERSION、MCP_CAPABILITY、GEOMETRY、SELECTION、MESH、SOLVER、PHYSICS_GATE、EXPORT、REVIEW、UPLOAD。同一失败无新证据连续三次停止该路径并登记根因；楔形几何布尔/相交失败属 GEOMETRY/SELECTION，必须先修拓扑取证再继续网格。

## 6. 交班最小字段（v3 增量）

沿用 v2 交班字段，另增：当前 S05 是否已因真实资源证据激活分段分支；G20 单模型制品的冻结检查点 SHA；后移分支（S07/S08）清单与未解冻状态；包版本与候选配置的差异记录。
