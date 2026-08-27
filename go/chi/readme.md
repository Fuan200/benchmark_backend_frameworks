## chi

`chi` is a lightweight, idiomatic and composable router for building Go HTTP services. It's especially good at helping you write large REST API services that are kept maintainable as your project grows and changes. `chi` is built on the new context package introduced in Go 1.7 to handle signaling, cancelation and request-scoped values across a handler chain.

* Programming Language: Golang
* Website: https://go-chi.io/
* Docs: https://go-chi.io/#/README
* Github: https://github.com/go-chi/chi

### Installation
* Init:
```bash
mkdir chi
cd chi
go mod init chi
go get github.com/go-chi/chi/v5
touch main.go
```
* Dev:
```bash
go run main.go
```
* Build:
```bash
go build -o chi
```

Port: 3000
