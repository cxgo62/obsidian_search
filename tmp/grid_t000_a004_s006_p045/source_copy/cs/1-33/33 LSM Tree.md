## 概论
- 传统的b+数是在磁盘上实现了一个类似跳表的结构，用来索引文件
- lsm tree跳出了这个思路，==它基于的一个假设是旧的数据会很少被用到，主要读取的都是新写入的数据==
- 基于这样的假设，对存储做了分层、分块，每一块都是有序的排列，通过简单的二分查找就可以快速定位到数据

b+树中，新旧数据的读取性能是平等的，但是lsm tree新数据的读性能会远强于旧数据


以[[level db]]基于lsm tree

特点：
1. 适合大量写的场景，比如日志记录
2. 读性能不佳

LSM tree写性能好的原因：
1. 写入到内存和redo log就可以返回，磁盘写是顺序写
2. compaction的时候都是顺序写

存在的问题：
1. 如果数据已经下沉到很深，读取的开销和速度非常高
2. 需要配合使用cache和布隆过滤器，否着查询效率很低
3. 存在读放大（一层层找）和空间放大（存在历史的过期数据）的问题
4. compaction在解决读放大的同时也引入了写放大 [[RockDB 写放大简单分析]]

## 组件
1. redo log，用来回放
2. memtable 内存数据库
3. immutable memtable 被冻结的内存数据库
4. sstable 持久化到磁盘的数据库文件

## 过程
写入：
1. 先写redo Log，再写memtable，数据存储在内存中就直接返回
2. memtable被写满后会变为immutable memtable，新数据会写入新建的memtable中
3. minor/major compaction

读取：
按memtable-》immutable memtable -》 sstable（从低层到高层）的顺序读取

## compaction的过程
[[level db#compaction]]

## 缺点
1. 底层数据的读取性能非常差，这一点很容易被攻击，需要额外的保护策略，如cache，布隆过滤器等
2. 读写放大都比较大，对ssd不友好


