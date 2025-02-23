# ethers.js简述

ethers.js是一个完整而紧凑的开源库，用于与以太坊区块链及其生态系统进行交互。如果你要写Dapp的前端，你就需要用到ethers.js。

与更早出现的web3.js相比，它有以下优点：

- 代码更加紧凑：ethers.js大小为116.5 kB，而web3.js为590.6 kB。
- 更加安全：Web3.js认为用户会在本地部署以太坊节点，私钥和网络连接状态由这个节点管理（实际并不是这样）；ethers.js中，Provider提供器类管理网络连接状态，Wallet钱包类管理密钥，安全且灵活。
- 原生支持ENS。

![](https://www.wtf.academy/_next/image?url=https%3A%2F%2Fstatic.wtf.academy%2Fimage%2Fd68508c8d82bf30c5f949acfc9be7ed9.png&w=3840&q=75)

# 开发工具
- VScode（推荐）
你可以使用本地vscode进行开发。你需要安装Node.js，然后利用包管理工具npm安装ethers库：

npm install ethers --save

- playcode（不稳定）

# HelloVitalik

现在，让我们用ethers编写第一个程序HelloVitalik：查询Vitalik的ETH余额，并输出在console中。整个程序只需要6行，非常简单！
注意：在playcode上第一次运行可能会提示module not found，这是因为ethers库还没有安装，只需要点击install按钮安装即可。


