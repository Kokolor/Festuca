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
EFI_SIZE      = "50MiB"

def run(cmd):
    print(f"> {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def clean_all():
    print("[*] Cleaning everything…")
    try:
        run(f"sudo umount -R {MOUNT_POINT} 2>/dev/null")
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
        run(f"dd if=/dev/zero of={DISK_IMG} bs=1M count=128")
        run(f"parted {DISK_IMG} --script mklabel gpt")
        run(f"parted {DISK_IMG} --script mkpart ESP fat32 1MiB {EFI_SIZE}")
        run(f"parted {DISK_IMG} --script set 1 esp on")
        run(f"parted {DISK_IMG} --script mkpart primary ext4 {EFI_SIZE} 100%")

        loop = subprocess.check_output(
            f"sudo losetup --show --find --partscan {DISK_IMG}", shell=True
        ).decode().strip()

        run(f"sudo mkfs.fat -F32 {loop}p1")
        run(f"sudo mkfs.ext4 {loop}p2")
        os.makedirs(MOUNT_POINT, exist_ok=True)
        run(f"sudo mount {loop}p2 {MOUNT_POINT}")
        run(f"sudo mkdir -p {MOUNT_POINT}/boot")
        run(f"sudo mkdir -p {MOUNT_POINT}/boot/efi")
        run(f"sudo mount {loop}p1 {MOUNT_POINT}/boot/efi")
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

        run(f"sudo mkdir -p {MOUNT_POINT}/boot/grub")
        run(f"sudo cp {GRUB_TMP_CFG} {MOUNT_POINT}/boot/grub/grub.cfg")
        run(f"""sudo grub-install \
            --target=i386-pc \
            --boot-directory={MOUNT_POINT}/boot \
            --modules="part_gpt ext2" \
            --force --no-floppy \
            --root-directory={MOUNT_POINT} \
            {loop}""")
        run(f"""sudo grub-install \
            --target=x86_64-efi \
            --boot-directory={MOUNT_POINT}/boot \
            --efi-directory={MOUNT_POINT}/boot/efi \
            --modules="part_gpt ext2 fat" \
            --no-nvram \
            --removable""")

        run(f"sudo ls -lR {MOUNT_POINT}/boot/efi")
        run(f"sudo umount {MOUNT_POINT}/boot/efi")
        run(f"sudo umount {MOUNT_POINT}")
        run(f"sudo losetup -d {loop}")
        ovmf_paths = [
            "/usr/share/edk2-ovmf/OVMF_CODE.fd",
            "/usr/share/edk2-ovmf/x64/OVMF_CODE.4m.fd",
            "/usr/share/OVMF/OVMF_CODE.fd"
        ]
        ovmf_found = None
        for path in ovmf_paths:
            if os.path.exists(path):
                ovmf_found = path
                break

        if ovmf_found:
            print("\n[+] Booting with UEFI support")
            run(f"qemu-system-x86_64 \
                -drive file={DISK_IMG},format=raw \
                -bios {ovmf_found} \
                -m 512M \
                -enable-kvm \
                -vga std")
        else:
            print("\n[!] OVMF not found, booting in BIOS mode")
            run(f"qemu-system-x86_64 -hda {DISK_IMG} -m 512M -enable-kvm -vga std")

    except Exception as e:
        print(f"[!] Error: {e}")
        import traceback
        traceback.print_exc()
        clean_all()
        sys.exit(1)

def main():
    print("""
Festuca OS Builder
==================
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
        print("Ok... C'est moi le creepipi")
        sys.exit(0)

if __name__ == "__main__":
    main()