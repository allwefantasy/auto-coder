package cmd

import (
	"fmt"
	"os"
	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "auto-coder-installer",
	Short: "Auto-Coder installation tool",
	Long: `This tool will install Miniconda, create an auto-coder environment,
and install the latest auto-coder package.`,
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("Use 'auto-coder-installer install' to begin installation.")
	},
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}