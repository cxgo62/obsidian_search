对一个很大的数据集进行百分位计算很困难，通过降低时间精度或者合并单机数据的方式在数学上是无效的（所以为什么实现一个超大数据集的avg很容易，因为可以直接用map reduce）
[[DDIA]]中提到了几种近似算法：
1. forward decay
2. t-digest
3. HdrHistogram

## es如何处理百分位计算
Elasticsearch支持两种近似算法
1. cardinality，基于[[112.4 hyper log log]]实现基数统计
2. percentiles，基于t-digest实现百分位统计

### t-digest
- t-digest的特性是对于极端的百分位估计要更准确，所有对p99的估算精度会大于p50，符合大部分的业务场景
- 被 ElastichSearch、Spark 和 Kylin使用

> TDigest 使用的思想是近似算法常用的 Sketch，也就是素描，用一部分数据来刻画整体数据集的特征，就像我们日常的素描画一样，虽然和实物有差距，但是却看着和实物很像，能够展现实物的特征


核心思想：
1. 对数据进行采样。通过对每一段数据进行合并，得到一个[avg,cnt]的坐标（质心数），通过这种方式完成对原有的概率密度图的采样
2. 质心数相当于一个规模小很多的采样集合，大幅降低了计算的难度
3. 通过控制这种聚合的粒度，可以实现精度和计算开销的平衡
有一个开源实现 [https://github.com/tdunning/t-digest](https://github.com/tdunning/t-digest)

## 并发计算
timescale的实现：
![[Pasted image 20221019114233.png|400]]
如何并发的计算百分位
- 大部分分布式集群涉及到多个节点的数据，前面提到，单纯的对每个节点的Percentiles计算是没有意义的
- 更合理的方式是==进行直方图的叠加==。我们可以利用t-digest进行采用，得到一个单机的直方图，这个直方图的数据量可控，让后在聚合各个节点的直方图（概率密度图）
## ref
https://cloud.tencent.com/developer/article/1815080

https://www.timescale.com/blog/how-percentile-approximation-works-and-why-its-more-useful-than-averages/




