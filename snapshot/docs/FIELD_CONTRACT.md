> 版本：v3（974 nm 楔形圆弧纤端一体化单体模型），修订日期 2026-11-11。范围与采样数量变更受 ADR-003 约束；保留的原数值阈值一律不改。

# 完整复场与接口合同（v3）

本文件与 v2 FIELD_CONTRACT.md 的字段、内积与测试合同一致；差异仅在：基线为单体全频域模型，因此“EWBE→EWFD 传场”一节对基线不适用，只有当真实内存受阻、启用受控分段 fallback 时才按本合同执行（见 COMSOL64_IMPLEMENTATION.md 第 3 节决策树与 ADR-003）。字段命名与 schemas（field.meta.schema.json 等）不变。

## 1. 标准数据包

每个截面包含 field.npz（测试阶段 NumPy 格式；生产可用 HDF5 但须适配）与 field.meta.json。NPZ 禁止 pickle 对象。数组至少含：

| 键 | 形状/单位 | 约束 |
|---|---|---|
| coords_m | (N,3), m | 全局坐标（单体模型默认全局，不再需要级联局部系） |
| E | (N,3), complex, V/m | 完整物理电场，不是未声明包络 |
| H | (N,3), complex, A/m | 完整物理磁场 |
| weights_m2 | (N,), m^2 | 有限正值，真实面积积分权重 |
| normal | (3,), 无量纲 | 单位法向；只接受同一平面固定法向 |
| Em/Hm | (M,N,3) | 同网格目标模式；M 至少覆盖 974 nm 实证的 HE11 两偏振；若存在弱导高阶，另存分类模式并单列 |

元数据至少：schema_version、case_id、quantity_kind=FULL_PHYSICAL_COMPLEX_FIELD、phasor=exp(+i*omega*t)、lambda_m（本阶段=974e-9 m）、frame_origin_m、frame_rotation_3x3、propagation_direction、plane_id、source_power_W、power_forward_W、power_backward_W（未知必须 null+reason）、coordinate_hash、quadrature_method、model_sha256、config_sha256、study_tag、dataset_tag、solution_index、expression_E/H、carrier_restoration、interpolation_method、units、generator_version、mode_classification。文件自身 SHA 记在外部制品清单。

v3 基线的 plane_id 清单（名称写入实际模型后以实录为准，禁止猜 tag）：
- source_plane：z=-gap 的源参考监测面（非求解边界，仅导出场）；
- monitor_apex（可选）：顶点附近 z=0- 监测面；
- mode_plane：下游均匀光纤截面（端口所在、离透镜足够远），HE11 模式与功率在此定义；
- port_boundary：Numeric Port 所在平面。

场和目标模式必须在同一物理面、同法向、同坐标与积分节点。重采样复数实/虚部而不是强度；相位可重置一个整体常数，不得逐像素对相位。面积积分用正确梯形/有限元权重；PML 内拉伸坐标场不用于真实功率积分；mode_plane 必须验证模式尾部捕获。

## 2. 带功率内积的投影（与 v2 一致）

无损互易同截面正向导模：B(u,v)=1/4*Int(E_u x H_v* + E_v* x H_u)·n dA。单模 Pm=B(m,m)，a=B(field,m)/Pm，Pmatched=|a|^2*Pm。多目标模式未功率正交时用 Gram：G_ij=B(mode_j,mode_i)，b_i=B(field,mode_i)，Ptarget=Re(b^H * G^-1 * b)。检查 G 近 Hermitian、正定、条件数合理；退化/重复模式拒绝，不用伪逆通过验收。

974 nm 近截止追加约束：目标子空间只含经 S02 模式识别确认的 HE11 两偏振；任何 LP11 类候选单独投影、单独入账，不得合并进 eta_HE11。该 B 内积不适用于有损/非厄米泄漏模与 PML 模；近截止下若候选模 Im(neff) 显著，先分类再投影，无法分类就记 null+原因。两偏振总功率基底无关；单偏振分量必须说明所选物理偏振基（本包 x/y）。

必做单测（包工具层，不启动 COMSOL）：自投影、正交偏振、整体相位不变、反向同形波（E 同/H 反）投影为 0、模式幅度缩放不改目标功率、可逆基变换后总功率不变、重复模式必须失败、错误法向/负权重/NaN 必须失败。

## 3. 传场/分段合同（仅受控分段 fallback 时生效）

基线单体模型不做级联，无 EWBE→EWFD 传场。若真实内存受阻后按受控流程分段（该分支需独立审查、对应 gate G10/G11a/G11b/G17 全部激活，见 VALIDATION.md），则完整执行 v2 第 3 节：指定物理参考面 → 导出完整 E/H 与原载波/单位 → 如含回反射先分离正向 → 将正向场变为接收模型可用的可微源表示 → 空域桥接 → 同一接收面比较幅相/功率/目标投影 → 再放入真实光纤。

推荐 PWE 桥接（对足够大均匀空气截面做已验证角谱分解，保留谱相位与正向 kz，横向矢量投影生成一致 H，在局部三维空气中以平面波和表达式重构 E(x,y,z)）。谱截断/有限窗/采样是额外误差，不得重新归一化抹去；重构前后保留绝对幅度。若用 COMSOL 散射场背景，三维 Ebackground 须在需要区域可微；不能把二维表通过 General Extrusion 等耦合算子直接设为背景 [C64_EWFD]。必须检查无散射体空域残差，而不是看材料外场“合理”。不得同时固定所有 E/H 边界分量造成超约束。G11b 只允许消去一个整体相位，仍需保存不消除整体相位的参考相位记录。

## 4. 旋转与前后向（定义保留，本阶段不求解倾斜）

本基线不含装调倾斜工况（S07 后移），但合同保留供后续：倾斜采用明确旋转矩阵，顺序固定记录；coords、E、H、法向、模式进入同一比较坐标，旋转中心为端面中心。平面全场 E/H 用一致角谱方向分解或已验证互易投影区分前后向；不得用净 Poynting 通量当入射源功率：存在反射时净通量=Pforward-Pbackward。源分母始终来自已知入射场的独立正向归一化。

## 5. 单体模型的反射分量导出

在 source_plane 与 mode_plane 分别导出 E/H 后，用角谱方向分解（或已验证互易投影）计算 Pforward/Pbackward 并写入 meta。楔面与端面反射在求解域内已包含；导出层只负责记账，不得再人为叠加反射。
