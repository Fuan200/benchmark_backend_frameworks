package main

import (
    "fmt"
    "net/http"
    "log"

    "github.com/julienschmidt/httprouter"
)

func HelloWorld(w http.ResponseWriter, r *http.Request, _ httprouter.Params) {
    fmt.Fprint(w, "Hello World!")
}

func main() {
    router := httprouter.New()
    router.GET("/", HelloWorld)

    log.Fatal(http.ListenAndServe(":8080", router))
}