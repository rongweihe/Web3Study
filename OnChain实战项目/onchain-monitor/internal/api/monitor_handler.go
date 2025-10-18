// 文件路径: internal/api/monitor_handler.go
package api

import (
	"net/http"
	"onchain-monitor/internal/service"

	"github.com/labstack/echo/v4"
)

// GetSystemInfo 返回系统信息（CPU/内存/指标等）
// 由 cmd/main.go 中路由 /api/system 调用
func GetSystemInfo(c echo.Context) error {
	info := service.GetSystemInfo()
	return c.JSON(http.StatusOK, info)
}
