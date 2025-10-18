package api

import (
	"net/http"
	"onchain-monitor/internal/utils"

	"github.com/labstack/echo/v4"
)

func GetRandomQuote(c echo.Context) error {
	quote := utils.GetRandomQuote()
	return c.JSON(http.StatusOK, map[string]string{"quote": quote})
}
