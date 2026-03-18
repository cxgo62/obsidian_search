## 两方事务
基于rocketmq的事务消息

### half（prepare） message
消息被成功发送到rocketMQ后并不能立即被消费到，必须等待producer的二次确认

### 消息状态检查
在以下情况时二次确认的消息无法达到rocketMQ：
1. producer进程意外中断
2. 网络故障导致确认丢失
3. rocketMQ本身宕机了

rocketMQ会检查处于half message状态的所有消息，在设定的超时到达后会主动向producer发起一次查询，获得一个明确的状态：commit or rollback

procducer需要注册一个**TransactionCheckListener**方法，用于rocketMQ的主动查询

![[Pasted image 20210317160902.png]]

### 两方事务的总结
本质是利用了预提交这个动作来实现producer和roketMQ之间的最终一致

rocketMQ中的transactionMsg checkservice和TCC中的事务控制器是一样的原理，都是保证事务能够正常结束的手段

注意：在保证严格事务时，需要设定为同步刷盘

缺点：
如果后面的事务执行失败，没有机会对全面那个事务进行回滚，所以后面的事务必须要一定可以被成功执行

### 一个简单的多方事务方案
在不考虑延迟和性能的情况下，可以对两方事务进行级联，实现任意多的多方事务

### 另外一种实现事务消息的思路
[[90.1 基于发件箱模式的事务消息]]
### ref
[[rocketMQ transction message]]

