---
{}
---

## 为什么使用DDD
           DDD是一套设计哲学，但是包含了一份具体的操作手册
		   
![[Pasted image 20211214110952.png]]

DDD使用的场景
1. 业务复杂度
2. 需求反复变化，要求系统比较灵活

代价
1. DDD需要学习成本
2. 建模需要投入额外的工作量
3. 模型可能会失效，需要维护

收益
1. 一个更整洁的架构带来的可读性、维护性提升
2. 业务核心知识的沉淀
3. 开发成本的降低


## 如何操作
几个核心的点
1. 通用语言
2. 充血模型
3. 架构分层

### 通用语言
通用语言是一种“黑话”，代表各个角色对业务核心逻辑的一种共识

在我们的场景中，可能的通用语言包括Mainfeed，subTabFeed，Banner，TopicZone等等，通用语言中的词汇一般和代码中的建模（class)一一对应。

每个词汇代表核心业务中的一个场景或者事实，尽量不要使用太多泛化的词汇，这样模型的表现力会很弱，缺乏实际的价值


通用语言的发明，本质是一个对业务建模的过程，抽象出业务中的各个实体概念，并且对它们进行链接

通用语言发明的过程
1. 基于事件风暴的集中讨论，产生初步的概念
2. 对初步产生的模型反复打磨
3. 理想状态下邀请产品参与共建，达成各个角色理解的一致

## 充血模型
什么是贫血模型
1. 类只作为数据的容器
2. 只包含get set方法
3. 基本没有业务逻辑
```java
class Counter {
	private cnt;
	
	public int getCnt() {
		return cnt;
	}
	
	public setCnt(int newCnt) {
		cnt = newCnt;
	}	
}


func XX() {
	Counter counter = new Counter()
	
	//inc
	counter.setCnt(counter.getCnt()+1)
}
```

充血模型
1. 核心业务逻辑被收敛在类的内部
2. 具有有具体业务含义的方法名，可以被无负担的使用
```java
class Counter {
	private cnt;
	
	public int getCnt() {
		return cnt;
	}
	
	public IncOneCnt() {
		cnt++;
	}	
}
```

充血模型的好处
1. 充血模型是一种高内聚的实现，业务逻辑都被统一管理在内部了，相对于散落在各处，维护成本会低很多
2. 应为细节被封装在内部，且对外提供一个明确的无副作用的方法，这样大大降低了这个类的使用者的心智负担
3. 更容易完成单元测试

## 架构分层
最基础的划分
1. interface
2. application
3. domain
4. infrastructure

interface：
简单的数据适配，一个简单的场景是我们对于同一套业务逻辑，我们的输入可能来自rpc、http、离线消息，interface层的存在可以对这些不同来源的数据格式做转换，给下一层提供一个统一格式的输入
这个感觉类似于controller的定位

application：
这一层只包含非常弱的业务逻辑，大部分时候是对象的存取和简单组合
一个例子
```java

func xxApp(req) {
	A a = aRepo.getById(req.aId)
	A b = bRepo.getById(req.bId)
	
	b.xxx(a)
	
	brepo.Save(b)
	
	return b
}

```
这个感觉和service类似，区别不同的是我们现在的service中包含了application和domain的部分，没有区分开

domain：
最核心的业务建模，应该包含各种充血模型的类，application层是对domain的组合调用


infrastructure：
基建层：数据库，消息中间件，rpc
简单来说就是各种repoImpl，gatewayImpl，clientImpl

一般repo的interface在domain，impl在interface


六边形架构
1. 基础架构的一种变换，是一种对称架构
2. 具体请参考<实现领域驱动涉及>


## 我们怎么落地DDD
1. 核心：建立基础模型（通用语言），完成业务架构建模
2. 对现有的架构进行微调，支持DDD的结构
3. 效验证和切流