# 用 Python 实现简易版本 EVM 

## 1. Hello Opcodes

## 2. 数据操作指令

## 3. 跳转指令

## 4. 条件指令

## 5. 比较指令

## 6. 位级指令

EVM 中用于位级运算的 8 个指令，包括AND（与），OR（或），和XOR（异或）。并且，我们将在用 Python 写的极简版 EVM 中添加对他们的支持。

1. `AND`：对两个值进行按位与操作，它的操作码为`0x21`，gas消耗为3。
2. `OR`：对两个值进行按位或操作，它的操作码为`0x22`，gas消耗为3。
3. `XOR`：对两个值进行按位异或操作，它的操作码为`0x20`，gas消耗为3。


## 7. 内存指令

EVM中用于内存（Memory）操作的4个指令，包括MSTORE，MSTORE8，MLOAD，和MSIZE。我们将在用Python写的极简版EVM中添加对这些操作的支持。

1. `MSTORE`：将内存中的数据存储到指定的位置，它的操作码为`0x52`，gas消耗为3。
2. `MSTORE8`：将内存中的数据存储到指定的位置，它的操作码为`0x53`，gas消耗为3。
3. `MLOAD`：从内存中加载数据到栈顶，它的操作码为`0x51`，gas消耗为3。
4. `MSIZE`：返回内存的大小，它的操作码为`0x54`，gas消耗为3。
    
## 8. 存储（Storage）

EVM中用于存储（Storage）操作的2个指令：SSTORE和SLOAD。并且，我们将在用Python写的极简版EVM中添加对这些操作的支持。

EVM存储和内存不同，它是一种持久化存储空间，存在存储中的数据在交易之间可以保持。它是EVM的状态存储的一部分，支持以256 bit为单位的读写。

由于存储使用键值对存储数据，每个键和值都是256 bit，因此我们可以用Python内置的dict（字典）来代表存储：

```python
def __init__(self, code):
    self.code = code
    self.pc = 0
    self.stack = []
    self.memory = bytearray()  # 内存初始化为空
    self.storage = {}  # 存储初始化为空字典
```

对存储的读取（SLOAD）和写入（SSTORE）都需要gas，并且比内存操作更昂贵。这样设计可以防止滥用存储资源，因为所有的存储数据都需要在每个以太坊节点上保存。

## 9. 控制流指令

EVM中用于控制流的5个指令，包括STOP，JUMP，JUMPI，JUMPDEST，和PC。我们将在用Python写的极简版EVM中添加对这些操作的支持。

作用：这些操作为合约提供了控制流程的能力，为编写更复杂的合约逻辑提供了可能。


## 10. 区块信息指令
EVM中用于查询区块信息的9个指令，包括BLOCKHASH，COINBASE，PREVRANDAO等。我们将在用Python写的极简版EVM中添加对这些操作的支持。

下面，我们介绍这些区块信息指令：

1. `BLOCKHASH`: 查询特定区块（最近的256个区块，不包括当前区块）的hash，它的操作码为`0x40`，gas消耗为20。。它从堆栈中弹出一个值作为区块高度（block number），然后将该区块的hash压入堆栈，如果它不属于最近的256个区块，则返回0（你可以使用`NUMBER`指令查询当前区块高度）。但是为了简化，我们在这里只考虑当前块。

    ```python
    def blockhash(self):
        if len(self.stack) < 1:
            raise Exception('Stack underflow')
        number = self.stack.pop()
        # 在真实场景中, 你会需要访问历史的区块hash
        if number == self.current_block["number"]:
            self.stack.append(self.current_block["blockhash"])
        else:
            self.stack.append(0)  # 如果不是当前块，返回0
    ```


2. `COINBASE`: 将当前区块的coinbase（矿工/受益人）地址压入堆栈，它的操作码为`0x41`，gas消耗为2。

    ```python
    def coinbase(self):
        self.stack.append(self.current_block["coinbase"])
    ```

3. `TIMESTAMP`: 将当前区块的时间戳压入堆栈，它的操作码为`0x42`，gas消耗为2。

    ```python
    def timestamp(self):
        self.stack.append(self.current_block["timestamp"])
    ```

4. `NUMBER`: 将当前区块高度压入堆栈，它的操作码为`0x43`，gas消耗为2。

    ```python
    def number(self):
        self.stack.append(self.current_block["number"])
    ```

5. `PREVRANDAO`: 替代了原先的`DIFFICULTY`(0x44) 操作码，其返回值是beacon链随机性信标的输出。此变更允许智能合约在以太坊转向权益证明(PoS)后继续从原本的`DIFFICULTY`操作码处获得随机性。它的操作码为`0x44`，gas消耗为2。

    ```python
    def prevrandao(self):
        self.stack.append(self.current_block["prevrandao"])
    ```

6. `GASLIMIT`: 将当前区块的gas限制压入堆栈，它的操作码为`0x45`，gas消耗为2。

    ```python
    def gaslimit(self):
        self.stack.append(self.current_block["gaslimit"])
    ```

7. `CHAINID`: 将当前的[链ID](https://chainlist.org/)压入堆栈，它的操作码为`0x46`，gas消耗为2。

    ```python
    def chainid(self):
        self.stack.append(self.current_block["chainid"])
    ```

8. `SELFBALANCE`: 将合约的当前余额压入堆栈，它的操作码为`0x47`，gas消耗为5。

    ```python
    def selfbalance(self):
        self.stack.append(self.current_block["selfbalance"])
    ```

9. `BASEFEE`: 将当前区块的[基础费](https://ethereum.org/zh/developers/docs/gas/#base-fee)（base fee）压入堆栈，它的操作码`0x48`，gas消耗为2。

    ```python
    def basefee(self):
        self.stack.append(self.current_block["basefee"])
    ```

## 11. 堆栈指令

### PC：
在EVM中，程序计数器（通常缩写为 PC）是一个用于跟踪当前执行指令位置的寄存器。每执行一条指令（opcode），程序计数器的值会自动增加，以指向下一个待执行的指令。但是，这个过程并不总是线性的，在执行跳转指令（JUMP和JUMPI）时，程序计数器会被设置为新的值。

EVM是基于堆栈的，堆栈遵循 LIFO（后入先出）原则，最后一个被放入堆栈的元素将是第一个被取出的元素。PUSH和POP指令就是用来操作堆栈的。

### PUSH：
在EVM中，PUSH是一系列操作符，共有32个（在以太坊上海升级前），从PUSH1，PUSH2，一直到PUSH32，操作码范围为0x60到0x7F。它们将一个字节大小为1到32字节的值从字节码压入堆栈（堆栈中每个元素的长度为32字节），每种指令的gas消耗都是3。

以PUSH1为例，它的操作码为0x60，它会将字节码中的下一个字节压入堆栈。例如，字节码0x6001就表示把0x01压入堆栈。PUSH2就是将字节码中的下两个字节压入堆栈，例如，0x610101就是把0x0101压入堆栈。其他的PUSH指令类似。

以太坊上海升级新加入了PUSH0，操作码为0x5F（即0x60的前一位），用于将0压入堆栈，gas消耗为2，比其他的PUSH指令更省gas。

### POP：
在EVM中，在EVM中，POP指令（操作码0x50，gas消耗2）用于移除栈顶元素；如果当前堆栈为空，就抛出一个异常。

### DUP：

在EVM中，DUP是一系列的指令，总共有16个，从DUP1到DUP16，操作码范围为0x80到0x8F，gas消耗均为3。

作用：这些指令用于复制（Duplicate）堆栈上的指定元素（根据指令的序号）到堆栈顶部。例如，DUP1复制栈顶元素，DUP2复制距离栈顶的第二个元素，以此类推。


## 12. SH3指令
EVM唯一内置的密码学指令--SHA3，你可以用它计算keccak-256哈希。

在EVM中，计算数据的哈希是一个常见的操作。以太坊使用Keccak算法（SHA-3）计算数据的哈希，并提供了一个专门的操作码SHA3，Solidity中的keccak256()函数就是建立在它之上的。

SHA3(offset, size)指令从堆栈中取出两个参数，起始位置offset和长度size（以字节为单位），然后它从内存中读取起始位置offset开始的size长度的数据，计算这段数据的Keccak-256哈希，并将结果（一个32字节的值）压入堆栈。它的操作码为0x20，gas消耗为30 + 6*数据的字节长度 + 扩展内存成本。

在Python中，我们可以使用pysha3库来实现keccak-256哈希计算。

## 13. 以太坊账户结构
以太坊上的账户分两类：外部账户（Externally Owned Accounts，EOA）和合约账户。EOA是用户在以太坊网络上的代表，它们可以拥有ETH、发送交易并与合约互动；而合约账户是存储和执行智能合约代码的实体，它们也可以拥有和发送ETH，但不能主动发起交易。

以太坊上的账户结构非常简单，你可以它理解为地址到账户状态的映射。账户地址是20字节（160位）的数据，可以用40位的16进制表示，比如0x9bbfed6889322e016e0a02ee459d306fc19545d8。而账户的状态具有4种属性：

- Balance：这是账户持有的ETH数量，用Wei表示（1 ETH = 10^18 Wei）。

- Nonce：对于外部账户（EOA），这是该账户发送的交易数。对于合约账户，它是该账户创建的合约数量。

- Storage：每个合约账户都有与之关联的存储空间，其中包含状态变量的值。

- Code：合约账户的字节码。

也就是说，只有合约账户拥有Storage和Code，EOA没有。

EVM中与账户（Account）相关的4个指令，包括
- BALANCE：用于返回某个账户的余额。
- EXTCODESIZE：用于返回某个账户的代码长度（以字节为单位）。
- EXTCODECOPY：用于将某个账户的部分代码复制到EVM的内存中。
- EXTCODEHASH：返回某个账户的代码的Keccak256哈希值。

我们能利用这些指令获取以太坊账户的信息。
