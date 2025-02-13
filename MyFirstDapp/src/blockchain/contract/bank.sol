// SPDX-License-Identifier: MIT
pragma solidity ^0.8.13;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract Bank {
    // record bank deposits: user to banlance
    mapping(address => uint) public deposited;

    address public immutable token;

    constructor(address _token) {
        token = _token;
    }

    modifier validBalance(uint amount) {
        amount = amount * 10 ** 18;
        uint balance = deposited[msg.sender];
        require(balance >= amount, "less then bank balance");
        _;
    }
    
     // 修复：定义 requireBalance 修饰符
    modifier requireBalance(uint amount) {
        uint balance = deposited[msg.sender];
        require(balance >= amount, "Insufficient balance");
        _;
    }


    function deposit(uint amount) public {
        amount = amount * 10 ** 18;
        require(IERC20(token).transferFrom(msg.sender, address(this), amount), "Transfer from error");
        deposited[msg.sender] += amount;
    }

    function myBalance() view public  returns(uint balance){
        balance = deposited[msg.sender]/(10 ** 18);
    }

    function withdraw(uint amount) validBalance(amount) external {
        SafeERC20.safeTransfer(IERC20(token), msg.sender, amount);
        deposited[msg.sender] -= amount;
    }

    // transfer 
    function bankTransfer(address to, uint amount) public requireBalance (amount) {
        amount = amount * 10 ** 18;
        // require(amount <= deposited[msg.sender], "the amount more then bank of balance");
        deposited[msg.sender] -= amount;
        deposited[to] += amount;
    }

}