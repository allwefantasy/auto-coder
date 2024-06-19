BINARY_NAME=auto-coder-installer

build:
	GOOS=darwin GOARCH=amd64 go build -o ./bin/${BINARY_NAME}-darwin main.go
	GOOS=linux GOARCH=amd64 go build -o ./bin/${BINARY_NAME}-linux main.go
	GOOS=windows GOARCH=amd64 go build -o ./bin/${BINARY_NAME}-windows.exe -ldflags="-H windowsgui" -manifest gui.manifest gui/main.go  

clean:
	go clean
	rm ./bin/${BINARY_NAME}-*