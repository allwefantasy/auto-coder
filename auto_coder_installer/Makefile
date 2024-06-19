BINARY_NAME=auto-coder-installer

build:
    mkdir -p ./bin/${BINARY_NAME}-windows
	GOOS=darwin GOARCH=amd64 go build -o ./bin/${BINARY_NAME}-darwin main.go
	GOOS=linux GOARCH=amd64 go build -o ./bin/${BINARY_NAME}-linux main.go
	GOOS=windows GOARCH=amd64 go build -o ./bin/${BINARY_NAME}-windows/${BINARY_NAME}-windows.exe -ldflags="-H windowsgui" gui/main.go	
	cp gui.exe.manifest ./bin/${BINARY_NAME}-windows/${BINARY_NAME}-windows.exe.manifest
	cd ./bin && zip ${BINARY_NAME}-windows.zip ${BINARY_NAME}-windows

clean:
	go clean
	rm ./bin/${BINARY_NAME}-*