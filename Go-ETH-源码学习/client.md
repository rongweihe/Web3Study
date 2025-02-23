# 开启客户端

用Go初始化以太坊客户端是和区块链交互所需的基本步骤。首先，导入go-etherem的ethclient包并通过调用接收区块链服务提供者URL的Dial来初始化它。

若您没有现有以太坊客户端，您可以连接到infura网关。Infura管理着一批安全，可靠，可扩展的以太坊[geth和parity]节点，并且在接入以太坊网络时降低了新人的入门门槛。

```go
client, err := ethclient.Dial("https://cloudflare-eth.com")
```
若您运行了本地geth实例，您还可以将路径传递给IPC端点文件。

```go
client, err := ethclient.Dial("/home/user/.ethereum/geth.ipc")
```
对每个Go以太坊项目，使用ethclient是您开始的必要事项

运行代码

```go
package main

import (
    "fmt"
    "log"

    "github.com/ethereum/go-ethereum/ethclient"
)

func main() {
    client, err := ethclient.Dial("https://cloudflare-eth.com")
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println("we have a connection")
    _ = client // we'll use this in the upcoming sections
}
```

运行结果

```go
~GolangCode: go mod tidy
go: finding module for package github.com/ethereum/go-ethereum/ethclient
go: downloading github.com/ethereum/go-ethereum v1.15.2
go: found github.com/ethereum/go-ethereum/ethclient in github.com/ethereum/go-ethereum v1.15.2
go: downloading golang.org/x/crypto v0.32.0
go: downloading github.com/holiman/uint256 v1.3.2
go: downloading golang.org/x/sys v0.29.0
go: downloading golang.org/x/exp v0.0.0-20240222234643-814bf88cf225
go: downloading github.com/pion/stun/v2 v2.0.0
go: downloading github.com/supranational/blst v0.3.14
go: downloading github.com/tklauser/go-sysconf v0.3.13
go: downloading golang.org/x/net v0.34.0
go: downloading github.com/pion/dtls/v2 v2.2.7
go: downloading github.com/pion/transport/v3 v3.0.1
go: downloading github.com/klauspost/compress v1.17.7
go: downloading github.com/tklauser/numcpus v0.7.0
go: downloading github.com/pion/logging v0.2.2
go: downloading github.com/pion/transport/v2 v2.2.1
go: downloading golang.org/x/text v0.21.0

~GolangCode: go run main.go
~GolangCode: we have a connection
```
