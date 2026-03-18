# CS Reference Evaluation Report

## Dataset
- kept_note_count: 139
- evaluation_note_count: 30
- dropped_note_count: 38

## Metrics
- dataset_note_count: 30
- avg_gt_links_per_note: 1.6000
- hit_at_5: 0.7667
- hit_at_10: 0.8333
- recall_at_5: 0.6444
- recall_at_10: 0.6944
- precision_at_5: 0.1867
- precision_at_10: 0.1098
- mrr: 0.4900
- coverage: 0.8333

## Worst Misses
- cs/34-98/89 分布式事务 总览.md: hits_10=0, misses_10=cs/34-98/90 rocketMQ 事务消息 两方事务.md,cs/34-98/91 XA 2PC 3PC.md
- cs/1-33/1.1 t-test t检验.md: hits_10=0, misses_10=cs/1-33/1 统计显著性.md
- cs/1-33/11 事件总线.md: hits_10=0, misses_10=cs/1-33/31 阿里云 DTS.md
- cs/1-33/32.2.1 全局二级索引.md: hits_10=0, misses_10=cs/34-98/91 XA 2PC 3PC.md
- cs/1-33/32.5 MVCC.md: hits_10=0, misses_10=cs/34-98/95 WAL 预写日志.md
- cs/1-33/30.1.2 数据库ACID.md: hits_10=1, misses_10=cs/34-98/91 XA 2PC 3PC.md,cs/34-98/95 WAL 预写日志.md
- cs/1-33/11.3 CQRS 命里和查询分离.md: hits_10=1, misses_10=cs/1-33/31 阿里云 DTS.md
- cs/1-33/19 监控报警.md: hits_10=1, misses_10=cs/1-33/22 混沌工程 故障注入.md
- cs/1-33/30.1 阿里云 DRDS(PolarDB-X).md: hits_10=1, misses_10=cs/34-98/91 XA 2PC 3PC.md
- cs/99-160/165 RTB & DSP.md: hits_10=1, misses_10=cs/99-160/163 eCPM的思路.md

## False Positives
- cs/1-33/1.1 t-test t检验.md: false_positives_10=cs/1-33/1.2 大数据分析的分类.md,cs/1-33/21 全链路压测.md,cs/1-33/26 shadow testing.md,cs/1-33/30.1.3.2 SQL 连接.md,cs/34-98/50 ROC AUC 准确率 召回率.md
- cs/1-33/11 事件总线.md: false_positives_10=cs/1-33/11.1 事件驱动 EDA.md,cs/1-33/11.3 CQRS 命里和查询分离.md,cs/1-33/21.1 背压 back pressure.md,cs/1-33/31.3 类kafka结构的问题.md,cs/34-98/71 DDD 下解决多个repo的分布式事务问题.md
- cs/1-33/32.2.1 全局二级索引.md: false_positives_10=cs/1-33/30.1 阿里云 DRDS(PolarDB-X).md,cs/1-33/30.1.0 分布式数据库.md,cs/1-33/30.1.2 数据库ACID.md,cs/1-33/30.2.10 hash分区和range分区.md,cs/1-33/31.3 类kafka结构的问题.md
- cs/1-33/32.5 MVCC.md: false_positives_10=cs/1-33/30.1.2 数据库ACID.md,cs/1-33/31.1 mysql bin log.md,cs/1-33/32 MYSQL （innodb）锁 tobe review.md,cs/1-33/32.1 mysql innodb 死锁问题.md,cs/1-33/32.4 隔离等级.md
- cs/34-98/89 分布式事务 总览.md: false_positives_10=cs/1-33/11 事件总线.md,cs/1-33/30.1.2 数据库ACID.md,cs/1-33/30.1.3 CAP.md,cs/34-98/71 DDD 下解决多个repo的分布式事务问题.md,cs/34-98/90.0 基于kafka的事物消息.md
- cs/1-33/10.2 ABAC 权限模型.md: false_positives_10=cs/1-33/10.1 DAC MAC.md,cs/1-33/11.2 六边形架构.md,cs/1-33/30.1.3.1 范式和反范式.md,cs/1-33/32.4 隔离等级.md,cs/34-98/70.3 BOUNDED CONTEXT（BC）的划分.md
- cs/1-33/11.3 CQRS 命里和查询分离.md: false_positives_10=cs/1-33/11.2 六边形架构.md,cs/1-33/12.0 分层架构.md,cs/1-33/12.9 依赖倒置DIP.md,cs/34-98/69 DDD简介 极简版.md,cs/34-98/69.1 DDD中领域的定义.md
- cs/1-33/19 监控报警.md: false_positives_10=cs/1-33/11 事件总线.md,cs/1-33/15 软件架构度量.md,cs/1-33/18.1 故障发现.md,cs/1-33/20 流量预案.md,cs/1-33/26 shadow testing.md
- cs/1-33/20 流量预案.md: false_positives_10=cs/1-33/18.1 故障发现.md,cs/1-33/19 监控报警.md,cs/1-33/21.1 背压 back pressure.md,cs/1-33/26 shadow testing.md,cs/1-33/26.1 dark launching.md
- cs/1-33/30.1 阿里云 DRDS(PolarDB-X).md: false_positives_10=cs/1-33/30.1.0 分布式数据库.md,cs/1-33/30.2 proxy的路由的思路.md,cs/1-33/30.2.10 hash分区和range分区.md,cs/1-33/30.5 阿里云 ADB.md,cs/1-33/31 阿里云 DTS.md
