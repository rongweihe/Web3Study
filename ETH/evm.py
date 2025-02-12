
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
             "blockhash": 0x6827123fc877fe753b3122dc592671b4902ebf2b325dd2c7224a43c0cbeee398,
            "coinbase": 0x699C818CA8B9251b393131C08a736A67ccB19356,
            "timestamp": 1739363186,
            "number": 173936312,
            "prevrandao": 0xfd124dee50136f3f93f19667fb4198c6b94eecbacfa300469e5280012757bf89,
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


    def sha3(self):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        offset = self.pop()
        size = self.pop()
        data = self.memory[offset:offset+size]  # 从内存中获取数据
        hash_value = int.from_bytes(sha3.keccak_256(data).digest(), 'big')  # 计算哈希值
        self.stack.append(hash_value)  # 将哈希值压入堆栈

    # SHA3
    # code = b"\x5F\x5F\x20"
    # evm = EVM(code)
    # evm.run()
    # print(hex(evm.stack[-1]))  # 打印出0的keccak256 hash
    # # output: 0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470

    # BALANCE 指令用于返回某个账户的余额。它从堆栈中弹出一个地址，然后查询该地址的余额并压入堆栈。它的操作码是0x31，gas为2600（cold address）或100（warm address）。
    def balance(self):
        if len(self.stack) < 1:
            raise Exception('Stack underflow')
        addr_int = self.stack.pop()
        # 将stack中的int转换为bytes，然后再转换为十六进制字符串，用于在账户数据库中查询
        addr_str = '0x' + addr_int.to_bytes(20, byteorder='big').hex()
        self.stack.append(self.account_db.get(addr_str, {}).get('balance', 0))


    # EXTCODESIZE 指令用于返回某个账户的代码长度（以字节为单位）。它从堆栈中弹出一个地址，然后查询该地址的代码长度并压入堆栈。如果账户不存在或没有代码，返回0。他的操作码为0x3B，gas为2600（cold address）或100（warm address）。
    def extcodesize(self):
        if len(self.stack) < 1:
            raise Exception('Stack underflow')
        addr_int = self.stack.pop()
        # 将stack中的int转换为bytes，然后再转换为十六进制字符串，用于在账户数据库中查询
        addr_str = '0x' + addr_int.to_bytes(20, byteorder='big').hex()
        self.stack.append(len(self.account_db.get(addr_str, {}).get('code', b'')))


    def add(self):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        a = self.stack.pop()
        b = self.stack.pop()
        res = (a+b)%(2**256)# 加法结果需要模2^256，防止溢出
        self.stack.append(res)


    def sub(self):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        a = self.stack.pop()
        b = self.stack.pop()
        res = (a-b)%(2**256)# 减法结果需要模2^256，防止溢出
        self.stack.append(res)

    def mul(self):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        a = self.stack.pop()
        b = self.stack.pop()
        res = (a*b)%(2**256)# 乘法结果需要模2^256，防止溢出
        self.stack.append(res)

    def div(self):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        a = self.stack.pop()
        b = self.stack.pop()
        if b == 0:
            res = 0
        else:
            res = (a // b)%(2**256)# 除法结果需要模2^256，防止溢出
        self.stack.append(res)


    def lt(self):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        a = self.stack.pop()
        b = self.stack.pop()
        self.stack.append(int(b < a)) # 注意这里的比较顺序

    def gt(self):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        a = self.stack.pop()
        b = self.stack.pop()
        self.stack.append(int(b > a)) # 注意这里的比较顺序

    def eq(self):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        a = self.stack.pop()
        b = self.stack.pop()
        self.stack.append(int(a == b))
    
    # AND指令从堆栈中弹出两个元素，对它们进行位与运算，并将结果推入堆栈。操作码是0x16，gas 消耗为3。
    def and_op(self):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        a = self.stack.pop()
        b = self.stack.pop()
        self.stack.append(a & b)
    
    # OR指令从堆栈中弹出两个元素，对它们进行位或运算，并将结果推入堆栈。操作码是0x17，gas 消耗为3。
    def or_op(self):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        a = self.stack.pop()
        b = self.stack.pop()
        self.stack.append(a | b)

    # XOR指令与AND和OR指令类似，但执行的是异或运算。操作码是0x18，gas 消耗为3。
    def xor_op(self):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        a = self.stack.pop()
        b = self.stack.pop()
        self.stack.append(a ^ b)


    def stop(self):
        print('Program has been stopped')
        return
    
    # JUMPDEST指令标记一个有效的跳转目标位置，不然无法使用JUMP和JUMPI进行跳转。它的操作码是0x5b，gas消耗为1。
    # 但是0x5b有时会作为PUSH的参数（详情可看黄皮书中的9.4.3. Jump Destination Validity），所以需要在运行代码前，筛选字节码中有效的JUMPDEST指令，使用ValidJumpDest 来存储有效的JUMPDEST指令所在位置。
    def findValidJumpDestinations(self):
        pc = 0
        while pc < len(self.code):
            op = self.code[pc]
            if op == JUMPDEST:
                self.validJumpDest[pc] = True
            elif op >= PUSH1 and op <= PUSH32:
                pc += op - PUSH1 + 1
            pc += 1

    def jumpdest(self):
        pass

    # JUMP指令用于无条件跳转到一个新的程序计数器位置。它从堆栈中弹出一个元素，将这个元素设定为新的程序计数器（pc）的值。操作码是0x56，gas消耗为8。
    def jump(self):
        if len(self.stack) < 1:
            raise Exception('Stack underflow')
        dest = self.stack.pop()
        if dest not in self.validJumpDest:
            raise Exception('Invalid jump destination')
        else: self.pc = dest

    # JUMPI指令用于条件跳转，它从堆栈中弹出两个元素，如果第二个元素（条件，condition）不为0，那么将第一个元素（目标，destination）设定为新的pc的值。操作码是0x57，gas消耗为10。
    def jumpi(self):
        if len(self.stack) < 2:
            raise Exception('Stack underflow')
        destination = self.stack.pop()
        condition = self.stack.pop()
        if condition != 0:
            if destination not in self.validJumpDest:
                raise Exception('Invalid jump destination')
            else:  self.pc = destination

    # NOT指令从堆栈中弹出一个元素，对它进行位非运算，并将结果推入堆栈。操作码是0x19，gas 消耗为3。
    def not_op(self):
        if len(self.stack) < 1:
            raise Exception('Stack underflow')
        a = self.stack.pop()
        self.stack.append(~a)

    def execute(self, code):
        for instruction in code:
            if instruction[0] == 'PUSH':
                self.push(instruction[1])
            elif instruction[0] == 'POP':
                self.pop()
            elif instruction[0] == 'MLOAD':
                self.mload(instruction[1])
            elif instruction[0] == 'MSTORE':
                self.mstore(instruction[1], instruction[2])
            elif instruction[0] == 'CALL':
                self.call(instruction[1], instruction[2], instruction[3], instruction[4])
            elif instruction[0] == 'RET':
                self.ret(instruction[1], instruction[2])
        return self.return_data 

    # 获取下一条指令
    def next_instruction(self):
        op = self.code[self.pc]
        self.pc += 1
        return op
    
    def run(self):
        while self.pc < len(self.code):
            op = self.next_instruction()
            if PUSH1 <= op <= PUSH32: # 如果为PUSH1-PUSH32
                size = op - PUSH1 + 1
                self.push(size)
            elif op == PUSH0: # 如果为PUSH0
                self.stack.append(0)
            elif op == POP: # 如果为POP
                self.pop()
            elif op == ADD: # 如果为ADD
                self.add()
            elif op == SUB: # 如果为SUB
                self.sub()
            elif op == MUL: # 如果为MUL
                self.mul()
            elif op == DIV: # 如果为DIV
                self.div()
            elif op == LT: # 处理LT指令
                self.lt()
            elif op == GT: # 处理GT指令
                self.gt()
            elif op == EQ: # 处理EQ指令
                self.eq()
            elif op == AND: # 处理AND指令
                self.and_op()
            elif op == OR: # 处理OR指令
                self.or_op()
            elif op == NOT: # 处理NOT指令
                self.not_op()
            elif op == XOR: # 处理XOR指令
                self.xor_op()

            elif op == MSTORE: # 处理MSTORE指令
                self.mstore()

            elif op == MLOAD: # 处理MLOAD指令
                self.mload()
            elif op == SSTORE: # 处理SSTORE指令
                self.sstore()
            elif op == SLOAD: # 处理SLOAD指令
                self.sload()

            elif op == JUMP: 
                self.jump()
            elif op == JUMPDEST: 
                self.jumpdest()

            elif op == JUMPI: 
                self.jumpi()

            elif DUP1 <= op <= DUP16: # 处理DUP1-DUP16指令
                self.dup(op - DUP1 + 1)

            elif SWAP1 <= op <= SWAP16: # 如果是SWAP1-SWAP16
                self.swap(op - SWAP1 + 1)

            elif op == SHA3: # 如果为SHA3
                self.sha3()

            elif op == STOP: # 处理STOP指令
                print('Program has been stopped')
                break

if __name__ == '__main__':
    
    # add 1+1
    # code = b"\x60\x01\x60\x01" 
    # # （PUSH1 1 PUSH1 1）
    # evm = EVMForPY(code)
    # evm.run()
    # print(evm.stack) 
    # output: [1, 1]

    # add 2+3 （PUSH1 2 PUSH1 3 ADD）
    code = b"\x60\x02\x60\x03\x01"
    evm = EVMForPY(code)
    evm.run()
    print(evm.stack)
    # output: [5]
