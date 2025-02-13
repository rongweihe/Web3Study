import ABI from "../ABI.json";

const bank_address = "0xdFc1e783cFfE018Dce6A1e80f1fAeF42Ecdb2959";

const newBankContract = web3 => {
    return new web3.eth.Contract(ABI, bank_address);
};

export default newBankContract;
