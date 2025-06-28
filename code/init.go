package main

import (
	"fmt"
	"os"
	"os/exec"
	"syscall"
)

func main() {
	fmt.Println("Welcome to Festuca!\nLaunching toybox")
	cmd := exec.Command("/bin/toybox-x86_64", "sh")
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Setsid:  true,
		Setctty: true,
		Ctty:    int(os.Stdin.Fd()),
	}

	if err := cmd.Run(); err != nil {
		fmt.Println(err)
		select {}
	}

	select {}
}
