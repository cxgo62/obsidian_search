shadow testing

## 简介

一种使用线上流量来验证新版本系统的方法，非常类似于之前想在中视频实现的那种流量diff能力

基本的流程

1.  转发线上请求到shadow-deployment
    
2.  shadow-deployment执行请求，但是不返回结果
    
3.  对比两个系统的执行结果的diff
    
![[Pasted image 20220714155641.png]]

它基于了混沌工程的基础原理

> Systems behave differently depending on environment and traffic patterns. Since the behavior of utilization can change at any time, sampling real traffic is the only way to reliably capture the request path. To guarantee both authenticity of the way in which the system is exercised and relevance to the current deployed system, Chaos strongly prefers to experiment directly on production traffic

  

有一种类似的开发模式：[darklaunching](https://martinfowler.com/bliki/DarkLaunching.html)

  

## 框架，diff

diffy，envoy都支持了shadow testing这种方式

  

diffy基于的是一种网关转发的方案 [https://github.com/opendiffy/diffy](https://github.com/opendiffy/diffy)

  ![[Pasted image 20220714155631.png]]

diffy解决diff的方式

1.  同时跑三个服务。两个旧的，一个新的
    
2.  两个旧服务之间会一些diff，这种diff会被判定为噪音
    
3.  新旧之间的diff减去噪音就是我们需要的真实的diff