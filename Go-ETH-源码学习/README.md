# Go-Eth

主要 follow 官网 https://goethereumbook.org/zh/

记录学习笔记

## 前置知识
以太坊是一个开源，公开，基于区块链的分布式计算平台和具备智能合约（脚本）功能的操作系统。它通过基于交易的状态转移支持中本聪共识的一个改进算法。

## 维基百科

以太坊是一个区块链，允许开发者创建完全去中心化运行的应用程序，这意味着没有单个实体可以将其删除或修改它。部署到以太坊上的每个应用都由以太坊网络上每个完整客户端执行。

## Solidity
Solidity是一种用于编写智能合约的图灵完备编程语言。Solidity被编译成以太坊虚拟机可执行的字节码。

## go-ethereum
本书中，我们将使用Go的官方以太坊实现go-ethereum来和以太坊区块链进行交互。Go-ethereum，也被简称为Geth，是最流行的以太坊客户端。因为它是用Go开发的，当使用Golang开发应用程序时，Geth提供了读写区块链的一切功能。

本书的例子在go-ethereum版本1.8.10-stable和Go版本go1.10.2下完成测试。

## Block Explorers
Etherscan是一个用于查看和深入研究区块链上数据的网站。这些类型的网站被称为区块浏览器，因为它们允许您查看区块（包含交易）的内容。区块是区块链的基础构成要素。区块包含在已分配的出块时间内开采出的所有交易数据。区块浏览器也允许您查看智能合约执行期间释放的事件以及诸如支付的gas和交易的以太币数量等。

## Swarm and Whisper
我们还将深入研究蜂群(Swarm)和耳语(Whisper)，分别是一个文件存储协议和一个点对点的消息传递协议，它们是实现完全去中心化和分布式应用程序需要的另外两个核心。
![](https://user-images.githubusercontent.com/168240/41317815-2e287afe-6e4b-11e8-89d8-4ec959988b64.png)


## 账号

"Ethereum 和 Bitcoin 最大的不同之一是二者使用链上数据模型不同。其中，Bitcoin 是基于 UTXO 模型的 Blockchain/Ledger 系统
Ethereum是基于 Account/State 模型的系统"。那么，这个另辟蹊径的 Account/State 模型究竟不同在何处呢？取决于=以太坊中的基本数据单元(Metadata)之一的Account。

简单的来说，Ethereum 的运行是一种基于交易的状态机模型(Transaction-based State Machine)。整个系统由若干的账户组成 (Account)，类似于银行账户。

状态(State)反应了某一账户(Account)在某一时刻下的值(value)。在以太坊中，State 对应的基本数据结构，称为 StateObject。

当 StateObject 的值发生了变化时，我们称为状态转移。在 Ethereum 的运行模型中，StateObject 所包含的数据会因为 Transaction 的执行引发数据更新/删除/创建，引发状态转移，我们说：StateObject 的状态从当前的 State 转移到另一个 State。

在 Ethereum 中，承载 StateObject 的具体实例就是 Ethereum 中的 Account。通常，我们提到的 State 具体指的就是 Account 在某个时刻的包含的数据的值。

- Account --> StateObject
- State --> The value/data of the Account
总的来说, Account (账户)是参与链上交易(Transaction)的基本角色，是Ethereum状态机模型中的基本单位，承担了链上交易的发起者以及接收者的角色。
目前，在以太坊中，有两种类型的Account，分别是外部账户(EOA)以及合约账户(Contract)。
