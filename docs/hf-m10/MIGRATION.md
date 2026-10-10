# HF-M10 原生源码迁移，2026-10-10

官方设备名称：和家小荷 MINI 10，型号 HF-M10。新设备 profile/镜像标识为
`cmcc-lotus-hf-m10`，设备树首兼容标识为 `cmcc,lotus-hf-m10`，model 为 `HF-M10`。
官方 OpenWrt 原始历史保留；适配基于固定 `v25.12.5`，不是跟踪最新 master。
版本来源见 `provenance.json`。

## 已迁移

- 保留 6.12.108 及上一已验证固件的 generic/rockchip 内核补丁集合。
- NAND/SFTL、Wi-Fi 50 MHz、原厂 B-revision 音频、四键、电池、温控适配。
- Squashfs＋ext4 overlay、分区按名称/几何检查、配对哈希和 switch_root。
- USB 串口密码登录、板级 NTP/网络默认配置、默认内置 SSH/LuCI。
- Boot 17 MiB、Rootfs 35 MiB 的原生镜像配方；不继承 SD/eMMC 升级路径。
- 所有板级包、BusyBox 配置、启动源码与宿主机工具进入本仓库。
  无 `$(TOPDIR)/../`、旧工程目录或预制 SDK 路径依赖。
- 改名只改变新设备/profile/包名/默认主机名/USB 显示标识；保留旧持久目录、
  身份标记、ALSA 卡名及硬件 ABI，防止丢失现有配置或破坏独立应用。
- USB 序列号优先读取本机 U-Boot `androidboot.serialno`，避免两台设备都使用
  `LOTUSMINICONSOLE`。改变 USB 设备实例后 Windows 可能分配新的 COM 号。

## 维护边界

`contrib/hf-m10/build-uboot-no-recovery.py` 只处理摘要固定的原厂 U-Boot 文件，
保持 Loader 按键路径，不接触设备；输出仍需独立实测和完整读回。
普通构建不生成/刷写 U-Boot、DDR Loader、Trust、GPT 或 Userdata。
保留原开发工程中的已验证 Windows 迁移/回滚包和实机私有备份。
它们没有作为新源码或默认首装包导入，更不能跨设备复用。

硬件服务、HA 卫星及它们的 LuCI 界面继续在独立仓库维护，未改变其 API、
配置或默认麦克风策略。本轮迁移不自动安装或启动这些应用。
USB 跨主机恢复问题、APK overlay 升级、通用首装与 sysupgrade 是独立待办。

## 验证

2026-10-10 验证结果：

- 原生 feeds/defconfig 通过，官方 feeds 固定提交匹配。
- 45 项行为/镜像格式/USB 身份回归通过（38＋4＋3）。
- 完整 `make -j4 V=s world` 通过，自建 GCC 14.3.0/musl 工具链；未使用 SDK、
  外部工具链或旧工程的编译对象。仅复用了可校验的源码下载缓存。
- 首轮完整编译在基础包安装阶段发现默认配置脚本文件名遗漏；修正并重新通过
  38 项相关回归后继续完整构建，最终输入提交为 `c78df0b01c`。
- Boot/Rootfs 尺寸、Android 头部、XZ initramfs、静态 BusyBox、LZ4 内核、
  RSCE 设备树、配对 SHA-256 和启动源码一致性核验通过。
- 设备树型号为 `HF-M10`，首兼容标识为 `cmcc,lotus-hf-m10`；Rootfs 为
  25.12.5、`rockchip/hf_m10`、`aarch64_generic`；90 个内核模块均为
  AArch64、6.12.108。默认配置及 USB gadget 与源码逐字节一致。
- ROM 未包含预设 root 密码、SSH 主机私钥、adbd 或 `/openwrt-shell`。

Boot 有效载荷为 4,034,560 字节，余量为 13,791,232 字节。
摘要见 `provenance.json`；本机完整镜像、配置及核验报告保存在忽略目录
`artifacts/native-hf-m10-20261010-c78df0b01c/`，未提交到源码 Git。
首次构建日志位于 `build-logs/native-world-r1.log`，修正后日志为
`build-logs/native-world-r2.log`。

发行版 revision 保持上游正式版的 `r33051-f5dae5ece4`；本 fork 的实际输入提交
另行记录，不根据发行版 revision 推断本地适配提交。
旧工程只清理了生成的 build_dir/staging_dir/tmp，源码、配置、镜像及备份保留。
旧工程的实机结果不等于新改名固件验收，本轮没有刷写、重启或访问设备。
新镜像仍需独立完成启动与硬件测试，不标记为已通过实机验收。
