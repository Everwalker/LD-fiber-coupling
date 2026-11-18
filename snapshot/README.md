# LD→带透镜光纤端 单基线 | COMSOL 6.4 工作包 v3.0（974 nm）

基线日期：2026-11-11。工作语言：中文。规范对象：DG-SM-980-GP-600 芯片等效辐射场 → 空气间隙 → 光纤端部一体化楔形圆弧透镜 → Corning HI 1060 FLEX 均匀（等效阶跃）光纤基模耦合。仿真工况波长 974 nm 由用户指定。

**这是一个实施任务包，不是已完成的仿真项目。** 包内没有 COMSOL 求解结果、没有虚构 .mph，科学状态为 NOT_RUN。生成本包的会话未连接 COMSOL；不能据此判断其他进程或会话的实时状态。源码检查、预检与将来的 COMSOL 物理验收严格分开。

## 立即开始（完整路径）

1. 以本目录为工作区，把 GOAL.txt 粘贴给执行 agent；不要只给 goal 不给文件。
2. 阅读顺序：AGENTS.md → REQUIREMENTS.md → PLAN.md → NEXT.md → 当前阶段 docs/stages/Sxx_*.md。建模前还应阅读 docs/GEOMETRY_BASELINE.md、PHYSICS、FIELD_CONTRACT、COMSOL64_IMPLEMENTATION、VALIDATION、EXECUTION_AND_RECOVERY 和 GITHUB；v2 快照仅供只读追溯。
3. 先运行软件预检（需要 Python 3.10+ 与 requirements.txt 依赖；不启动 COMSOL、不联网、不推送）：

```text
python -m tools.preflight
python -m unittest discover -s tests -v
```

`jsonschema` 是两项 schema 行为测试的可选依赖；未安装时这两项会跳过，不能计为已验证。本包生成时该依赖可用，47 项测试均执行并通过。其他机器上的实际通过、跳过和失败数量以运行结果为准。

预检/单元测试只验证输入哈希、配置一致性、解析参考与投影/记录代码在测试输入上工作。**它们不能证明 COMSOL 已安装、许可可用、MCP 可连接，也不构成任何物理结果证据。** 五层证据（软件单测、COMSOL 物理单元、完整模型、公差/谱（本版后移）、交接复现）不能互相替代。
4. 进入 S00 前，在执行机只读检查：现有 COMSOL/MCP 会话、活动 job、.mph 锁与遗留文件。状态不明时禁止重发作业或启动可能清空既有模型的会话。

## 本版与 v2 的关系

v2（两非球面透镜、970 nm 名义、967/970/973 与宽谱/公差计划）是本版依据，其规范快照只读保存在 legacy/v2_snapshot/；完整 v2 项目与历史日志在原项目目录（本包之外），不得修改。本版按用户确认的范围改写：单一一体化纤端透镜基线、974 nm 单工况、S05 跨接口条件不适用、S07/S08 后移、S06 改为纤端透镜、G20 改为一个模型制品。保留的原数值阈值一律不改；采样数量缩减与 gate 适用性变更全部登记在 CHANGELOG.md 的 ADR 台账。

## 文件地图

| 文件/目录 | 用途 |
|---|---|
| GOAL.txt | 给执行 agent 的目标文本 |
| AGENTS.md | 执行边界、审查与接班纪律 |
| REQUIREMENTS.md | 本版唯一规范性范围、要求编号、DoD |
| PLAN.md | 阶段顺序、并行边界与必须增量 |
| CHANGELOG.md | v3 变更记录 + ADR 台账 |
| docs/stages/S00..S09 | 每阶段输入、操作、证据、有限验收与失败处理 |
| configs/ | parameters.json / gates.json / sampling.json：参数、阈值、适用性和代表工况；gates.json 是门槛数值来源 |
| src/、validation/、tools/、tests/ | 源场数学、独立投影、预检与单元测试；仅软件检查，不是 COMSOL 建模适配器 |
| docs/GEOMETRY_BASELINE.md、references/ | 可重建纤端示意几何与公开来源及适用边界 |
| inputs/private_originals/ + manifest.json | U1/U2 原件逐字节副本与 SHA-256；默认不进 Git |
| legacy/v2_snapshot/ | v2 规范只读快照，无本版优先级 |
| PROJECT_STATE.json、NEXT.md、handoff/ | 接班状态索引，由执行 agent 按实际更新 |

## 状态与恢复

- 四个独立状态轴各自记录、不得互相代替：科学（NOT_RUN→各 gate 实测值）、独立审查、远端同步（当前 LOCAL_ONLY）、实验验证（NOT_PERFORMED）。当前目录位于原 Git 工作树内；上层 origin 已配置，但公开上传范围待确认，独立解压后须重新检查。
- 任何接班：先读 PROJECT_STATE.json 与 NEXT.md，再查未结束 job 与 .mph 锁，然后从上一检查点继续；不从 README 重头再造一遍。状态文件声称 VALIDATED 但证据缺失时回退为待核验并记录。
- 会话结束前更新 PROJECT_STATE.json、NEXT.md 与 handoff/，写清未结束 job、最后可重算模型及 SHA、已过/未过 gate、精确下一步。禁止只写"基本完成"。

## 发布与隐私

默认按私有研发项目处理。原始截图/PDF、厂商资料、许可、机器标识、令牌不进普通 Git；.gitignore 默认忽略大模型与场文件，但被忽略的科学字节仍须经批准的制品存储保留并可取回（SHA 校验）。未获用户逐项授权前不上传、不公开、不因上传受阻而改变仓库可见性。

规范优先级：用户新指令 > REQUIREMENTS.md > 其他 v3 文档/配置 > legacy/v2_snapshot。规范变更必须写 ADR 并修改版本，不得以"优化脚本"为由悄悄降门槛。
