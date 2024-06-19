BINARY_NAME=auto-coder-installer

build:
	mkdir -p ./bin/${BINARY_NAME}-darwin
	mkdir -p ./bin/${BINARY_NAME}-linux
	GOOS=darwin GOARCH=amd64 go build -o ./bin/${BINARY_NAME}-darwin main.go
	GOOS=linux GOARCH=amd64 go build -o ./bin/${BINARY_NAME}-linux main.go
	
build-win:
	mkdir -p ./bin/${BINARY_NAME}-windows
	GOOS=windows GOARCH=amd64 go build -o ./bin/${BINARY_NAME}-windows/${BINARY_NAME}-windows.exe -ldflags="-H windowsgui" gui/main.go
	cp gui.exe.manifest ./bin/${BINARY_NAME}-windows/${BINARY_NAME}-windows.exe.manifest  
	cd ./bin && zip -r ${BINARY_NAME}-windows.zip ${BINARY_NAME}-windows

build-win-cmd:
	mkdir -p ./bin/${BINARY_NAME}-windows-cmd
	GOOS=windows GOARCH=amd64 go build -o ./bin/${BINARY_NAME}-windows-cmd/${BINARY_NAME}-windows.exe main.go
	cd ./bin && zip -r ${BINARY_NAME}-windows-cmd.zip ${BINARY_NAME}-windows-cmd

clean:
	go clean
	rm -rf ./bin/*