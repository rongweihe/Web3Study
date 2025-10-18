package api

import (
	"net/http"
	"onchain-monitor/internal/service"

	"github.com/labstack/echo/v4"
)

func GetPrices(c echo.Context) error {
	data := service.FetchAllPrices()
	return c.JSON(http.StatusOK, data)
}
