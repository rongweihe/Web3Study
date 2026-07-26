// SPDX-License-Identifier: MIT 开源协议声明
pragma solidity 0.8.24; // 指定Solidity编译器版本

// 引入ERC20标准接口
import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
// ERC20获取代币小数位接口
import { IERC20Metadata } from "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
// 安全转账封装，规避ERC20转账返回值坑
import { SafeERC20 } from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
// 重入攻击保护修饰器
import { ReentrancyGuard } from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
// 安全乘除数学库，防止溢出
import { Math } from "@openzeppelin/contracts/utils/math/Math.sol";

/// @notice 教学版 x*y=k 恒定乘积AMM资金池。
/// 重要特性：LP流动性份额仅合约内部记账，**没有发行可转账的LP ERC20代币**
contract MiniCPAMM is ReentrancyGuard {
    // 给IERC20启用SafeERC20安全转账方法
    using SafeERC20 for IERC20;

    // 自定义错误：两个代币地址不能相同
    error IdenticalTokens();
    // 自定义错误：传入零地址
    error ZeroAddress();
    // 自定义错误：传入数量为0
    error ZeroAmount();
    // 自定义错误：传入代币不属于池子内两种代币
    error InvalidToken();
    // 自定义错误：流动性不足
    error InsufficientLiquidity();
    // 自定义错误：兑换输出代币小于用户预期最小值
    error InsufficientOutput();
    // 自定义错误：添加流动性时两种代币比例不符合池子比例
    error InvalidRatio();

    // 手续费分母 10000 = 代表万分之单位
    uint256 public constant FEE_DENOMINATOR = 10_000;
    // 手续费 30bps = 千分之3手续费
    uint256 public constant FEE_BPS = 30;
    // 池子两种代币，部署时自动排序，地址更小的为token0
    address public immutable token0;
    address public immutable token1;

    // 池子代币库存储备，uint112节省gas
    uint112 private _reserve0;
    uint112 private _reserve1;

    // 池子流动性总份额（全局总和）
    uint256 public totalLiquidity;
    // 账本：地址 => 该地址拥有的流动性份额
    mapping(address provider => uint256 shares) public liquidityOf;

    // 添加流动性事件
    event LiquidityAdded(
        address indexed provider, // 流动性接收地址
        uint256 amount0,          // 转入token0数量
        uint256 amount1,          // 转入token1数量
        uint256 shares            // 发放的流动性份额
    );

    // 移除流动性事件
    event LiquidityRemoved(
        address indexed provider, // 发起赎回的用户
        uint256 amount0,          // 赎回得到token0
        uint256 amount1,          // 赎回得到token1
        uint256 shares            // 销毁的流动性份额
    );

    // 代币兑换交易事件
    event Swap(
        address indexed sender,    // 兑换发起者
        address indexed tokenIn,    // 输入代币
        uint256 amountIn,          // 输入代币数量
        uint256 amountOut,          // 输出代币数量
        address recipient           // 接收兑换代币的地址
    );

    /// @dev 构造函数，部署池子
    constructor(address tokenA, address tokenB) {
        // 不能传入零地址代币
        if (tokenA == address(0) || tokenB == address(0)) revert ZeroAddress();
        // 两个代币不能是同一个
        if (tokenA == tokenB) revert IdenticalTokens();
        // 自动排序：地址小的赋值给token0，大的为token1，和UniV2保持一致
        (token0, token1) = tokenA < tokenB ? (tokenA, tokenB) : (tokenB, tokenA);
    }

    /**
     * @notice 添加流动性，向池子存入token0、token1，获取流动性份额
     * @param amount0 存入token0数量
     * @param amount1 存入token1数量
     * @param recipient 流动性份额发放给谁（可以不是调用者）
     * @return shares 获取到的流动性份额
     */
    function addLiquidity(uint256 amount0, uint256 amount1, address recipient)
        external
        nonReentrant // 防重入攻击
        returns (uint256 shares)
    {
        // 不能存入0数量代币
        if (amount0 == 0 || amount1 == 0) revert ZeroAmount();
        // 份额接收地址不能是0地址
        if (recipient == address(0)) revert ZeroAddress();

        // 分支1：池子是空池，第一次添加流动性（初始化池子）
        if (totalLiquidity == 0) {
            // 初始份额 = √(amount0 * amount1)，和UniswapV2初始化规则一致
            shares = Math.sqrt(amount0 * amount1);
        } else {
            // 分支2：池子已有流动性，按当前储备比例计算份额
            // 根据投入的token0计算应得份额
            uint256 shares0 = Math.mulDiv(amount0, totalLiquidity, _reserve0);
            // 根据投入的token1计算应得份额
            uint256 shares1 = Math.mulDiv(amount1, totalLiquidity, _reserve1);
            // 重点：两个方式算出份额必须相等！必须严格按照池子当前比例投入
            if (shares0 != shares1) revert InvalidRatio();
            shares = shares0;
        }

        // 计算得到份额不能为0，防止极小资金无法获取份额
        if (shares == 0) revert InsufficientLiquidity();

        // 从调用者钱包把token0转入池子合约
        IERC20(token0).safeTransferFrom(msg.sender, address(this), amount0);
        // 从调用者钱包把token1转入池子合约
        IERC20(token1).safeTransferFrom(msg.sender, address(this), amount1);

        // 更新账本：给接收地址增加流动性份额
        liquidityOf[recipient] += shares;
        // 更新池子全局总份额
        totalLiquidity += shares;

        // 同步更新池子代币储备余额
        _sync();
        // 触发添加流动性日志事件
        emit LiquidityAdded(recipient, amount0, amount1, shares);
    }

    /**
     * @notice 移除流动性，销毁份额，赎回池子里对应的两种代币
     * @param shares 需要销毁的流动性份额
     * @param recipient 赎回出来的代币转给这个地址
     * @return amount0 赎回得到token0数量
     * @return amount1 赎回得到token1数量
     */
    function removeLiquidity(uint256 shares, address recipient)
        external
        nonReentrant // 防重入
        returns (uint256 amount0, uint256 amount1)
    {
        // 不能销毁0份额
        if (shares == 0) revert ZeroAmount();
        // 校验：调用者自身拥有的份额足够赎回
        if (liquidityOf[msg.sender] < shares) revert InsufficientLiquidity();

        // 按份额占比瓜分池内资产
        // 可拿回token0 = 池子储备0 * 赎回份额 / 总流动性份额
        amount0 = Math.mulDiv(_reserve0, shares, totalLiquidity);
        // 可拿回token1 = 池子储备1 * 赎回份额 / 总流动性份额
        amount1 = Math.mulDiv(_reserve1, shares, totalLiquidity);

        // 用户账本扣除销毁的份额
        liquidityOf[msg.sender] -= shares;
        // 全局总份额减少
        totalLiquidity -= shares;

        // 合约转账token0给目标地址
        IERC20(token0).safeTransfer(recipient, amount0);
        // 合约转账token1给目标地址
        IERC20(token1).safeTransfer(recipient, amount1);

        // 同步更新储备
        _sync();
        // 触发移除流动性事件
        emit LiquidityRemoved(msg.sender, amount0, amount1, shares);
    }

    /**
     * @notice 只读函数：预估输入指定代币，扣除手续费后能兑换多少代币（报价）
     * @param tokenIn 输入的代币
     * @param amountIn 输入代币数量
     * @return amountOut 预估可得到的输出代币
     */
    function quoteExactInput(address tokenIn, uint256 amountIn)
        public
        view
        returns (uint256 amountOut)
    {
        if (amountIn == 0) revert ZeroAmount();
        // 判断兑换方向：true=token0换token1，false=token1换token0
        bool zeroForOne = _direction(tokenIn);
        // 根据方向分配输入储备、输出储备
        (uint256 reserveIn, uint256 reserveOut) =
            zeroForOne ? (_reserve0, _reserve1) : (_reserve1, _reserve0);

        // 池子其中一种代币为空，无法交易
        if (reserveIn == 0 || reserveOut == 0) revert InsufficientLiquidity();

        // 扣除千三手续费后的实际参与兑换金额
        uint256 amountInWithFee = amountIn * (FEE_DENOMINATOR - FEE_BPS);
        // UniV2恒定乘积兑换公式计算输出数量
        amountOut =
            Math.mulDiv(amountInWithFee, reserveOut, reserveIn * FEE_DENOMINATOR + amountInWithFee);
    }

    /**
     * @notice 真实兑换：输入固定数量代币，换取另一种代币
     * @param tokenIn 输入代币地址
     * @param amountIn 输入代币数量
     * @param minAmountOut 最少能收到多少输出代币（滑点保护）
     * @param recipient 收到兑换后代币的地址
     * @return amountOut 实际得到输出代币
     */
    function swapExactInput(
        address tokenIn,
        uint256 amountIn,
        uint256 minAmountOut,
        address recipient
    ) external nonReentrant returns (uint256 amountOut) {
        bool zeroForOne = _direction(tokenIn);
        // 调用报价函数算出预期输出
        amountOut = quoteExactInput(tokenIn, amountIn);
        // 如果实际能换的少于用户最低预期，交易回滚，防止滑点
        if (amountOut < minAmountOut) revert InsufficientOutput();
        // 获取输出代币地址
        address tokenOut = zeroForOne ? token1 : token0;
        // 用户把输入代币转给池子
        IERC20(tokenIn).safeTransferFrom(msg.sender, address(this), amountIn);
        // 池子把输出代币转给接收人
        IERC20(tokenOut).safeTransfer(recipient, amountOut);
        // 更新储备
        _sync();
        emit Swap(msg.sender, tokenIn, amountIn, amountOut, recipient);
    }

    /// @notice 查询当前池子两种代币储备量
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1) {
        return (_reserve0, _reserve1);
    }

    /**
     * @notice 获取现货价格，统一放大到1e18精度方便前端展示
     * @param baseToken 基准代币，查询 1个baseToken能换多少另一种币
     */
    function spotPriceX18(address baseToken) public view returns (uint256) {
        bool baseIs0 = _direction(baseToken);
        // 获取两种代币小数位
        uint8 decimals0 = IERC20Metadata(token0).decimals();
        uint8 decimals1 = IERC20Metadata(token1).decimals();
        if (baseIs0) {
            // 1 token0 = ? token1，做精度换算，结果 *1e18
            return Math.mulDiv(
                uint256(_reserve1) * (10 ** decimals0), 1e18, uint256(_reserve0) * (10 ** decimals1)
            );
        }
        // 1 token1 = ? token0
        return Math.mulDiv(
            uint256(_reserve0) * (10 ** decimals1), 1e18, uint256(_reserve1) * (10 ** decimals0)
        );
    }

    /// @dev 私有工具函数，判断传入代币是token0还是token1，返回兑换方向
    function _direction(address tokenIn) private view returns (bool zeroForOne) {
        if (tokenIn == token0) return true;
        if (tokenIn == token1) return false;
        revert InvalidToken();
    }

    /// @dev 同步函数：读取合约真实代币余额，刷新池子储备_reserve0、_reserve1
    function _sync() private {
        // 读取合约当前真实持有的代币余额
        uint256 balance0 = IERC20(token0).balanceOf(address(this));
        uint256 balance1 = IERC20(token1).balanceOf(address(this));
        // 余额超过uint112最大值则报错
        if (balance0 > type(uint112).max || balance1 > type(uint112).max) {
            revert InsufficientLiquidity();
        }
        // 使用真实余额覆盖更新储备
        _reserve0 = uint112(balance0);
        _reserve1 = uint112(balance1);
    }
}
