---
{}
---

# aggregate

aggregate的意义：解决一组对象在生存周期中的一致性问题，简单来说就是如何处理事物。

  

## 对aggregate的引用原则

外部对象只能持有aggregate的root，这个root有一个全局唯一的标识，所以应该有一个对应的repo来获取它，看起来会像是这样

```
class OuterObj {
	private Root root;
}

//appliction layer
obj = new OuterObj();
root = repoRoot.getRootById(id);
obj.setRoot(root);
```

  

外部对象可以通过root来获取内部对象进行临时（只读的）使用，但是持有内部对象是不允许的

```
class OuterObj {
	private Root root;
  private InnerObj innerObj; //not allowed
  
  func A() {
  	root.getInnerObj().xxMethod(); // 通过root来间接使用内部对象
    root.setInnerObj(newObj); //not allowed
  }
}
```

  

aggregate的boundary是单向透明的，内部对象可以持有外部的root，所以不是所有的操作全部收口到root。

  

# factory & repo

在ddd中，对象的生产和使用是两个完全独立的过程，需要被区分对待。entity等对象只需要考虑使用，儿不需要关心生产。所以如果一个对象的构造过于复杂，那么就应该存在单独的建模来支持这种构建，特别是当这个构建过程涉及到多个对象的创建和组合时。

本质上还是对复杂性进行分离，使用和生产不应该产生耦合。

  

factory和repo都是产生对象的方法，区别在于repo一般只负责简单对象的生产。因为repo的实现一般位于基建层，如果包含了过于复杂的创建逻辑，会导致领域知识的泄露，而factory就是将这种『生产知识』保留在领域层的方法。

  

非常简单的、纯内存的类的构建还是应该基于构造函数，保持代码精简。

  

## 典型的repo形式

n个读方法+1个写方法，和很多orm比较像，对象的修改一般也都是惰性的，只在save时真正写

```
A a = repoA.getAById1(id1)
A a = repoA.getAById2(id2)

repoA.save(a)
```

在实save方法时，需要通过判断id是否为空来决定是进行inert还是update操作，如果是insert还需要进行id的回写

  

也存在很多非标准的情况，例如架构那里讲的需要针对一些特别的批量操作单独新增repo的函数

  

一般会在领域层编写一个repo的interface，在基建层去写实现类。repo的抽象机制对测试是极其友好的，可以通过简单的替换repo的实现来实现数据mock

  

## aggregate的持久化问题

对于可以映射到外部存储的对象，factory的创建过程需要特别对待。

一般来说，在领域层中的factory不应该直接真的去操作数据库，所以当创建一个aggregate的时候，其实它只在内存中存在，并且缺乏一个真实的全局id

  

假设一个非常简单的场景，一个订单对象中包含一个物流对象，订单到物流记录单向关联，存在两个数据库表分配存放订单和物流记录，id就是各自的自增主键。

### 方法1

领域层factory的伪代码大概是这样

```
func createOrder() {
	order = new Order()
	logistics = new Logistics()
  order.setLogistic(logistics)
  return order
}
```

这会产生一个如下的没有和数据库实际关联的对象

![[Pasted image 20220414102328.png]]

然后应用层会去使用repo进行持久化，这是应用层factory的save方法

```
func saveOrder(Order order) {
  
  //begin transaction
  logisticRepo.save(order.getLogistic)
  //此时logistic已经具有真实的id
	orderRepo.save(order)
  //此时order具有真实的id  
  //commit
}
```

此时对象中的id已经被正确填充了

![[Pasted image 20220414102306.png]]

  

### 方法2

另一种方式是不接受这种id为0的假对象，order的组装会被提前到应用层

```
func createOrder(param) {
	//begin transaction
  logistic = new Logistic()
  logisticRepo.save(logistic)
  
  order = new Order()
  order.setLogistic(logistics)
  order.save
  //commit
  return order
}
```

  

这里两种方式order的组装逻辑都已经泄露到应用层，而且logistic本身作为一个非root对象是否需要对应的repo也是存疑的，虽然它在物理上确是有一个独立的表。

跨repo事物也是一个非常麻烦的问题，有一些业界实践（例如unit of work），但是实际使用起来还是会很麻烦，而且需要一些额外的框架开发。

  

### 方法3

最实用的方式还是直接放弃logisticRepo，直接将所有的order、logistic操作全部封装在orderRepo内部

领域层的实现同方法1，应用层实现如下：

```
func saveOrder(Order order) {
	orderRepo.save(order)
  //此时order具有真实的id  
  //此时logistic已经具有真实的id
}
```

事物在repo内部去实现，通过将一部分持久化逻辑泄露到基建层，整体的代码实现反而更简单了

  

但好像repo和factory的区分度更低了，因为repo中存在读取的方法

```
order = orderRepo.getOrderById(id)
```

  

这实际上和领域层的orderFactory在功能上完全重叠了，只是一个在建新对象，一个在读取旧对象，我们完全可以新建一个repo的方法来替代领域层的factory

```
order = orderRepo.createNewOrder(param)
```

这样所有的order创建逻辑就完全在repo中的，但这同样导致了很多的问题：

1.  订单的创建逻辑完全泄露了
    
2.  失去了惰性创建订单的能力
    

  

总体来说，对一个aggregate的持久化很难有一个绝对理想化的标准方式，更多的还是要更具业务场景去妥协和调整，选择业务逻辑在factory和repo中的位置，是一个不太容易的tradeoff的过程。