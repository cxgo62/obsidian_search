---
{}
---

## 概览
- tinyLRU是一种cache准入策略
- 这种策略和cache的淘汰策略是正交的，可以适配很多淘汰策略

# LRU和LFU的缺点
LFU缺点：

第一，它需要给每个记录项维护频率信息，每次访问都需要更新，这是个巨大的开销；

第二，如果数据访问模式随时间有变，LFU的频率信息无法随之变化，因此早先频繁访问的记录可能会占据缓存，而后期访问较多的记录则无法被命中，LFU仅对分布稳定的请求是最优策略

LRU缺点：
不能很好地应对偶然的突发流量。比如一个数据在一分钟内的前59秒访问很多次，而在最后1秒没有访问，但是有一批冷门数据在最后一秒进入缓存，那么热点数据就会被冲刷掉。
大部分情况下，LRU需要更多的空间来实现和LFU一样的命中率

# LFU的一些改进
## WLFU 
只维护最近w次访问，需要维护一个访问序列编号
对分布动态变化的情况适应的更好

# W-TinyLFU

核心点：
1. 基于LFU的基本原理
2. 提供一种准入机制，只有满足这样的准入机制，才允许淘汰旧数据，进入新数据
3. 提供一种叫做tinyLFU的数据结构，在大样本量的情况下提供近似的LFU统计数据，同步保持这种额外统计的存储开销很小（百万级别的key只在一个page中）


![[Pasted image 20220622162353.png]]

## 数据结构
基本的思路是基于[[112.3 Spectral Bloom Filter （SBF）]]的改进

SBF很难实现总数为W这样一个限定

> 一种slide实现的方式：
> 1. 实现一组有顺序的多个SBF
> 2. 新数据总是写入第一个SBF
> 3. 当总数达到后，最后一个SBF淘汰，并且在头部加入一个新SBF
> 
> 缺点：有读放大的问题，需要读取每个SBF的计数并求和

### reset
当一个counter的计数达到最大值后，将所有的这一组hash对应的counter全部除以2

优势
1. 额外的开销很低
2. 对高频key的判断更加精确了 [证明](marginnote3app://note/303A48A2-3239-4CE2-BB5D-2089E2865E6A)

缺点：
1. 需要比较高频率的进行除2操作，但是现代硬件可以比较高效的执行
2. 在除2的时候会导致小数，引入一些额外的[删除错误](marginnote3app://note/FC6AB9B9-880D-439D-8BCF-79FFC82E7269)


### 空间优化
#### small counter
通过区分冷热key来优化每个counter的大小

- 因为总的窗口大小是W，所以单个key的最大也只能是W
- 因此每个counter需要使用log2W个bit来计数，这是一个很大的开销

一个前提：
- frequency histogram只需在一个潜在的被替换key和当前访问key之间做出选择
- frequency histogram不需要知道全局的key排序
- 构造一个大小为C的cache，使得所有访问频率超过1/C的key都在这个cache中，合理的假设所有的access次数之和是大于C的

通过区分热key和冷key，这样就把冷key的countersize降到了log2(W/C)，因为这里不会有超过W/C的计数
只有通过reset才能实现这样的优化机制，如果是上面的slide方式是无法这样优化的

#### doorkeeper
减少counter的总数，主要是减少大量长尾对象的影响

- 思路是大部分长尾对象使用counter这种多bit的数据结构是不划算的，可以退化到单bit的结构
- 实现的方式是在SBF前面加一层普通BF，这个普通的BF叫做doorkeeper

具体的过程
1. 当新请求到达时，如果在doorkeeper中不存在，则更新doorkeeper后直接返回
2. 如果在dookeeper中存在，再写入SBF
3. 查询时如果在doorkeeper中存在就在SBF的计数上再加一
4. 当执行reset操作时，清除对应的doorkeeper数据

缺点：doorkeeper中的1在reset中丢失，导致类似小数产生的删除错误

## 和cache的链接
tinyLFU作为一种准入策略是可以和cache任意链接的
但是因为reset的原因，需要将tinyLRU的reset和cache进行同步操作

# tinyLFU的缺点
对sparse bursts稀疏爆发的这种情况处理不太好，这种在存储服务器上比较常见

每一个突刺的流量来不及累积足够的频率就被淘汰掉了，照成重复miss

## 升级策略Window TinyLFU scheme (W-tinyLFU)
![[Pasted image 20220627164033.png]]
在普通tinyLFU cache的基础上再叠加一个总容量为主cache 1%的普通LRUcache，用来应付突发性的短时爆发请求