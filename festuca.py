import os
import shutil
import subprocess
import sys

INIT_GO       = "code/init.go"
INIT_BINARY   = "build/init"
INITRD_ROOT   = "initrd_root"
INITRD_IMG    = "initrd.img"
DISK_IMG      = "festuca.img"
MOUNT_POINT   = "/tmp/festuca_mount"
GRUB_TMP_CFG  = "grub.cfg.temp"

def run(cmd):
    print(f"> {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def clean_all():
    print("[*] Cleaning everything…")
    try:
        run(f"sudo umount {MOUNT_POINT}")
    except:
        pass
    try:
        out = subprocess.check_output("losetup -a", shell=True).decode()
        for line in out.splitlines():
            if DISK_IMG in line:
                dev = line.split(":")[0]
                run(f"sudo losetup -d {dev}")
    except:
        pass
    for path in (INITRD_ROOT, "build", INITRD_IMG, DISK_IMG, GRUB_TMP_CFG):
        shutil.rmtree(path, ignore_errors=True) if os.path.isdir(path) else (
            os.remove(path) if os.path.isfile(path) else None
        )
    print("[*] Clean done.")

def full_build():
    try:
        clean_all()
        os.makedirs(INITRD_ROOT, exist_ok=True)
        os.makedirs("build", exist_ok=True)
        run(f"gccgo -static {INIT_GO} -o {INIT_BINARY}")
        shutil.copy(INIT_BINARY, os.path.join(INITRD_ROOT, "init"))
        run(f"chmod +x {os.path.join(INITRD_ROOT, 'init')}")
        shutil.rmtree("build")
        cwd = os.getcwd()
        os.chdir(INITRD_ROOT)
        for d in ("bin","sbin","etc","dev","proc","sys","tmp","mnt","lib","lib64","usr","var"):
            os.makedirs(d, exist_ok=True)
        run("sudo chmod +x ../package/build/*")
        run("sudo cp ../package/build/* bin/")
        run("sudo mknod dev/null c 1 3")
        run("sudo chmod 666 dev/null")
        run(f"find . | cpio -o --format=newc | gzip > ../{INITRD_IMG}")
        os.chdir(cwd)
        run(f"dd if=/dev/zero of={DISK_IMG} bs=1M count=64")
        run(f"parted {DISK_IMG} --script mklabel msdos")
        run(f"parted {DISK_IMG} --script mkpart primary ext2 1MiB 100%")
        loop = subprocess.check_output(
            f"sudo losetup --show --find --partscan {DISK_IMG}", shell=True
        ).decode().strip()
        run(f"sudo mkfs.ext2 {loop}p1")
        os.makedirs(MOUNT_POINT, exist_ok=True)
        run(f"sudo mount {loop}p1 {MOUNT_POINT}")
        run(f"sudo mkdir -p {MOUNT_POINT}/boot/grub")
        run(f"sudo cp distro/bzImage {MOUNT_POINT}/boot/vmlinuz")
        run(f"sudo cp {INITRD_IMG} {MOUNT_POINT}/boot/initrd.img")
        grub_cfg = """
set timeout=5
set default=0

menuentry "Festuca" {
    linux /boot/vmlinuz rdinit=/init
    initrd /boot/initrd.img
}
"""
        with open(GRUB_TMP_CFG, "w") as f:
            f.write(grub_cfg)
        run(f"sudo tee {MOUNT_POINT}/boot/grub/grub.cfg < {GRUB_TMP_CFG} > /dev/null")
        run(f"""sudo grub-install \
            --target=i386-pc \
            --boot-directory={MOUNT_POINT}/boot \
            --modules="normal part_msdos ext2" \
            --force --no-floppy \
            --root-directory={MOUNT_POINT} \
            {loop}""")
        run(f"sudo umount {MOUNT_POINT}")
        run(f"sudo losetup -d {loop}")
        run(f"qemu-system-x86_64 -hda {DISK_IMG} -m 512M -enable-kvm -vga std")
    except Exception as e:
        print(f"[!] Error: {e}")
        clean_all()
        sys.exit(1)

def main():
    print("""
Festuca
===============
1) Build & run (clean first, then full pipeline)
2) Clean all generated files
0) Exit
""")
    choice = input("Select an option: ").strip()
    if choice == "1":
        full_build()
    elif choice == "2":
        clean_all()
    else:
        print("Bye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
