# AGENTS.md | LD_Fiber 974 nm 单基线工作包 v3.0

本文件是包内执行 agent 的行为边界。用户新指令 > REQUIREMENTS.md > 本文件与其他 v3 文档 > legacy/v2_snapshot（只读对照，无规范优先级）。

## GPT 主 Agent 与本地子 Agent 协作

仅在使用 GPT 模型时生效：主 Agent 负责规划、关键决策、冲突协调与最终验收，常规探索、编码和测试优先委派。子 Agent 优先实际调用 `omlx/Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S`、推理强度 `max`；不得仅因本地模型速度切换。该模型不可用时可用 `gpt-6-luna`、`max` 作为唯一备选，未经用户允许不得使用其他模型；若工具不回显实际路由，应明确标注未核实。

可独立推进的任务优先并行，最多三个子 Agent；依赖明显或并行成本更高时串行。共享工程并行必须使用分支或独立目录，由一个协调者整合，禁止写入冲突；同一 COMSOL 会话或 `.mph` 始终只有一个写入者。独立审查者不得是该候选实现者。常规问题自主解决；连续三次有效尝试无进展，或涉及重大架构、复杂算法、兼容性和数据安全时，提交关键证据供主 Agent 决策。

只实施实际需求和已确认问题，保持最小 diff、必要安全检查和与修改范围相称的验证，不做无依据兜底、重试、无关重构或多轮重复测试。最终分别报告实际可核实的执行模型、修改、验证与未完成事项。

## 任务而非计划

你在实施本项目：读现有文件、核实环境后，逐阶段编写可运行的建模源码/MCP 调用序列，经 MCP 在真实 COMSOL 6.4 中创建、求解、导出、验证、修复。禁止只补文档、生成空函数后宣称完成。同一会话内可继续下一个已满足依赖的阶段；离开会话前更新 PROJECT_STATE.json、NEXT.md 与 handoff。

## 不可破坏的边界

1. 只在本工作包目录及获准的 COMSOL 执行机内操作。原项目目录（本包之外）一律只读；不 hard reset、不 force push、不覆盖其他项目、不自动合并 main。先查 git 状态，保留他人改动。
2. 默认 MCP-only。MCP 内部调用的官方 API 不等于绕过；绕过 MCP 的 Java/MATLAB/CLI 直连须用户批准并记 ADR。属性名/节点 tag 从实际 6.4 录制、导出或文档核对获得；禁止猜测属性后静默跳过失败节点。
3. 实际版本必须是 6.4：读出 build 与 Wave Optics 许可可用性并保存去敏记录。旧模型只能在副本上迁移。交付模型由实际 6.4 保存并重新打开验证。
4. 不伪造输入、许可、连接、求解、截图、日志、审查、push 或上传。空模板、解析结果、其他文献数值、历史缓存均不是本项目 COMSOL 结果。不存在的值写 null+原因，不写 0 冒充。
5. 物理硬规则（沿袭 v2，不得放松）：主效率分母固定为原始源正向功率（计算归一 1 W；0.600 W×eta 仅为 974 nm 单色等效换算，不是实测 974 功率，也不是宽谱加权功率）；失配、辐射、返回源侧功率不得丢弃；不重复扣反射；PML 是数值开放边界不是材料吸收，不与同一穿界通量重复计；总截面通量不是 HE11，效率只取识别后的两 HE11 偏振子空间投影。
6. 不得自行放松门槛、删掉难分支、改成二维纵截面、换器件以通过验收。允许新增明确标注适用边界的诊断分支。本版已冻结的排除项（形状对比、参数优化、公差扫描、宽谱扫描）不得因"顺手"而执行。
7. 原始 U1/U2、v2 快照与原项目文件不可修改。inputs/private_originals 的 SHA-256 必须与 inputs/manifest.json 一致。未获用户逐项授权不上传原始资料、许可证、安装器、机器标识、密钥；不因 GitHub 受阻而改变仓库可见性。

## 本版范围护栏（详见 REQUIREMENTS.md 第 6 节与 CHANGELOG ADR 台账）

- 一个规范 3D 模型（含模态/源辅助 study），不要求四个模型制品；G20 按一个模型判定。
- 代表工况集合 v3 = {BASE 名义基线, LAT1 回归/诊断偏移 dx=+1 um}。不跑公差扫描、不跑光谱扫描。
- 974 nm 是用户指定仿真工况；U1 的 967/970/973 nm、600 mW、慢轴 6 deg（数值为 U；x=水平慢轴对应与全角 FWHM 约定为 E）、15 nm 谱宽与 U2 的 930+-40 nm 截止、推荐工作 >980 nm 全部保留为原始记录，974 超出两者名义范围必须如实写入 limitations。
- 楔形半角 45 deg、顶端 R3.25 um、轴向间隙 5.65 um 是公开 980 nm 研究初值（等级 A/E），不是产品规格或最优。

## 命令契约（纯软件，不启动 COMSOL）

- python -m tools.preflight：输入哈希、配置一致性、gate 模式与静态自检。
- python -m unittest discover -s tests -v：解析、投影、记录工具的单元测试。
两者通过只证明软件检查成立，不构成任何 COMSOL 能力、求解或物理结论的证据。

## 执行、审查与接班

- 每阶段：读取输入/状态 → 冻结候选配置 → 实现与测试 → 保存原始证据 → 自检 → 独立子 agent 审查 → 修复 → 重审 → 记录。独立审查者不得是该候选实现者，必须读冻结代码、原始数值、失败日志与规范，而不是作者摘要。无法真实派生审查者时标 REVIEW_BLOCKED，不得自任审查。
- 同一 .mph / 同一 COMSOL server 会话只允许一个写入者；其他 agent 只读冻结制品或写不冲突文件。
- 每个最小可复算增量记录：case_id、参数/代码/输入/模型哈希、study/dataset、job_id、MCP 调用日志、耗时、状态。数值通过、审查通过、远端推送是三个独立状态（NOT_STARTED/RUNNING/NEEDS_REVIEW/VALIDATED/BLOCKED/FAILED；LOCAL_ONLY/COMMITTED/PUSHED/VERIFIED_REMOTE/REMOTE_UNCONFIGURED）。
- 超时先查询既有 job（job_id/状态），不重新提交；无法查询则 UNKNOWN_JOB_STATE 并人工确认。取消只作用于确认属于本项目的 job。同一失败连续 3 次且无新证据时停止该路径，登记根因（LICENSE/VERSION/MCP_CAPABILITY/GEOMETRY/SELECTION/MESH/SOLVER/PHYSICS_GATE/EXPORT/REVIEW/UPLOAD），转向可独立任务。资源：单 job RAM 目标 ≤ 物理 RAM 70%，磁盘余量 ≥ 预计检查点体积 3 倍。
- 任何新的范围、分支、gate 适用性或采样数量变更：先在 CHANGELOG.md 和 ADR 中登记，再实施；被标记 NOT_APPLICABLE/DEFERRED 的 gate 保留原 id 与原限值，不删除、不改数值。本版范围决策见 docs/adr/ADR-003-974-lensed-fiber.md；当前包生成审查不替代后续变更审查。

## 尚待执行环境确认（不得假定）

COMSOL 6.4 精确 build、Wave Optics 许可、MCP 实际工具 schema 与复场导出能力、RAM/磁盘、可派生独立审查 agent、目标远端仓库与可见性。本包生成会话未连接 COMSOL；PROJECT_STATE.json 中的 NOT_RUN 是事实，不是缺漏。
