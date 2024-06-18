package cmd

import (
	"fmt"
	"os/exec"
	"runtime"

	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(installCmd)
}

var installCmd = &cobra.Command{
	Use:   "install",
	Short: "Install Auto-Coder",
	Long:  `Download and install Miniconda, create the auto-coder environment, and install the auto-coder package.`,
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("Downloading Miniconda...")
		downloadMiniconda()

		fmt.Println("Installing Miniconda...")
        installMiniconda()

		fmt.Println("Creating auto-coder environment...")
		createEnvironment()

		fmt.Println("Installing auto-coder package...")
		installAutoCoder()

		fmt.Println("Starting Ray cluster...")
		startRayCluster()
	},
}

func downloadMiniconda() {
	url := ""
	switch runtime.GOOS {
	case "darwin":
		url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
	case "linux":
		url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
	case "windows":
		url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
	}
	if runtime.GOOS == "windows" {
		exec.Command("curl", "-o", "miniconda.exe", url).Run()
	} else {
		exec.Command("wget", "-O", "miniconda.sh", url).Run()
	}
}

func installMiniconda() {
	if runtime.GOOS == "windows" {
		exec.Command("miniconda.exe", "/S", "/D=%UserProfile%\Miniconda3").Run()
	} else {
		exec.Command("bash", "miniconda.sh", "-b").Run()
	}
}

func createEnvironment() {
	exec.Command("conda", "create", "--name", "auto-coder", "python=3.10.11", "-y").Run()
}

func installAutoCoder() {
	exec.Command("conda", "run", "-n", "auto-coder", "pip", "install", "-U", "auto-coder").Run()
}

func startRayCluster() {
	exec.Command("conda", "run", "-n", "auto-coder", "ray", "start", "--head").Run()
}