package utils

import (
	"encoding/json"
	"io/ioutil"
	"log"
	"net/http"
	"strconv"
)

// func FetchField(url, field string) float64 {
// 	resp, err := http.Get(url)
// 	if err != nil {
// 		return 0
// 	}
// 	defer resp.Body.Close()

// 	body, _ := io.ReadAll(resp.Body)
// 	var data map[string]interface{}
// 	json.Unmarshal(body, &data)

// 	// 处理嵌套结构
// 	if nested, ok := data["data"].([]interface{}); ok && len(nested) > 0 {
// 		if strings.Contains(url,"api.bitget.com") {
// 			if m, ok := nested[field].(string); ok {
// 				val, _ := strconv.ParseFloat(m, 64)
// 				return val
// 			}
// 		}
// 		if m, ok := nested[0].(map[string]interface{}); ok {
// 			val, _ := strconv.ParseFloat(m[field].(string), 64)
// 			return val
// 		}
// 	}

// 	valStr, ok := data[field].(string)
// 	if !ok {
// 		return 0
// 	}
// 	val, _ := strconv.ParseFloat(valStr, 64)
// 	return val
// }

func FetchField(url string, field string) float64 {
	resp, err := http.Get(url)
	if err != nil {
		log.Printf("HTTP GET %s error: %v", url, err)
		return 0
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		log.Printf("Read body error: %v", err)
		return 0
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		log.Printf("JSON Unmarshal error: %v", err)
		return 0
	}

	// 1️⃣ 先判断是否有嵌套 data 对象 // bitget 返回的 data json 结构
	var target map[string]interface{}
	if dataRaw, ok := result["data"]; ok {
		switch dataVal := dataRaw.(type) {
		case map[string]interface{}:
			target = dataVal
		case []interface{}:
			// 如果是数组，取第一个元素
			if len(dataVal) > 0 {
				if first, ok := dataVal[0].(map[string]interface{}); ok {
					target = first
				}
			}
		default:
			log.Printf("未知 data 类型: %T", dataVal)
		}
	} else {
		// 没有嵌套 data，直接用 root
		target = result
	}

	if target != nil {
		valStr, ok := target[field].(string)
		if !ok {
			return 0
		}
		val, _ := strconv.ParseFloat(valStr, 64)
		return val
	}

	log.Printf("[FetchField 字段 %s 未找到", field)
	return 0
}
