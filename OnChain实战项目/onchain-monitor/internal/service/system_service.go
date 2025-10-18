package service

import (
	"onchain-monitor/internal/utils"
)

func GetSystemInfo() map[string]interface{} {
	return utils.GetSystemStats()
}
