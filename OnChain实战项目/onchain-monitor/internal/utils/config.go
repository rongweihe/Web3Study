package utils

import (
	"encoding/json"
	"math/rand"
	"os"
	"time"
)

func GetRandomQuote() string {
	b, _ := os.ReadFile("internal/data/quotes.json")
	var quotes []string
	json.Unmarshal(b, &quotes)
	rand.Seed(time.Now().UnixNano())
	return quotes[rand.Intn(len(quotes))]
}
