package main

import (
  "net/http"

  "github.com/gin-gonic/gin"
)

func main() {
  // Create a Gin router with default middleware (logger and recovery)
  r := gin.Default()

  // Define a simple GET endpoint
  r.GET("/", func(c *gin.Context) {
    // Return JSON response
		// c.JSON(http.StatusOK, gin.H{
		//   "message": "pong",
		// })
	c.String(http.StatusOK, "Hello World!")
  })

  // Start server on port 8080 (default)
  r.Run()
}