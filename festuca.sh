#!/bin/bash

cd third-party/busybox
find . | cpio -o --format=newc | gzip > ../../initrd.img
cd ../../
dd if=/dev/zero of=festuca.img bs=1M count=64
parted festuca.img --script -- mklabel msdos
parted festuca.img --script -- mkpart primary ext2 1MiB 100%
LOOPDEV=$(sudo losetup --show --find --partscan festuca.img)
echo $LOOPDEV
sudo mkfs.ext2 ${LOOPDEV}p1
mkdir -p /tmp/festuca_mount
sudo mount ${LOOPDEV}p1 /tmp/festuca_mount
sudo mkdir -p /tmp/festuca_mount/boot/grub
sudo cp distro/bzImage /tmp/festuca_mount/boot/vmlinuz
sudo cp initrd.img /tmp/festuca_mount/boot/initrd.img
cat <<EOF | sudo tee /tmp/festuca_mount/boot/grub/grub.cfg
set timeout=0
set default=0

menuentry "Festuca Linux" {
    linux /boot/vmlinuz console=tty0 rdinit=/init
    initrd /boot/initrd.img
}
EOF
sudo grub-install \
  --target=i386-pc \
  --boot-directory=/tmp/festuca_mount/boot \
  --modules="normal part_msdos ext2" \
  --force \
  --no-floppy \
  --root-directory=/tmp/festuca_mount \
  ${LOOPDEV}
sudo umount /tmp/festuca_mount
sudo losetup -d ${LOOPDEV}
qemu-system-x86_64 -hda festuca.img -m 512M -enable-kvm
rm -rf festuca.img initrd.img