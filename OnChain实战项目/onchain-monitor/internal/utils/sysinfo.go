package utils

import (
	"fmt"
	"runtime"
	"time"
)

func GetSystemStats() map[string]interface{} {
	var m runtime.MemStats
	runtime.ReadMemStats(&m)

	return map[string]interface{}{
		"cpu":   "N/A (MacOS 默认展示)",
		"memMB": fmt.Sprintf("%.2f MB", float64(m.Alloc)/1024/1024),
		"goNum": runtime.NumGoroutine(),
		"time":  time.Now().Format("2006-01-02 15:04:05"),
	}
}
