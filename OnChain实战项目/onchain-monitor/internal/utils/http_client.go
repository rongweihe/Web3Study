package utils

import (
	"encoding/json"
	"io"
	"net/http"
	"strconv"
)

func FetchField(url, field string) float64 {
	resp, err := http.Get(url)
	if err != nil {
		return 0
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var data map[string]interface{}
	json.Unmarshal(body, &data)

	// 处理嵌套结构
	if nested, ok := data["data"].([]interface{}); ok && len(nested) > 0 {
		if m, ok := nested[0].(map[string]interface{}); ok {
			val, _ := strconv.ParseFloat(m[field].(string), 64)
			return val
		}
	}

	valStr, ok := data[field].(string)
	if !ok {
		return 0
	}
	val, _ := strconv.ParseFloat(valStr, 64)
	return val
}
