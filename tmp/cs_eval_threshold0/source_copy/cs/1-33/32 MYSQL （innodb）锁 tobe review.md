## 概述
分类：
1. 表锁
2. 行锁
3. 意向锁
4. 自增锁

行锁和表锁都支持共享锁（S）和排他锁（X）

## 表锁 LOCK_TABLE
### mysql server和innodb
mysql server和innodb都有实现，会对整个表加锁：
1. 仅当`autocommit=0`、`innodb_table_lock=1`时mysql server和innodb可以感知对方的表锁
2. 若不是这样设置，innodb将无法处理表级别锁的死锁

### 共享锁和排他锁
1. 如果当前线程加的是共享锁，只能进行读操作
2. 如果要进行写操作需要加排它锁


### 触发加表锁的情况
1. 手动加锁 LOCK TALBES table_name [READ | WRITE]
2. alter table语句
3. select for update时没有指定主键id

### 表锁和事务
1. 事务开始时会自动unlock之前的表锁
2. commit和rollback都不能自动解锁通过LOCK TALBES加的锁
3. `LOCK TALBES`时会先隐式提交事务，再锁表，`UNLOCK TALBES`也会隐式提交事务

==注意事项==
事务中需要的表锁必须在事务开头一次性获取，无法再事务中间获取，因为不管是`LOCK TALBES`还是`UNLOCK TALBES`都会提交事务

官方建议的使用方式：
```sql
SET autocommit=0;
LOCK TABLES t1 WRITE, t2 READ, ...;
... do something with tables t1 and t2 here ...
COMMIT;
UNLOCK TABLES;
```
## 意向锁
1. 一种特殊的表锁：取得行的共享锁和排它锁之前必须获取表的意向共享锁（IS）和意向排它锁（IX）
2. IS和IX添加的过程是自动的
3. 当存在写意向锁（IX）时，读写的表锁都加不上
4. 当存在读意向锁（IS）时，写的表锁加不上，读的可以加

意向锁存在的意义
1. 如果没有意向锁，为了添加表锁，必须遍历每个行锁，看下是否有冲突
2. ==意向锁相当于一个是否已经存在行锁的标志，用来避免遍历==
![[Pasted image 20210331190703.png|400]]

## 行锁LOCK_REC
innodb行锁的分类（隔离等级为RR时）：
1. 记录锁（record locks）
2. 间隙锁（gap locks）
3. 临键锁（next-key locks）
4. 插入意向锁（insert intention locks）

![[Pasted image 20210331145839.png|300]]

行锁的作用位置：
1. 索引
	1. sql操作主键索引，直接锁定聚簇索引
	2. sql操作非主键索引，先锁定非聚簇索引，再锁定聚簇索引
2. 索引间隙

触发加行锁的语句：
1. 写操作：Update、Delete、Insert
2. SELECT ... FOR SHARE | UPDATE 

### 记录锁（record locks）
锁定某个具体的索引：
1. 当SQL按照唯一性索引（Primary key、Unique key）进行数据检索时
2. 如果查询条件对应的数据存在，则加上记录锁
![[Pasted image 20210331114122.png|500]]
### 间隙锁（gap locks）
1. 当SQL检索的数据不存在，会加间隙锁
2. 锁住的是索引之间的间隙
3. 多个间隙锁可以共存，不区分共享和排它
4. 间隙锁的作用是防止幻读：其它的事务不能往间隙中添加新的数据

间隙锁的目的时禁止在这个间隙内写入数据，所以多个间隙锁的区间相互覆盖并不是问题，应为多个间隙锁的目标是一致的

![[Pasted image 20210331114239.png]]

### 临键锁（next-key locks）
1. 锁住索引本身和索引之间的间隙
2. ==SQL进行了非唯一索引的数据检索==
3. 如果查询没有命中任何索引，会给所有行添加临键锁，相当于锁表

因为是非唯一索引，即时锁住了单个行也保证不了重复的数据会插入，==所以将行和间隙一起进行锁定，这是和间隙锁的区别之处==
![[Pasted image 20210331141914.png|500]]

### 插入意向锁（insert intention locks）
1. 一种间隙锁形式的意向锁
2. 在执行insert之前设置
3. 解决间隙锁的并发问题

如何解决并发：
1. 在没有间隙锁存在的情况下，innodb允许两个事务同时提交insert请求，因为意向锁之间不会冲突
2. 如果存在一个间隙锁或临键锁，这时插入意向锁会被block，防止幻读

==TODO==：这块理解的不是很清楚，先放过

## 自增锁
1. 如果一个表的某个行具有`AUTO_INCREMENT`的列，则一个事务在插入记录到这个表的时候，会先获取自增锁
2. 如果一个事务持有自增锁，会阻塞其他事物对该表的插入操作，保证自增连续

## 和隔离等级的关系
区分快照度和当前读
快照读的RR基于[[32.5 MVCC]]就可以实现，不需要锁，只有当前读（update等dml）才需要锁的介入来保证

### SERIALIZABLE
1. 所有select会被隐式转换为SELECT ... FOR SHARE，阻塞其它写
2. 开启autocommit时不转换

### RC
1. 没有间隙锁，会导致幻读
2. 临键锁退化为记录锁
3. 在RR隔离级别下，加锁时如果查询条件没有命中索引，则会给表中每条记录都加上临键锁。而RC隔离级别下因为没有间隙锁，则会退化成给表中每条数据加上记录锁，并且还会把没有匹配的行上的锁给释放掉，而不是把全表所有记录不管有没有匹配都给锁上

### 死锁问题
[[32.1 mysql innodb 死锁问题]]

### select for update的加锁情况
以user id的查询为例
![[Pasted image 20220824112120.png]]
## ref
https://app.yinxiang.com/shard/s9/nl/1058287/5d5d2ebd-fe67-4a3d-bf98-b243f5a15b51