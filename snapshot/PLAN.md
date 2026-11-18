# 执行计划 v3.0 | 单基线关键路径与并行边界

S00 环境与 S01 输入可并行独立推进。S02 模态与 S03 源可作为同一规范模型内的 study 或由不同 agent 在辅助工作副本上并行推进；触及同一 .mph 或同一 COMSOL server 会话时必须串行、单写入者。S04→S05→S06 为关键路径（局部入纤能力 → 单模型注入/域可行性 → 完整规范模型）。S09 在 S06 基线通过之后。S07/S08 本版后移，不排入本包执行队列。

| 阶段 | 详细步骤 | 本版必须形成的增量 |
|---|---|---|
| S00 | docs/stages/S00_ENV.md | 6.4 真实环境/MCP 能力记录 + 最小模型读写重开 + 复场导出能力证明（G16） |
| S01 | docs/stages/S01_INPUTS.md | 974 冻结配置、原件 SHA 核对、974 解析参考、fail-closed 检查与 case 表（G01/G02） |
| S02 | docs/stages/S02_MODES.md | 974 nm 真实本征模 study：HE11 子空间 + 近截止高阶候选 + 网格/域收敛（G04a/b） |
| S03 | docs/stages/S03_SOURCE.md | 974 矢量角谱源生成器 + 功率/FWHM 验证 + 可微背景场输出（G03a/b） |
| S04 | docs/stages/S04_RECEIVER.md | 平端局部 EWFD：B1/B2/B3 能力基准 + BASE/LAT1 直接入纤 + 账本闭合（G05a/b、G06a/b） |
| S05 | docs/stages/S05_TRANSFER.md | 单模型注入与全域网格/PML 可行性（G17；G10/G11a/b NOT_APPLICABLE 登记） |
| S06 | docs/stages/S06_LENSES.md | 一体化楔形圆弧纤端规范模型求解：效率、账本、反射范围（G07a/G14） |
| S07 | docs/stages/S07_TOLERANCE.md | 本版不执行（DEFERRED，激活条件与保留规程见文内） |
| S08 | docs/stages/S08_SPECTRUM.md | 本版不执行（DEFERRED，974 单波长即本版工况） |
| S09 | docs/stages/S09_RELEASE.md | 代表工况最终三网格/域验证、清空解重算、独立审查、单模型制品可取回（G08/G09/G15/G18/G19/G20） |

共同出口（每阶段）：可重跑的建模源码/MCP 调用序列、冻结参数、真实模型/数据制品、自动检查、独立审查、同步记录。本包当前 LOCAL_ONLY，上层工作树已有历史 origin，公开上传范围待确认；独立解压后须重新核对，不虚构上传。文件与 case 命名用阶段/工况 id（基线 case_id：LD974-WEDGE-BASE-001；LAT1 派生 case 按参数哈希生成）。

命令契约贯穿全程：python -m tools.preflight 与 python -m unittest discover -s tests -v。两者只在软件层生效，任何阶段不得用其绿灯替代 COMSOL 证据。

里程碑逐步释放结果，不预先铺开设定点：本版只有 BASE + LAT1 两个 case，不存在"先跑网格再补物理验证"的路径；也不得为对比而临时增加工况（须 ADR）。

阅读路径：AGENTS.md → REQUIREMENTS.md → 本文件 → NEXT.md → 当前 Sxx 文档；建模前必读 PHYSICS.md、FIELD_CONTRACT.md、COMSOL64_IMPLEMENTATION.md、VALIDATION.md（整合修订版）；执行纪律见 EXECUTION_AND_RECOVERY.md；上传矩阵见 GITHUB.md（远端未确认前只记录不执行）。
