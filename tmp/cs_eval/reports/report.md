# CS Reference Evaluation Report

## Dataset
- kept_note_count: 139
- evaluation_note_count: 30
- dropped_note_count: 38

## Metrics
- dataset_note_count: 30
- avg_gt_links_per_note: 1.6000
- hit_at_5: 0.2333
- hit_at_10: 0.2333
- recall_at_5: 0.1750
- recall_at_10: 0.1750
- precision_at_5: 0.2000
- precision_at_10: 0.2000
- mrr: 0.2167
- coverage: 0.2333

## Worst Misses
- cs/1-33/18.1 故障发现.md: hits_10=0, misses_10=cs/1-33/19 监控报警.md,cs/1-33/21 全链路压测.md,cs/1-33/22 混沌工程 故障注入.md
- cs/1-33/30.1.2 数据库ACID.md: hits_10=0, misses_10=cs/34-98/91 XA 2PC 3PC.md,cs/34-98/95 WAL 预写日志.md,cs/目录/分布式事务index.md
- cs/目录/稳定性index.md: hits_10=0, misses_10=cs/1-33/18 稳定性建设思路.md,cs/1-33/20 流量预案.md,cs/1-33/21 全链路压测.md
- cs/目录/算法 index.md: hits_10=0, misses_10=cs/99-160/100 遗传算法GA.md,cs/99-160/106 拓扑排序.md,cs/99-160/107 最短路径.md
- cs/1-33/11.3 CQRS 命里和查询分离.md: hits_10=0, misses_10=cs/1-33/11 事件总线.md,cs/1-33/31 阿里云 DTS.md
- cs/1-33/19 监控报警.md: hits_10=0, misses_10=cs/1-33/21 全链路压测.md,cs/1-33/22 混沌工程 故障注入.md
- cs/1-33/30.1 阿里云 DRDS(PolarDB-X).md: hits_10=0, misses_10=cs/1-33/30 阿里云 RDS.md,cs/34-98/91 XA 2PC 3PC.md
- cs/34-98/89 分布式事务 总览.md: hits_10=0, misses_10=cs/34-98/90 rocketMQ 事务消息 两方事务.md,cs/34-98/91 XA 2PC 3PC.md
- cs/目录/架构 index.md: hits_10=0, misses_10=cs/1-33/11 事件总线.md,cs/1-33/15 软件架构度量.md
- cs/1-33/1.1 t-test t检验.md: hits_10=0, misses_10=cs/1-33/1 统计显著性.md

## False Positives
- cs/34-98/89 分布式事务 总览.md: false_positives_10=cs/34-98/92 seata 分布式事务.md,cs/34-98/92.2 seata TCC.md,cs/目录/分布式事务index.md
- cs/1-33/11.3 CQRS 命里和查询分离.md: false_positives_10=cs/1-33/11.2 六边形架构.md,cs/1-33/12.0 分层架构.md
- cs/1-33/32.4 隔离等级.md: false_positives_10=cs/1-33/30.1.2 数据库ACID.md,cs/1-33/32.5 MVCC.md
- cs/1-33/32.5 MVCC.md: false_positives_10=cs/1-33/32.1 mysql innodb 死锁问题.md,cs/1-33/32.4 隔离等级.md
- cs/1-33/10.2 ABAC 权限模型.md: false_positives_10=cs/目录/权限系统index.md
- cs/1-33/19 监控报警.md: false_positives_10=cs/1-33/18.1 故障发现.md
- cs/1-33/30.1 阿里云 DRDS(PolarDB-X).md: false_positives_10=cs/1-33/30.1.0 分布式数据库.md
- cs/99-160/139 BFF（Backends For Frontends）.md: false_positives_10=cs/目录/low code index.md
- cs/99-160/165 RTB & DSP.md: false_positives_10=cs/99-160/165.2 ssp 供给方平台.md
- cs/目录/low code index.md: false_positives_10=cs/99-160/139 BFF（Backends For Frontends）.md
