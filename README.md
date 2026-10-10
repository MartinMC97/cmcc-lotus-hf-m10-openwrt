# 和家小荷 MINI 10 / CMCC HF-M10 OpenWrt

本仓库是官方 OpenWrt `v25.12.5` 的完整源码分支，设备标识为
`cmcc-lotus-hf-m10`，OpenWrt 型号为 `HF-M10`。内核保持已适配的 **6.12.108**，
用户态和 packages/LuCI 使用 25.12.5 正式版固定提交。

## 构建

安装 OpenWrt 宿主机构建依赖，使用非 root 用户，在仓库根目录执行：

```sh
./scripts/feeds update -a
./scripts/feeds install -a
cp configs/cmcc-lotus-hf-m10.config .config
make defconfig
make menuconfig  # 可选：Rockchip → CMCC HF-M10 → CMCC HF-M10
make download -j4
make -j4
```

使用 OpenWrt 自建工具链，不需要预先安装 SDK，不需要另一个 Lotus Mini 工程。
构建配置默认内置 Dropbear、HTTP/HTTPS LuCI、USB 串口、Wi-Fi、蓝牙及板级驱动。
新产物验证状态见 [迁移记录](docs/hf-m10/MIGRATION.md)。

输出位于 `bin/targets/rockchip/hf_m10/`：配对的 `*-boot.img`（17 MiB）、
`*-rootfs.squashfs`（35 MiB），以及 Boot 配对摘要。普通升级只刷 Boot/Rootfs，
不写 Userdata、GPT、U-Boot、Trust 或 DDR Loader。

## 设备与安装

这是 RK3308 NAND/SFTL 设备的专用目标，默认布局已删除 Recovery、扩充 Boot。
Rootfs 起始 `0xD000`、Userdata 起始 `0x1E800`；Userdata 长度保持本机原值。
镜像只适用于已验证的新布局设备，不是原厂首装或通用 sysupgrade 镜像。
切根 initramfs 通过 `switch_root` 启动 OpenWrt，保留 Squashfs＋ext4 overlay。
既有 `lotus-openwrt-v1` 持久目录和身份标记保持兼容，不自动格式化或清除用户设置。

USB 默认只有 CDC ACM 串口，115200、8N1、无流控；使用 root 和本机密码登录。
Windows 查看设备管理器 COM；Linux 查看 `/dev/serial/by-id/`。串口工具：
`python3 contrib/hf-m10/serial-terminal.py /dev/ttyACM0`（需要端口访问权限）。
新系统默认主机名 `cmcc-lotus-hf-m10`；原有自定义主机名、网络和密钥保持。

硬件服务、HA 语音卫星和对应 LuCI 应用仍由独立项目提供，不默认内置。
升级保留 Userdata 中已安装的应用；迁移源码布局不等于完成应用包数据库升级。
旧 Snapshot overlay 的 APK 状态需另行迁移，暂勿批量 `apk upgrade` 或混装官方 kmod。

迁移分区前，保存本机完整离线 NAND/Userdata，验证音量加＋USB 上电进入 Loader。
恢复依赖 NAND 上可用的 U-Boot，不能替代独立 Maskrom。通用 sysupgrade 尚未适配。

## 源码组织

- `target/linux/rockchip/hf_m10/`：专用目标配置与板级默认文件。
- `target/linux/rockchip/files-6.12/`、`patches-6.12/`：设备树、NAND/SFTL、音频和温控适配。
- `target/linux/rockchip/image/hf_m10.mk`：原生配对镜像配方。
- `package/cmcc-lotus-hf-m10/`：板级软件包、静态 BusyBox、preinit 和 initramfs 源码。
- `tools/hf-m10-resource/`：从源码构建的 Rockchip RSCE 宿主机工具。
- `scripts/cmcc-lotus-hf-m10/`：镜像格式封装与切根 initramfs 构造。
- `contrib/hf-m10/`：离线 GPT、Userdata、U-Boot 维护和串口工具；不参与普通刷写。
- `tests/hf-m10/`、`docs/hf-m10/`：行为回归、来源和验收记录。

[上游 OpenWrt](https://github.com/openwrt/openwrt) 使用 GPL-2.0；
第三方代码保留原有版权与许可证声明。
