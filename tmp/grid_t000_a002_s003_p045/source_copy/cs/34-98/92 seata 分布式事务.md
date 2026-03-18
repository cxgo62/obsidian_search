## 概要
分布式事务的定义：包含多个分支事务，每个分支事务是一个local transaction

## 基础组件
### Transaction Coordinator(TC)
- 记录全局事务和分支事务的状态
- 控制全局的commit和rollback
### Transaction Manager(TM)
- 定义全局事务的生存周期：开始、提交、回滚
### Resource Manager(RM)
- 控制分支事务中的资源
- 和TC进行通信：注册分支事务，上报事务执行状态
- 控制分支事务的commit和rollback

![[Pasted image 20210317194821.png|500]]

## 流程
![[Pasted image 20210317194733.png|600]]

1. TM向TC申请开启一个全局事务，TC返回一个全局的XID作为事务id
2. XID会在微服务调用链上被传递，分发给所有的参与者
3. RM将本地事务注册到TC，使用XID作为标识
4. TM向TC提交特定XID的commit或rollback请求
5. 因为之前对应的RM在TC进行过注册，TC会保证每个RM都完成local事务的commit或rollback


## 几种模式
### AT模式
AT 模式基于local DB的ACID特性
-   一阶段 prepare 行为：在本地事务中，一并提交业务数据更新和相应回滚日志记录。
-   二阶段 commit 行为：马上成功结束，**自动** 异步批量清理回滚日志。
-   二阶段 rollback 行为：通过回滚日志，**自动** 生成补偿操作，完成数据回滚。

[[92.1 seata AT模式]]
### TCC模式
需要用户自己实现各个子服务的prepare，commit，rollback
[[92.2 seata TCC]]

### saga模式
saga是一种长事务的解决方案，基于状态机
[[92.3 seata SAGA]]

