package main

import (
	"os"

	"github.com/williamzhu/auto-coder/async_agent_runner/cmd"
)

func main() {
	if err := cmd.Execute(); err != nil {
		os.Exit(1)
	}
}