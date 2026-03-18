## 概述
1. csp和actor是两种解决并发问题的编程模式
2. actor模式的代表是erlang
3. csp模式的代表是golang

==本质就是点对点通信和发布订阅的区别==

## actor
![[Pasted image 20210406181105.png|300]]

1. actor模式中，每个参与者被称作一个actor
2. actor之间直接交换消息，不通过中介
3. actor的内部对外界不可见，外界能影响actor的手段只能是向它发消息
4. 每个actor有一个理论上无限大的收件箱，所以外部向actor发消息时永远不会阻塞，可以认为是全异步消息

## csp
Communicating Sequential Processes
1. 参与者之间不相互联系
2. 通过channel进行发送和接收的解耦合

![[Pasted image 20210406185351.png|300]]

## 区别
1. 类似于点对点通信和消息中间件的区别
2. actor模式的耦合很强，每个actor都需要知道具体的发送接收者
3. csp是一种低耦合模式，类似发布订阅
4. 如果csp的channel无buffer，那么csp可以认为是同步交换信息的，但是actor一定是异步交换信息（基于收件箱）
5. csp的channel在无buffer下更为节省存储，actor理论上需要无限的存储空间来缓存消息


