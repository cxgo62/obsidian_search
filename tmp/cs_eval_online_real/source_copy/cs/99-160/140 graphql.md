## 概览
graphql是一种给前端使用的编排语言，可以将BFF（Backends For Frontends）的工作交给前端自行完成

整体还是一种服务编排的思路，后端提供一些数据选项，前端通过一个DSL描述出他们需要那些字段

这样后端只需要提供一个处理DSL的接口，就可以让前端自行实现他们的数据需求，防止接口爆炸，将后端从拼api这样的繁琐工作中释放出来

## ref
https://tech.meituan.com/2021/05/06/bff-graphql.html
https://netflix.github.io/dgs/getting-started/
https://zhuanlan.zhihu.com/p/460593348