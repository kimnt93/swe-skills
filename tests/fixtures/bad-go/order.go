package orders

// Order breaks the go-code struct rule twice; structcheck must report both.
type Order struct {
	ID    string   `json:"id"`
	Price *float64 `json:"price"`
	Note  string   `json:"note,omitempty"`
}
