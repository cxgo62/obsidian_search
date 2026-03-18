# CS Reference Evaluation Report

## Dataset
- kept_note_count: 139
- evaluation_note_count: 30
- dropped_note_count: 38

## Metrics
- dataset_note_count: 30
- avg_gt_links_per_note: 1.6000
- hit_at_5: 0.4667
- hit_at_10: 0.5000
- recall_at_5: 0.4111
- recall_at_10: 0.4278
- precision_at_5: 0.2250
- precision_at_10: 0.2201
- mrr: 0.3561
- coverage: 0.5000

## Worst Misses
- cs/1-33/30.1.2 数据库ACID.md: hits_10=0, misses_10=cs/34-98/91 XA 2PC 3PC.md,cs/34-98/95 WAL 预写日志.md,cs/目录/分布式事务index.md
- cs/目录/稳定性index.md: hits_10=0, misses_10=cs/1-33/18 稳定性建设思路.md,cs/1-33/20 流量预案.md,cs/1-33/21 全链路压测.md
- cs/目录/算法 index.md: hits_10=0, misses_10=cs/99-160/100 遗传算法GA.md,cs/99-160/106 拓扑排序.md,cs/99-160/107 最短路径.md
- cs/1-33/19 监控报警.md: hits_10=0, misses_10=cs/1-33/21 全链路压测.md,cs/1-33/22 混沌工程 故障注入.md
- cs/1-33/30.1 阿里云 DRDS(PolarDB-X).md: hits_10=0, misses_10=cs/1-33/30 阿里云 RDS.md,cs/34-98/91 XA 2PC 3PC.md
- cs/34-98/89 分布式事务 总览.md: hits_10=0, misses_10=cs/34-98/90 rocketMQ 事务消息 两方事务.md,cs/34-98/91 XA 2PC 3PC.md
- cs/目录/架构 index.md: hits_10=0, misses_10=cs/1-33/11 事件总线.md,cs/1-33/15 软件架构度量.md
- cs/1-33/1.1 t-test t检验.md: hits_10=0, misses_10=cs/1-33/1 统计显著性.md
- cs/1-33/11 事件总线.md: hits_10=0, misses_10=cs/1-33/31 阿里云 DTS.md
- cs/1-33/20 流量预案.md: hits_10=0, misses_10=cs/1-33/21 全链路压测.md

## False Positives
- cs/1-33/11.3 CQRS 命里和查询分离.md: false_positives_10=cs/1-33/11.2 六边形架构.md,cs/1-33/12.0 分层架构.md,cs/1-33/12.9 依赖倒置DIP.md,cs/34-98/69 DDD简介 极简版.md,cs/34-98/69.1 DDD中领域的定义.md
- cs/1-33/32.5 MVCC.md: false_positives_10=cs/1-33/30.1.2 数据库ACID.md,cs/1-33/32 MYSQL （innodb）锁 tobe review.md,cs/1-33/32.1 mysql innodb 死锁问题.md,cs/1-33/32.4 隔离等级.md,cs/34-98/35 悲观锁乐观锁.md
- cs/99-160/165 RTB & DSP.md: false_positives_10=cs/99-160/109 内存分配基础.md,cs/99-160/109.1 排名算法 热榜算法.md,cs/99-160/112.1  Approximate Counting Architectures.md,cs/99-160/112.2 counting bloom filter（CBF）.md,cs/99-160/160 广告有效性模型.md
- cs/1-33/31 阿里云 DTS.md: false_positives_10=cs/1-33/11.3 CQRS 命里和查询分离.md,cs/1-33/30.1 阿里云 DRDS(PolarDB-X).md,cs/1-33/30.1.0 分布式数据库.md,cs/1-33/30.5 阿里云 ADB.md,cs/1-33/31.1 mysql bin log.md
- cs/34-98/89 分布式事务 总览.md: false_positives_10=cs/1-33/11 事件总线.md,cs/1-33/30.1.2 数据库ACID.md,cs/34-98/92 seata 分布式事务.md,cs/34-98/92.2 seata TCC.md,cs/34-98/92.4 编制（orchestration）和编排（choreography）.md
- cs/目录/缓存index.md: false_positives_10=cs/99-160/112.1  Approximate Counting Architectures.md,cs/99-160/112.1.0 bloom filter.md,cs/99-160/112.1.1 Bloom filter principle.md,cs/99-160/112.3 Spectral Bloom Filter （SBF）.md,cs/99-160/112.5 cm-sketch.md
- cs/目录/高并发 index.md: false_positives_10=cs/1-33/11.3 CQRS 命里和查询分离.md,cs/1-33/30.1 阿里云 DRDS(PolarDB-X).md,cs/1-33/30.1.0 分布式数据库.md,cs/1-33/30.2.1 负载均衡策略（前端服务器）.md,cs/1-33/31 阿里云 DTS.md
- cs/1-33/19 监控报警.md: false_positives_10=cs/1-33/18.1 故障发现.md,cs/34-98/50 ROC AUC 准确率 召回率.md,cs/99-160/112.1.1 Bloom filter principle.md,cs/目录/稳定性index.md
- cs/1-33/30.1 阿里云 DRDS(PolarDB-X).md: false_positives_10=cs/1-33/30.1.0 分布式数据库.md,cs/1-33/31 阿里云 DTS.md,cs/1-33/32 MYSQL （innodb）锁 tobe review.md,cs/目录/高并发 index.md
- cs/1-33/32.2.1 全局二级索引.md: false_positives_10=cs/1-33/30.1 阿里云 DRDS(PolarDB-X).md,cs/1-33/30.1.0 分布式数据库.md,cs/1-33/30.1.2 数据库ACID.md,cs/1-33/30.2.10 hash分区和range分区.md
