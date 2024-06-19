package main

import (
	"auto-coder/installer/cmd"

	"github.com/lxn/walk"
	. "github.com/lxn/walk/declarative"
)

func main() {
	var window *walk.MainWindow

	MainWindow{
		AssignTo: &window,
		Title:    "Auto-Coder Installer",
		Size:     Size{400, 300},
		Layout:   VBox{},
		Children: []Widget{
			PushButton{
				Text: "Install Auto-Coder",
				OnClicked: func() {
					cmd.Execute()
				},
			},
		},
	}.Create()

	window.Run()
}
