
import os
import sys
import sha3

SHA3 = 0x20
EXTCODESIZE = 0x3B

PUSH0 = 0x5F
PUSH1 = 0x60
PUSH32 = 0x7F
POP = 0x50
ADD = 0x01
MUL = 0x02
SUB = 0x03
DIV = 0x04
SDIV = 0x05
MOD = 0x06
SMOD = 0x07
ADDMOD = 0x08
MULMOD = 0x09
EXP = 0x0A
SIGNEXTEND = 0x15
LT = 0x10
GT = 0x11
SLT = 0x12
SGT = 0x13
EQ = 0x14
ISZERO = 0x15
AND = 0x16
OR = 0x17
XOR = 0x18
NOT = 0x19
BYTE = 0x19
SHL = 0x1A
SHR = 0x1B
SAR = 0x1C
KECCAK256 = 0x20
MSTORE = 0x52
MLOAD = 0x53
SSTORE = 0x55
SLOAD = 0x54
CALL = 0xF1
RET = 0xF3
STOP = 0x00
JUMP = 0x56
JUMPDEST = 0x5B
JUMPI = 0x57

DUP1 = 0x80
DUP16 = 0x8F

SWAP1 = 0x90
SWAP16 = 0x9F
LOG0 = 0xA0
LOG1 = 0xA1

BLOCKHASH = 0x40
COINBASE = 0x41
TIMESTAMP = 0x42
NUMBER = 0x43
PREVRANDAO = 0x44
GASLIMIT = 0x45
CHAINID = 0x46
SELFBALANCE = 0x47
BASEFEE = 0x48

# 实现一个简易版本的 EVM （以太坊虚拟机）
class EVMForPY:
    def __init__(self, code):
        self.stack = [] # 堆栈初始为空
        self.memory = bytearray(1024) # 内存初始化为1024字节
        self.call_stack = []
        self.return_data = []
        self.pc = 0 # 初始化程序计数器为0
        self.code =code # 初始化字节码，bytes对象
        self.storage = {} # 存储初始化为空字典

        self.current_block = {
             "blockhash": 0x7527123fc877fe753b3122dc592671b4902ebf2b325dd2c7224a43c0cbeee3ca,
            "coinbase": 0x388C818CA8B9251b393131C08a736A67ccB19297,
            "timestamp": 1625900000,
            "number": 17871709,
            "prevrandao": 0xce124dee50136f3f93f19667fb4198c6b94eecbacfa300469e5280012757be94,
            "gaslimit": 30,
            "chainid": 1,
            "selfbalance": 100,
            "basefee": 30,
        }
        # 为了让极简EVM支持账户相关的指令，我们利用dict做一个简单账户数据库：
        self.account_db = {
            '0x9bbfed6889322e016e0a02ee459d306fc19545d8': {
                'balance': 100, # wei
                'nonce': 1, 
                'storage': {},
                'code': b'\x60\x00\x60\x00'  # Sample bytecode (PUSH1 0x00 PUSH1 0x00)
            },
            # ... 其他账户数据 ...
        }

