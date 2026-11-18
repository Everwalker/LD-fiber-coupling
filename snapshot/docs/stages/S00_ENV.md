# S00 | 环境与最小可复算操作（974 单基线包）

## 输入与前置

输入：AGENTS.md、本 REQUIREMENTS/PLAN、NEXT.md；执行机上已安装的 COMSOL 与 MCP 服务。当前没有经核验的光学项目远端，也没有本版任何建模日志。S01 可与本阶段并行独立推进。若本会话未注册 COMSOL MCP 工具，如实记录，不推断其他进程状态。

## 操作步骤

1. 确认工作区根为本包目录；先查 git 状态并保留既有改动；确认运行账号权限、OS、RAM、磁盘、Python/NumPy 版本。不采集、不上传许可证内容或机器敏感标识。不在 MCP 工具自身仓库或原项目目录里创建光学模型。
2. 经已连接 MCP 实际读取 COMSOL 版本/build 与 Wave Optics 许可可用性。不是 6.4 时不保存正式模型，登记 VERSION_MISMATCH 交用户处理；只装 6.3 或许可缺失按 LICENSE/VERSION 阻塞上报。
3. 枚举实际 MCP 工具与参数 schema，保存去敏能力矩阵，逐项标 已实测/仅文档/不可用：模型创建/保存/关闭/重开；参数与表达式读写；几何与命名选择；材料与物理节点；模态 study 与驱动 study；job 启动/状态查询/取消；清空解但保留 study/mesh；完整复数 E/H 导出；日志/DOF 读取。单模型路线不需要 EWBE/传场算子能力，但仍须确认 3D EWFD 的端口、背景场表达式与模式积分可用（S03/S05 依赖）。
4. 创建独立最小模型：参数 L=1 um、一个几何体、明确命名选择与材料；保存 smoke_64.mph，关闭后重开并查询参数/树/选择；改 L 重建，核验选择仍指向正确对象。保存两次树对照，不只一张截图。
5. 在小空气域加 EWFD 频域研究做最小合法驱动解（不是本项目正式源），导出至少一组复数 E/H 与实数功率，验证 FIELD_CONTRACT 所需字段（坐标、权重、法向、完整物理复场而非包络）确实可取。没有真求解的几何 smoke 不能证明 solver 可用；能导 txt 不能证明能导复场。
6. 试验清空解但保留 study/mesh 并重新求解；试验长任务 job_id/状态查询与超时行为：超时后先查询既有 job，不无条件重发；无状态接口时设计单作业锁与人工确认路径并记录。
7. 确认能否真实派生独立子 agent 审查；不能则登记 REVIEW_BLOCKED。确认本包 git 远端状态（当前预期 REMOTE_UNCONFIGURED）；无远端不阻塞本地物理步骤，但不得虚构上传。
8. 为 src/runtime/ 编写真实适配器：动作输入输出、日志、失败分类、超时/取消、版本检查，只使用本阶段实测过的调用，不猜私有 API；配一个不依赖大模型的回归 smoke。
9. 运行命令契约：python -m tools.preflight、python -m unittest discover -s tests -v。失败先修软件层；通过只记软件绿灯，不写任何 COMSOL 结论。

## 必交付与有限验收

evidence/environment.json（去敏 build/许可/资源）、evidence/capabilities.json（功能+证据+缺能力清单）、smoke 模型与哈希、实际 MCP 调用日志、模型树对照、smoke 测试记录、远端策略记录。G16（6.4 实际读写重开与 MCP 能力测试）真实通过；复场导出能力缺失时 G16 判不通过并归类 MCP_CAPABILITY。环境不满足时准确区分许可/版本/MCP/资源问题。独立审查者核验"实际做了什么"，不是勾选工具清单。

## 失败处理

MCP 未连接/许可缺失/版本不符：BLOCKED 上报最小复现，同时继续不依赖它的 S01 与离线代码工作；不擅自 Java/MATLAB/CLI 直连（须用户批准+ADR）。同一失败连续 3 次无新证据：停止该路径，登记根因。

## 收尾（各阶段通用）

冻结候选哈希并提交独立子 agent 审查（分工见 EXECUTION_AND_RECOVERY.md）；审查未通过不得标 VALIDATED；修复产生新候选须重审。在 evidence/stages/S00/ 写 stage_result.json、摘要与去敏日志；模型/大场文件入 artifacts/runtime/S00/，小表与图入 results/S00/；模型、study/dataset、job、配置哈希串成可追溯链。更新 PROJECT_STATE.json、NEXT.md 与 handoff 后继续可执行阶段；阻塞时保存最小复现并转向不依赖该阻塞的任务。
