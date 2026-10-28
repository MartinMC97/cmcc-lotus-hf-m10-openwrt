# HF-M10 GitHub Actions 固件包

本包用于 CMCC 和家小荷 MINI 10 / HF-M10（RK3308 NAND/SFTL）。
包含原生 OpenWrt 25.12.5 / Linux 6.12.108、17 MiB Boot、35 MiB Rootfs，
以及音量加＋USB 进入 Loader、无 Recovery 布局使用的 U-Boot。
Actions 执行离线校验，不会连接设备；每次新构建仍需实机验收。

## 文件与地址

LBA 的单位为 **512 字节**。以下是新布局中的原始扇区地址，不是分区编号。

| 文件 | 起始 LBA | 长度 | 用途 |
| --- | --- | --- | --- |
| `upgrade/rootfs.squashfs` | `0xD000`（53248） | 35 MiB | 与 Boot 成对使用 |
| `upgrade/boot.img` | `0x4800`（18432） | 17 MiB | Android boot v0，含内核及切根 initramfs |
| `maintenance/uboot/uboot.img` | `0x2000`（8192） | 2 MiB | 独立维护/原厂迁移步骤，普通升级不刷 |
| `first-install/userdata-94175-sectors.img` | `0x1E800`（124928） | 94175 sectors | 可选，仅首次安装且本机长度匹配 |
| `first-install/userdata-95711-sectors.img` | `0x1E800`（124928） | 95711 sectors | 可选，仅首次安装且本机长度匹配 |

两份 Userdata 镜像是**二选一**，写入会清空该分区。它们不会含有出厂身份或
任何已有配置。普通升级不写 Userdata、GPT、U-Boot、Trust、Misc 或 DDR Loader。
Boot 内的 Rootfs SHA-256 必须与同包 Rootfs 匹配，不可跨构建混用。

`manifest.json` 记录本次源码和 feeds 提交、各镜像大小、摘要及地址；
`metadata/` 含实际构建配置和离线校验报告。解压后先校验：

```sh
sha256sum -c SHA256SUMS
```

Windows 可用 `Get-FileHash -Algorithm SHA256 文件路径` 对照 `SHA256SUMS`；
不能仅根据文件名、文件长度或工具显示 Download OK 判断一致。

## 已经迁移到 17 MiB Boot 布局的设备

1. 关机，按住音量加，接 USB 上电，确认进入 Rockchip Loader。
2. 核对当前分区表：Boot 起始 `0x4800`、长度 `0x8800` sectors，Rootfs
   起始 `0xD000`、长度 `0x11800` sectors；不应存在独立 Recovery 条目。
3. 用 RKDevTool 的原始地址镜像行或支持对应分区名的维护工具，先写
   `upgrade/rootfs.squashfs`，再写 `upgrade/boot.img`，中途不复位。
4. 完整读回两段并与本包逐字节或 SHA-256 比较，通过后再复位。

原厂布局的 Boot 地址为 `0xA800`，**不能**把本包 17 MiB Boot 写到该地址。
本包不是通用 sysupgrade 或整盘镜像。

## 原厂设备迁移到新布局

先在本地保存本机完整离线 NAND 逻辑备份，并保留它的权限保护。
不要把完整备份、Userdata、GUID 或设备专属刷机配置上传到 GitHub。

### U-Boot 与 Loader 入口

本包 U-Boot 来自固定的原厂镜像，原厂 SHA-256 为
`f4128865814b2aa9407389bfaed198ca26142f769a2e1eb703487c39452d58c6`，
音量加阈值补丁后的旧版本为
`610bdf5596915494cc6ecf2819199e88768b755834973cabd97b8ab9a2602e83`。
输出必须为
`615a65ebaed99f3065ea868458b323fe0124e9243604c34c777ef0bae11a0d4e`。
如果本机 U-Boot 既不是上述两个输入，也不是该输出，停止使用此 U-Boot 包。

这是确定性的原厂二进制补丁，不是从 U-Boot 源码重编。先仅更新 U-Boot
分区、完整读回，再分别验证正常开机和关机后按音量加＋USB 进入 Loader。
无 USB 时按音量加改走正常 Boot；原 Recovery 请求也改走 Boot。
这个入口仍依赖 NAND 上可执行的 U-Boot，不能替代独立 Maskrom 恢复。

### 从本机备份生成 GPT

每台设备的 GUID、副 GPT 位置及 Userdata 长度可能不同，本包不附带通用 GPT。
在本地执行（输出目录须尚不存在）：

```sh
python3 tools/gpt-layout.py /path/to/this-unit-full-nand.img \
  --candidate-directory /path/to/this-unit-new-gpt
```

该工具会验证主、副 GPT 和已知原厂分区几何，保持本机 GUID、Rootfs、Userdata
以及额外 SFTL 尾部不变，仅移除 Recovery 条目并把 Boot 扩展到 17 MiB。
读取输出 `layout.json`，其中 `backup_lba` 是副 GPT 片段的实际写入位置；
**不能**一律使用容量末尾或另一台机器的副 GPT 地址。
`parameter-layout-reference.txt` 只是布局参考文字，不能作为 Parameter 镜像刷入。

### 迁移写入

重新进入 Loader 后，在一次维护中按本机计划写入 Rootfs、新地址 Boot，以及
本机生成的副 GPT、主 GPT，中途不复位。若首次安装需要空白 ext4 Userdata，
还应在启动新系统前写入与本机长度完全匹配的那一份空镜像；已有 OpenWrt
持久数据应保留，不要刷空。工具的 GPT 输出不等于已经包含 Userdata 备份。

完整读回全部写入范围，确认与候选一致；确认其余分区未改变后再复位。
使用 Windows RKDevTool 时手动核对原始地址，不套用旧布局的 Boot 行，
也不勾选 Loader、Parameter、Trust、Misc 或其他未列入本机计划的行。

## USB 串口登录

正常启动后 USB 提供 CDC ACM 串口，无 ADB。参数为 115200、8N1、无流控。
Windows 查看设备管理器 COM；Linux 查看 `/dev/serial/by-id/`，或执行：

```sh
python3 tools/serial-terminal.py /dev/ttyACM0
```

使用 root 和本机密码登录；全新系统先通过串口执行 `passwd` 设置密码，再配置
Wi-Fi。固件没有预置 Wi-Fi 凭据、root 密码或 SSH 主机私钥。已有持久目录和
用户配置会保留，默认不内置独立项目中的硬件服务或 HA 语音卫星。
