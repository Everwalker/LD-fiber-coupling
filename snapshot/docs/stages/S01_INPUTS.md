# S01 | 参数冻结、原件核对与 974 解析参考

## 输入与前置

输入：inputs/private_originals/ 的 U1 截图与 U2 PDF（逐字节副本）、inputs/manifest.json、主 Agent 冻结的 configs/parameters.json（974 nm/OP974、楔形 45°/R3.25 um/间隙 5.65 um 初值、F_NOM 均匀阶跃、快轴 30° 假设）、legacy/v2_snapshot/ 只读对照。不依赖 COMSOL 已连通。

## 操作步骤

1. 运行命令契约（python -m tools.preflight；python -m unittest discover -s tests -v）。核对 U1/U2 实际 SHA-256 与 manifest 一致（清单记录值：U1=08238dee…4302，U2=2cf09d3e…adb9c，以 preflight 实际输出为准）。逐项目视 U1 与 U2 第 2 页：LD 名义 967/970/973 nm、600 mW、慢轴 6°、谱宽 10/15/20 nm、芯片 105/115/125 um；光纤 2010 版资料、截止 930±40 nm、推荐工作 >980 nm、MFD@980 4.0±0.3 um。原件不得改写，974 nm 作为用户新增工况写入。
2. 生成 evidence/parameter_review.md：每参数记原值/单位/定义/来源等级 U-R-A-E-D-N/用途/未知项。5 um 宽度约定、快轴实测、像散、参考温度、剖面、实测谱逐一列为不确定项；45°/R3.25/5.65 明确标"980 nm 研究初值（A/E），非规格非最优"。
3. 运行解析参考检查（validation 工具，输出字段必须标 ANALYTICAL_REFERENCE_974，不写 COMSOL）：Malitson n(974)；空气—熔融石英法向 Fresnel R(974)（v2 的 970 nm 参考 R≈0.03383412 只作对照，不挪用于 974 判定）；由 6°/30° 全角 FWHM 计算 wx/wy 初值；NA/截止关系与 F_NOM 弱导 LP11 截止估计（约 977 nm 量级，974 nm 不预设单模）；楔形/圆弧初值的边厚、自交叠与包络检查；等光程/高斯匹配仅作假设层参考。
4. 建立统一配置解析：单位仅在明确边界转换，内部 SI，COMSOL 表达式显式带单位；raw 层保留全部原始值，derived 另存。修改波长到 974 时不得无意改写已冻结的腰径、几何初值或装配。
5. 实现参数前置检查（fail-closed）：正波长/尺寸/功率；NA>0 且 ncore>nclad；楔形半角+R+间隙自洽（边厚>0、无自交叠）；源面/端口/PML 不穿入异材料；LAT1 平移后域包络合法；974 在 OP974 分支而非插值到 U1 名义带。为负半径、几何自交叠写负例，违规返回解释并在求解前停止。
6. 冻结分支与 case 命名：波长分支 OP974（用户指定）；光纤分支 F_NOM（均匀阶跃，等效模型声明随数据保存）；源分支 S_FF（本版唯一活动源分支；S_MFD_E2/S_MFD_FWHM 与快轴 20/40、像散 ±10 保留为配置中"已登记未执行"记录）。case_id 由规范化参数哈希生成：BASE=LD974-WEDGE-BASE-001，LAT1=BASE+dx=+1.0 um。不预填任何效率。
7. 生成待执行 case 表（仅参数+PENDING）：只有 BASE 与 LAT1 两行；同时把被后移的扫描留在 scan_plan 留档并标 DEFERRED，防止被误执行。

## 必交付与有限验收

参数审查表、假设/冲突记录、974 解析参考及工具测试日志、配置读取器与合法/负例测试、待执行 case 表。G01（原件与活动参数追溯）、G02（解析/几何/投影单测）通过。源场物理性与模式真实性分别留待 S03/S02，不在本阶段宣称已验证。

## 失败处理

SHA 不符：立即停止，核对副本来源，不覆盖原件。解析检查异常：区分代码错误与物理理解错误，留原始输出；连续 3 次无新证据则登记根因换可独立任务。参数冲突（如 974 与原始带不符）不"调和"，登记 conflicts 并按 U/用户指令定序。

## 收尾（各阶段通用）

冻结候选哈希并提交独立子 agent 审查；未通过不得标 VALIDATED；修复后重审。evidence/stages/S01/ 写 stage_result.json+摘要+去敏日志；大文件入 artifacts/runtime/S01/，小表图入 results/S01/；上传矩阵按 GITHUB.md，当前远端 REMOTE_UNCONFIGURED 只记录不执行。更新 PROJECT_STATE.json、NEXT.md、handoff 后继续。
