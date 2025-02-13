# NFTSwap

利用智能合约搭建一个零手续费的去中心化NFT交易所

## 功能：
- 卖家：出售 NFT 的一方，可以挂单 `list`，撤单 `revoke`，修改价格 `update` 。
- 买家：购买 NFT 的一方，可以购买 `purchase`。
- 订单：卖家发布的 NFT 链上订单，一个系列的同一个 `tokenId` 最多存在一个订单，其中包含挂单价格 `price` 和 持有人 `owner` 信息。当一个订单交易完成或被撤单后，其中信息清零.


## 合约设计

### 事件
合约包含 4 个事件，对应挂单 `list`，撤单 `revoke`，修改价格 `update`，购买 `purchase` 这四个行为：

```solidity
event List(address indexed seller, address indexed nftAddr, uint256 indexed tokenId, uint256 price);

event Purchase(address indexed buyer, address indexed nftAddr, uint256 indexed tokenId, uint256 price);

event Revoke(address indexed seller, address indexed nftAddr, uint256 indexed tokenId);    

event Update(address indexed seller, address indexed nftAddr, uint256 indexed tokenId, uint256 newPrice);

```

## 订单
NFT 订单抽象为 Order 结构体，包含挂单价格 price 和持有人 owner 信息。 nftList 映射记录了订单是对应的 NFT 系列（合约地址）和 tokenId 信息。

```solidity
// 定义order结构体
struct Order {
    address owner;
    uint256 price;
}
// NFT Order 映射
mapping(address => mapping(uint256 => Order)) public nftList;
```

## 回退函数
在 NTFSwap 合约中，用户使用了 ETF 购买了 NFT，因此，合约需要实现 fallback() 函数来接收 ETF。

```solidity
fallback() external payable{}
```

## onERC721Received
ERC721 的安全转账函数会检查接收合约是否实现了 onERC721Received() 函数，并返回正确的选择器 selector。

用户下单之后，需要将NFT发送给NFTSwap合约。因此NFTSwap继承IERC721Receiver接口，并实现onERC721Received()函数：

```solidity
contract NFTSwap is IERC721Receiver {
    // 实现{IERC721Receiver}的onERC721Received，能够接收ERC721代币
    function onERC721Received {
        address operator,
        address from,
        uint tokenId,
        bytes calldata data
    } external override returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }
}
```

## 交易
合约实现了 4 个交易相关的函数:

- 挂单 list(): 卖家创建 NFT 并创建订单，并释放 List 事件。参数为 NFT 合约地址_nftAddr，NFT 对应的 _tokenId，挂单价格 _price（注意：单位是wei ）。成功后，NFT 会从卖家转到 NFTSwap 合约中。

```solidity
function list(address _nftAddr, uint256 _tokenId, uint256 _price) public {
    IERC721 _nft = IERC721(_nftAddr); // 声明IERC721接口合约变量
    require(_nft.getApproved(_tokenId) == address(this), "Need Approval"); // 合约得到授权
    require(_price > 0); // price > 0 

    Order storage _order = nftList[_nftAddr][_tokenId]; //设置NFT持有人和价格
    _order.owner = msg.sender;
    _order.price = _price;
    // 将NFT转账到合约
    _nft.safeTransferFrom(msg.sender, address(this), _tokenId);
    //释放 List 事件
    emit List(msg.sender, _nftAddr, _tokenId, _price);
}
```

- 撤单 revoke(): 卖家撤单，释放 Revoke 事件。参数为 NFT 合约地址_nftAddr，NFT 对应的 _tokenId。成功后，NFT 会从 NFTSwap 合约中释放到卖家的钱包中。
  
```solidity
// 撤单： 卖家取消挂单
function revoke(address _nftAddr, uint256 _tokenId) public {
    Order storage _order = nftList[_nftAddr][_tokenId];
    require(_order.owner == msg.sender, "Not Owner"); // 必须是订单的owner
    IERC721 _nft = IERC721(_nftAddr); // 声明IERC721接口合约变量
    // 必须当前 NFT 在合约中
    require(_nft.ownerOf(_tokenId) == address(this), "Not in Contract"); 

    // 将 NFT 转回给卖家
    _nft.safeTransferFrom(address(this), msg.sender, _tokenId);
    delete nftList[_nftAddr][_tokenId]; // 清空订单信息

    // 释放 Revoke 事件
    emit Revoke(msg.sender, _nftAddr, _tokenId);
}
```
