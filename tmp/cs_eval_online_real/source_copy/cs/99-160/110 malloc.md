[[109 内存分配基础]]
## malloc
malloc的本质是在内存中找到一块给定size的逻辑上连续内存，返回指针，并提供释放这块内存的能力
### api
```c
 void *malloc(size_t size);  
 void free(void *ptr);  
 void *calloc(size_t nmemb, size_t size);  
 void *realloc(void *ptr, size_t size);
```
### malloc的实现
1. 将内存空间以block的形式组织起来
2. 每个block包含meta和数据两个区
3. meta包含：数据区大小，空闲标志，下一个数据区的地址
4. 数据区的第一个字节就是malloc返回的指针

最基础的block定义
```c
typedef struct s_block *t_block;
struct s_block {
	size_t size; /* 数据区大小 */ 
	t_block next; /* 指向下个块的指针 */
	int free; /* 是否是空闲块 */
	int padding; /* 填充4字节，保证meta块长度为8的倍数 */
	char data[1] /* 这是一个虚拟字段，表示数据块的第一个字节，长度不应计入meta */ };

```
![[Pasted image 20211109153926.png|500]]

### block的分配
找到一个空闲的，且size大于申请大小的block
1. first fit：从头开始找，选取第一个符合要求的block，效率高
2. best fit：从头开始找，选取blocksize和申请空间diff最小的block，碎片少

如果找不到符合的block，就在尾部新建一个block

分裂block
如果一个block在分配后剩余的数据区还很大，会对改block进行拆分，减少碎片，配合first fit使用
![[Pasted image 20211109154625.png|500]]

当size不为8时，会按8进行对齐

### free
free需要解决的问题
1. 传入的指针是否有效
2. 如何解决碎片的问题

有效性
1. 指针的地址在firstblock和break之间
2. 这个指针是通过自己的malloc分配的

判断是否是自己分配的内存
	- 方案1：在之前的block meta中添加一个magic number
	- 方案2：meta中添加一个magic pointer，指向数据区的第一个字节???==数据区的第一个字节不就是data？==

	
碎片
多次malloc和free之后，因为block本身可能分裂，所以会留下很多小的碎片block
1. free合并策略：当free一个block时，如果和它相邻的block也处于free状态，会和相邻的block进行合并，这需要==在meta中添加双向的指针==

## ref
malloc https://www.cnblogs.com/Commence/p/5785912.html