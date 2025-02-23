## 生成新钱包

要首先生成一个新的钱包，我们需要导入go-ethereumcrypto包，该包提供用于生成随机私钥的GenerateKey方法。

```go
privateKey, err := crypto.GenerateKey()
if err != nil {
  log.Fatal(err)
}
```
然后我们可以通过导入golangcrypto/ecdsa包并使用FromECDSA方法将其转换为字节。

```go
privateKeyBytes := crypto.FromECDSA(privateKey)
```

我们现在可以使用go-ethereumhexutil包将它转换为十六进制字符串，该包提供了一个带有字节切片的Encode方法。 然后我们在十六进制编码之后删除“0x”。

```go
fmt.Println(hexutil.Encode(privateKeyBytes)[2:])
```
这就是用于签署交易的私钥，将被视为密码，永远不应该被共享给别人，因为谁拥有它可以访问你的所有资产。

由于公钥是从私钥派生的，因此go-ethereum的加密私钥具有一个返回公钥的Public方法。

publicKey := privateKey.Public()

将其转换为十六进制的过程与我们使用转化私钥的过程类似。 我们剥离了0x和前2个字符04，它始终是EC前缀，不是必需的。

```go
publicKeyECDSA, ok := publicKey.(*ecdsa.PublicKey)
if !ok {
  log.Fatal("cannot assert type: publicKey is not of type *ecdsa.PublicKey")
}

publicKeyBytes := crypto.FromECDSAPub(publicKeyECDSA)
fmt.Println(hexutil.Encode(publicKeyBytes)[4:])
```

现在我们拥有公钥，就可以轻松生成你经常看到的公共地址。 为了做到这一点，go-ethereum加密包有一个PubkeyToAddress方法，它接受一个ECDSA公钥，并返回公共地址。

```go
address := crypto.PubkeyToAddress(*publicKeyECDSA).Hex()
fmt.Println(address) 
```

公共地址其实就是公钥的Keccak-256哈希，然后我们取最后40个字符（20个字节）并用“0x”作为前缀。 以下是使用 golang.org/x/crypto/sha3 的 Keccak256函数手动完成的方法。

```go
hash := sha3.NewLegacyKeccak256()
hash.Write(publicKeyBytes[1:])
fmt.Println(hexutil.Encode(hash.Sum(nil)[12:]))
```
## 完整代码
```go
package main

import (
	"crypto/ecdsa"
	"fmt"
	"log"

	"github.com/ethereum/go-ethereum/common/hexutil"
	"github.com/ethereum/go-ethereum/crypto"
	"golang.org/x/crypto/sha3"
)

func main() {
	privateKey, err := crypto.GenerateKey()
	if err != nil {
		log.Fatal(err)
	}

	privateKeyBytes := crypto.FromECDSA(privateKey)
	fmt.Println(hexutil.Encode(privateKeyBytes)[2:])

	publicKey := privateKey.Public()
	publicKeyECDSA, ok := publicKey.(*ecdsa.PublicKey)
	if !ok {
		log.Fatal("cannot assert type: publicKey is not of type *ecdsa.PublicKey")
	}

	publicKeyBytes := crypto.FromECDSAPub(publicKeyECDSA)
	fmt.Println(hexutil.Encode(publicKeyBytes)[4:])

	address := crypto.PubkeyToAddress(*publicKeyECDSA).Hex()
	fmt.Println(address)

	hash := sha3.NewLegacyKeccak256()
	hash.Write(publicKeyBytes[1:])
	fmt.Println(hexutil.Encode(hash.Sum(nil)[12:]))
}

```
运行结果
```c
9f28b3426e1a9e7053b39c2ec510483f69db6c9e19a0706b3d48db5e68f0121e
dac7ebc682e85ba010a8a076295549b09b506149994f7c95f71495c6ff77f7c541099138b093d24fcabecc7a9c2df34256184df903e70bc970f9a7a1215f761a
0xAf9D08D5702d9211f979278393113B89019E01d0
0xaf9d08d5702d9211f979278393113b89019e01d0
```
