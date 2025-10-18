package api

import (
	"encoding/json"
	"net/http"
	"os"

	"github.com/labstack/echo/v4"
)

// 结构定义
type EthTransfer struct {
	From   string  `json:"from"`
	To     string  `json:"to"`
	Amount float64 `json:"amount"`
	Time   string  `json:"time"`
}

// GetEthTop5 返回最近的 Top5 转账信息
func GetEthTop5(c echo.Context) error {
	data, err := os.ReadFile("data/eth_top.json")
	if err != nil {
		return c.JSON(http.StatusOK, []EthTransfer{})
	}

	var list []EthTransfer
	if err := json.Unmarshal(data, &list); err != nil {
		return c.JSON(http.StatusOK, []EthTransfer{})
	}

	return c.JSON(http.StatusOK, list)
}
