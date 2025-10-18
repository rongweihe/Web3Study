package service

import (
	"fmt"
	"onchain-monitor/internal/utils"
)

type PriceData struct {
	Symbol string  `json:"symbol"`
	Price  float64 `json:"price"`
}

func FetchAllPrices() []PriceData {
	coins := []string{"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"}
	var results []PriceData

	for _, sym := range coins {
		url := fmt.Sprintf("https://api.binance.com/api/v3/ticker/24hr?symbol=%s", sym)
		price := utils.FetchField(url, "lastPrice")
		results = append(results, PriceData{Symbol: sym, Price: price})
	}

	// OKB
	okb := utils.FetchField("https://www.okx.com/api/v5/market/ticker?instId=OKB-USDT", "last")
	results = append(results, PriceData{Symbol: "OKB", Price: okb})

	// BGB
	bgb := utils.FetchField("https://api.bitget.com/api/spot/v1/market/ticker?symbol=BGBUSDT_SPBL", "close")
	results = append(results, PriceData{Symbol: "BGB", Price: bgb})

	return results
}
