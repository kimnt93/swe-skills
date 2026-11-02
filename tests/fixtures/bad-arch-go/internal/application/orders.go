package application

// application must not reach into an adapter: archcheck must flag this import.
import _ "example.com/bad/internal/infrastructure/postgres"
