package cmd

import (
	"fmt"
	"os/exec"
	"runtime"

	"github.com/spf13/cobra"
)

func checkCondaExists() bool {
	_, err := exec.LookPath("conda")
	return err == nil
}

func init() {
	rootCmd.AddCommand(installCmd)
}

var installCmd = &cobra.Command{
	Use:   "install",
	Short: "Install Auto-Coder",
	Long:  `Download and install Miniconda, create the auto-coder environment, and install the auto-coder package.`,
	Run: func(cmd *cobra.Command, args []string) {
		var downloadStatus, installStatus, envStatus, packageStatus, rayStatus, storageStatus bool

		if !checkCondaExists() {
			fmt.Println("Downloading Miniconda...")
			downloadStatus = downloadMiniconda()

			if downloadStatus {
				fmt.Println("Installing Miniconda...")
				installStatus = installMiniconda()
			} else {
				fmt.Println("Miniconda download failed. Aborting installation.")
				return
			}
		} else {
			fmt.Println("Conda is already installed. Skipping Miniconda download and install.")
			downloadStatus, installStatus = true, true
		}

		if installStatus {
			fmt.Println("Creating auto-coder environment...")
			envStatus = createEnvironment()
		}

		if envStatus {
			fmt.Println("Installing auto-coder package...")
			packageStatus = installAutoCoder()
		}

		if packageStatus {
			fmt.Println("Starting Ray cluster...")
			rayStatus = startRayCluster()

			if rayStatus {
				fmt.Println("Installing BytzerLLM storage...")
				storageStatus = installStorage()
			}
		}

		if downloadStatus && installStatus && envStatus && packageStatus && rayStatus && storageStatus {
			fmt.Println("Auto-Coder installation completed successfully!")
		} else {
			fmt.Println("Auto-Coder installation encountered errors.")
		}
	},
}

func downloadMiniconda() bool {
	url := ""
	switch runtime.GOOS {
	case "darwin":
		url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
	case "linux":
		url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
	case "windows":
		url = "https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
	}
	var out []byte
	var err error
	if runtime.GOOS == "windows" {
		out, err = exec.Command("curl", "-o", "miniconda.exe", url).CombinedOutput()
	} else {
		out, err = exec.Command("wget", "-O", "miniconda.sh", url).CombinedOutput()
	}
	fmt.Printf("%s\n", out)
	return err == nil
}

func installMiniconda() bool {
	if runtime.GOOS == "windows" {
		fmt.Println("Please complete the Miniconda installation through the GUI.")
		cmd := exec.Command("miniconda.exe")
		err := cmd.Start()
		if err != nil {
			return false
		}
		fmt.Println("Press Enter when the Miniconda installation is complete...")
		fmt.Scanln()
		return true
	} else {
		out, err := exec.Command("bash", "miniconda.sh", "-b").CombinedOutput()
		fmt.Printf("%s\n", out)
		return err == nil
	}
}

func createEnvironment() bool {
	pythonVersion := "3.10.11"
	if runtime.GOOS == "windows" {
		pythonVersion = "3.11.9"
	}
	out, err := exec.Command("conda", "create", "--name", "auto-coder", "python="+pythonVersion, "-y").CombinedOutput()
	fmt.Printf("%s\n", out)
	return err == nil
}

func installAutoCoder() bool {
	out, err := exec.Command("conda", "run", "-n", "auto-coder", "pip", "install", "-U", "auto-coder").CombinedOutput()
	fmt.Printf("%s\n", out)
	return err == nil
}

func startRayCluster() bool {
	out, err := exec.Command("conda", "run", "-n", "auto-coder", "ray", "start", "--head").CombinedOutput()
	fmt.Printf("%s\n", out)
	return err == nil
}

func installStorage() bool {
	out, err := exec.Command("conda", "run", "-n", "auto-coder", "byzerllm", "storage", "start").CombinedOutput()
	fmt.Printf("%s\n", out)
	return err == nil
}
