# HF-M10 U-Boot 固定输入

`uboot-stock.img` 是已验证的原厂 2 MiB U-Boot 分区镜像，包含两个相同的
1 MiB `LOADER` 副本。它不是完整 NAND、Userdata、GPT 或设备身份备份。

| 输入/处理阶段 | SHA-256 |
| --- | --- |
| 本目录原厂镜像 | `f4128865814b2aa9407389bfaed198ca26142f769a2e1eb703487c39452d58c6` |
| 音量加 Loader 阈值补丁后 | `610bdf5596915494cc6ecf2819199e88768b755834973cabd97b8ab9a2602e83` |
| 再移除 Recovery 依赖后 | `615a65ebaed99f3065ea868458b323fe0124e9243604c34c777ef0bae11a0d4e` |

构建脚本：`contrib/hf-m10/build-uboot-no-recovery.py`。
这是基于原厂二进制的确定性补丁流程，不是从 U-Boot 源码重新编译。
每阶段均验证摘要、两个副本、LOADER CRC/SHA 和允许修改的字节范围。

下载键比较从 `cmp w0, #30` 改为 `cmp w0, #200`（每个副本偏移
`0x4A9C`），保留 ADC 通道选择和 USB VBUS/Loader 分支。关机后按住音量加、
接 USB 上电进入 Loader；无 USB 时，原 Recovery 路径改为正常 Boot。
该入口依赖 NAND 上仍可加载的 U-Boot。

本目录仅保留原厂二进制输入；原始二进制中的版权和版本信息未改写。
