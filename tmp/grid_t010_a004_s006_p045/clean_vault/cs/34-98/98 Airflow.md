---
{}
---

## 概要
[airflow](https://airflow.apache.org/docs/apache-airflow/stable/index.html)是一个基于DAG编排的任务流引擎，适用的场景：

1.  流程相对固定，变化比较少：**流程变化 VS 表单变化**
2.  airflow解决的是子任务之间的依赖关系，辅助解决一些task之间的数据流动，不要将airflow用成storm，它不适合解决流处理场景的问题

airflow应该是一种[[92.4 编制（orchestration）和编排（choreography）#Orchestration 编制|Orchestration]]

## 核心概念

### DAG

一个python文件，用来描述一个workflow，airflow会加载特定文件夹下的py文件

文件中包含的主要内容：

1.  基于crontab语法的执行规则
2.  task的定义
3.  task的连接

### task/operator

1.  workerflow中的一个任务节点，可以粗略的理解为一个预先写好的python函数，对比图计算中的算子的概念
2.  sensor是一个特别的算子，用来等待一个外部事件的触发：时间事件、文件事件、其它workflow状态变化
3.  operator之间相互连接，构成一个DAG

first\_task >> second\_task >> \[third\_task, fourth\_task\]

![[Pasted image 20210617192331.png]]

每个task的执行都是独立的，但处于downstream的task必须等待upstream的task执行完毕才会被调度执行（有一些配置可以绕开这种限制）

task之间也可以传递数据（基于Xcom），一般是传递一个存放元数据的map

利用不同的operator可以实现排它网关、并行网关、混合网关

operator是一个静态的概念，类似于image，task是operator的一次run，类似于container，是一个动态的概念

一个task会经历一些状态的变化，类似于：

\`none\` ->\`scheduled\`-> \`queued\`->\`running\`->\`success\`

## 架构

组件：

1.  **scheduler**

触发并调度workflow，将task分配到对应的excutor上执行

2.  **executor/worker**

负责实际的task的运行，excutor位于分布式的多个worker上

3.  DAG文件的folder，被其它的组件读取
4.  一个metadata的数据库，被其它组件读取
5.  webserver

![[Pasted image 20210617192402.png]]

## 优缺点

优势：

1.  简单上手快，熟悉Python的话可以快速构建一个workflow，学习曲线很友好
2.  自带webserver，功能很强大，日常管理分析足够使用
3.  原生分布式任务调度

劣势：

1.  没有DSL，只能用python构建workflow，可以自己实现一个简单的DSL，成本不会太高，也有一些开源的方案可以参考。可以考虑使用[dolphinscheduler](https://dolphinscheduler.apache.org/zh-cn/)作为替代方案，dolphinscheduler原生支持dsl
2.  不是很适合作为事件驱动架构的执行引擎，airflow的主力场景还是在类etl任务上
3.  整体的架构复杂度还是比较高，运维容易踩坑

# ref

其它的workflow框架

[netflix conductor](https://netflix.github.io/conductor/) _Orchestration模式的_微服务编排框架，使用json形式的DSL进行task和workflow的描述，核心是一个状态机和一个task queue

[activiti](https://www.activiti.org/) 基于bpmn2.0，比较重

[几种主流框架的对比](https://blog.csdn.net/weixin_40954107/article/details/103136579)