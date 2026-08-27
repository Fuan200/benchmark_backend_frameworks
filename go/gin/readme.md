## Gin

Gin is a high-performance HTTP web framework written in Go. It provides a Martini-like API but with significantly better performance—up to 40 times faster—thanks to httprouter. Gin is designed for building REST APIs, web applications, and microservices where speed and developer productivity are essential.

* Programming Language: Golang
* Website: https://gin-gonic.com/
* Docs: https://gin-gonic.com/en/docs/
* Github: https://github.com/gin-gonic/gin

### Installation
* Init:
```bash
mkdir gin
cd gin
go mod init gin
go get github.com/gin-gonic/gin
touch main.go
```
* Dev:
```bash
go run main.go
```
* Build:
```bash
go build -o gin
```

Port: 8080
