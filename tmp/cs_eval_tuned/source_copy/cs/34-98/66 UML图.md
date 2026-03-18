## 类图
类之间的几种关系
- 泛化 Generalization
- 实现 Realization
- 关联 Association
- 聚合 Aggregation
- 组合 Composition
- 依赖 Dependency

强弱关系
泛化 = 实现 > 组合 > 聚合 > 关联 > 依赖

### 泛化
泛化就是继承
```plantuml
parent_class <|-- child_class
```

### 实现
实现一个接口
这个是虚线，泛化是实线
```plantuml
interface <|.. class
```

### 组合/组成
- 整体和部分的关系，部分不能离开整体单独存在
- 属于一种关联关系，是所有关联关系中最强的

对不能独立存在的理解：
1. 整体需要控制部分的生命周期，扶着其创建和销毁
2. 例如公司和部门之间的关系

```plantuml
公司 *--> 部门
```

### 聚合
- 和组合的区别在于部分可以脱离整体单独存在
- 例如汽车和轮胎，整体无法控制部分的生命周期
- 在编码上和组合具有相同的形式，只是业务含义上的分别

```plantuml
汽车 o-- 轮胎
```


### 关联
- 比组合，聚合更弱的一种关系
- 感觉就是对象之间相互保存了对方的对象，但是对象个人本身都是独立而完整的概念
- 比如老师和学生，老师需要管理学生，所以成员变量中有student list，但老师并非由student构成
- 用箭头来表示单向还是双向，用*号来表示对应到多个

```plantuml
老师 <-> 学生
```


### 依赖
- 一种使用关系
- 一个类的实现需要其它类的协助
- 应该是一个单向的关系，指向被使用的一方

```plantuml
人 ..> 电脑
```


## ref
https://www.cnblogs.com/jiangds/p/6596595.html
https://plantuml.com/zh/class-diagram