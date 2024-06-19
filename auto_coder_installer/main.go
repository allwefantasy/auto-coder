package main

import (
	"auto-coder/installer/cmd"
	"auto-coder/installer/gui"
	"runtime"
)

func main() {
	if runtime.GOOS == "windows" {
		gui.main()
	} else {
		cmd.Execute()
	}
}