package main

import (
	"fmt"
	"onchain-monitor/internal/api"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

func main() {
	e := echo.New()
	e.Use(middleware.Logger())
	e.Use(middleware.Recover())

	// 路由注册
	e.GET("/", func(c echo.Context) error {
		return c.File("web/templates/index.html")
	})
	e.Static("/static", "web/static")

	e.GET("/api/prices", api.GetPrices)
	e.GET("/api/system", api.GetSystemInfo)
	e.GET("/api/quotes", api.GetRandomQuote)
	// 新增
	e.GET("/api/eth_top5", api.GetEthTop5)

	port := 8080
	fmt.Printf("✅ 服务已启动: http://localhost:%d\n", port)
	e.Logger.Fatal(e.Start(fmt.Sprintf(":%d", port)))
}
