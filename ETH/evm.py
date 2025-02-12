
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

    # PC指令将当前的程序计数器（pc）的值压入堆栈。操作码为0x58，gas消耗为2。
    def pc(self):
        self.stack.append(self.pc)
    
    def push(self, size):
        data = self.code[self.pc:self.pc + size] # 按照size从code中获取数据
        value = int.from_bytes(data, 'big') # 将bytes转换为int
        self.stack.append(value) # 压入堆栈
        self.pc += size # pc增加size单位
    
    def pop(self):
        return self.stack.pop()

    # MLOAD指令从内存中加载一个256位的值并推入堆栈。它从堆栈中弹出一个元素，从该元素表示的内存地址中加载32字节，并将其推入堆栈。操作码是0x51，gas消耗根据实际内存使用情况计算（3+X）。
    def mload(self, offset):
        if len(self.stack) < 1:
            raise Exception('Stack underflow')
        offset = self.stack.pop()
        while len(self.memory) < offset + 32:
            self.memory.append(0) # 扩展内存
        
        value = int.from_bytes(self.memory[offset:offset+32], 'big') # 从内存中加载数据
        self.stack.append(value) # 压入堆栈
    
    #内存写 将一个 256位的值存储到内存中，从堆栈中弹出两个元素，第一个元素内存地址（偏移量 offset）;第二个元素存储的值，操作码是0x52，gas 消耗为3。
    def mstore(self, offset, value):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')

        offset = self.stack.pop()
        value = self.stack.pop()

        while len(self.memory) < offset + 32:
            self.memory.append(0) # 扩展内存  
        self.memory[offset:offset+32] = value.to_bytes(32, 'big') # 存储数据  

    # MSIZE指令将当前的内存大小（以字节为单位）压入堆栈。操作码是0x59，gas消耗为2。
    def msize(self):
        self.stack.append(len(self.memory))

    # SSTORE (存储写)
    # SSTORE指令用于将一个256位（32字节）的值写入到存储。它从堆栈中弹出两个元素，第一个元素为存储的地址（key），第二个元素为存储的值（value）。操作码是0x55，gas消耗根据实际改变的数据计算（下面给出）。
    def sstore(self, slot, value):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        key = self.stack.pop()
        value = self.stack.pop()
        self.storage[key] = value

    # SLOAD指令从存储中读取一个256位（32字节）的值并推入堆栈。它从堆栈中弹出一个元素，从该元素表示的存储槽中加载值，并将其推入堆栈。操作码是0x54，gas消耗后面给出。
    def ssload(self, slot):
        if len(self.stack) < 1:
            raise Exception('Stack underflow')
        key = self.stack.pop()
        value = self.storage.get(key, 0)
        self.stack.append(value)
        
    def call(self, address, gas, value, data):
        self.call_stack.append((address, gas, value, data))
    def ret(self, offset, length):
        self.return_data = self.memory[offset:offset+length]

    # 在真实场景中, 你会需要访问历史的区块hash
    # 这里我们只是简单地返回当前区块的hash
    def blockhash(self):
        if len(self.stack) < 1:
            raise Exception('Stack underflow')
        number = self.stack.pop()
        if number == self.current_block['number']:
            self.stack.append(self.current_block['blockhash'])
        else:
            self.stack.append(0)# 如果不是当前块，返回0

    # COINBASE: 将当前区块的coinbase（矿工/受益人）地址压入堆栈，它的操作码为0x41，gas消耗为2。
    def coinbase(self):
        self.stack.append(self.current_block["coinbase"])
    
    # TIMESTAMP: 将当前区块的时间戳压入堆栈，它的操作码为0x42，gas消耗为2。
    def timestamp(self):
        self.stack.append(self.current_block["timestamp"])
    
    # NUMBER: 将当前区块高度压入堆栈，它的操作码为0x43，gas消耗为2。
    def number(self):
        self.stack.append(self.current_block["number"])
    
    # gaslimit
    def gaslimit(self):
        self.stack.append(self.current_block["gaslimit"])


    # 在EVM中，DUP是一系列的指令，总共有16个，从DUP1到DUP16，操作码范围为0x80到0x8F，gas消耗均为3。这些指令用于复制（Duplicate）堆栈上的指定元素（根据指令的序号）到堆栈顶部。例如，DUP1复制栈顶元素，DUP2复制距离栈顶的第二个元素，以此类推。
    def dup(self, n):
        if len(self.stack) < n:
            raise Exception('Stack underflow')
        val = self.stack[-n]
        self.stack.append(val)

    # SWAP指令用于交换堆栈顶部的两个元素。与DUP类似，SWAP也是一系列的指令，从SWAP1到SWAP16共16个，操作码范围为0x90到0x9F，gas消耗均为3。SWAP1交换堆栈的顶部和次顶部的元素，SWAP2交换顶部和第三个元素，以此类推。
    def swap(self, position):
        if len(self.stack) < position + 1:
            raise Exception('Stack underflow')
        idx1, idx2 = -1, -position - 1
        self.stack[idx1], self.stack[idx2] = self.stack[idx2], self.stack[idx1]
    
    # SWAP1
    # code = b"\x60\x01\x60\x02\x90"
    # evm = EVM(code)
    # evm.run()
    # print(evm.stack)  
    # # output: [2, 1]
