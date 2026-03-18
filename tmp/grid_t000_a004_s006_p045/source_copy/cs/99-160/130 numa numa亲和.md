# numa
- numa架构下，一个操作系统同时使用多个cpu和多组内存
- 一个物理cpu和一组内存构成一个node
- node之间可以相互访问内存，但是速度低于node内部的访问

# numa亲和
> 通过numactl启动程序，可以指定node绑定规则和内存使用规则。可以通过cpunodebind参数使进程使用固定node上的cpu，使用localalloc参数指定进程只使用cpu所在node上分配的内存。如果分配的node上的内存足够用，这样可以减少抖动，提供性能。如果内存紧张，则应该使用interleave参数，否则进程会因为只能使用部分内存而out of memory或者使用swap区造成性能下降


- 限定cpu只使用node内部的内存，从而降低跨node内存访问的开销
- 可以降低cpu的占用率
- node内部内存不足时会oom

## NUMA的内存分配策略
-   localalloc规定进程从当前node上请求分配内存；
-   preferred比较宽松地指定了一个推荐的node来获取内存，如果被推荐的node上没有足够内存，进程可以尝试别的node。
-   membind可以指定若干个node，进程只能从这些指定的node上请求分配内存。
-   interleave规定进程从指定的若干个node上以RR（Round Robin 轮询调度）算法交织地请求分配内存。

## ref
https://zhuanlan.zhihu.com/p/37444736

[OpenStack中的CPU绑核、NUMA亲和、大页内存](https://www.jianshu.com/p/eaf6a9615acc)