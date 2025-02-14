# 去中心化 Bank Dapp 

项目描述：

- 去中心化的链上银行 DAPP，允许用户通过 MetaMask 钱包与智能合约进行交互，实现存款、取款和转账功能；
- 前端使用 React 和 Web3.js 构建，后端
- 基于 Solidity 智能合约，部署在以太坊测试网。该项目旨在提供一个安全、透明且易于 使用的金融平台，利用区块链技术确保交易的不可篡改和去中心化特性。

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

### 运行前准备

- 更新 node_modules

- 替换你的合约地址 和 ABI.json

```c
const bank_address = 你的真实部署合约地址
```
- 更新 ABI.json 文件
- 保存然后执行
> npm run start

## Available Scripts

In the project directory, you can run:

### `npm start`

运行命令：
> npm run start 

如果报错 react-scripts: Permission denied 

执行
> sudo chmod -R 755 node_modules/.bin

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.


### 运行界面

- 正常链接 metaMask钱包
![pEufauT.png](https://s21.ax1x.com/2025/02/13/pEufauT.png)

- 存入
![pEuf5UH.png](https://s21.ax1x.com/2025/02/13/pEuf5UH.png)

- 显示余额
![pEufbxP.png](https://s21.ax1x.com/2025/02/13/pEufbxP.png)
