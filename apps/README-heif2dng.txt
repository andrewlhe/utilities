HEIF → DNG 转换工具（v2）
========================
heif2dng.py 将 iPhone HEIF/HEIC 照片批量转换为 16-bit 线性 DNG（无损）。

一、重要说明
------------
- HEIC/HEIF 是手机拍摄后已经处理完成的成品图像（已去马赛克、降噪、色调映射），
  并不包含原始传感器数据。转换得到的是"线性 DNG"：把成品图像无损封装为 16-bit
  的 DNG 容器，Lightroom / Photoshop / ACR 可直接打开编辑，但动态范围/宽容度
  不会超过原 HEIF，无法恢复已丢失的高光阴影细节。
- v1 版本存在两个致命问题导致 Lightroom 打不开且颜色错误，v2 已全部修复（见
  第五节"修复记录"）。v2 产物经 libraw（rawpy，与 ACR/Lightroom 同类严格读取器）
  渲染验证：可正常解码，且颜色与原图逐像素对比均差约 5~8/255（三通道均衡，
  无偏色）。
- 16-bit、默认不压缩（兼容性最好），完整保留 EXIF / GPS / 拍摄参数元数据。

二、用法
--------
  python heif2dng.py --input "HEIF文件夹" [选项]

  选项：
    --output <目录>      输出目录（默认：源目录同级 DNG 文件夹）
    --compression <模式> uncompressed(默认, 兼容性最好) | deflate(体积小,
                         约 1/3，Adobe 支持，但部分第三方读取器如 libraw 不认)
    --force              覆盖已存在的 DNG 文件
    --dry-run            只统计文件数和体积，不实际转换
    --jobs N             并行线程数（默认 3）
    --limit N            只处理前 N 个文件（0=全部，默认）

  示例：
    python heif2dng.py --input "W:\Travel\2022\iPhone\DJY\HEIF"
    python heif2dng.py --input "W:\..." --output "E:\dng" --force

  双击 heif2dng.bat 可一键重新转换本次的文件夹。

三、依赖
--------
  pillow, pillow-heif, numpy, piexif, tifffile（验证用）, rawpy（验证用）
  （已随本次任务安装到本机 Python）

四、本次运行记录（2026-10-30，v2 全量重转）
------------------------------------------
  输入：W:\Travel\2022\iPhone\DJY\HEIF  —— 440 个 .heif，837 MB
  输出：W:\Travel\2022\iPhone\DJY\DNG   —— 440 个 .dng（v2，覆盖 v1 产物）
  压缩：uncompressed（默认，最大兼容）
  验证：libraw(rawpy) 可解码渲染；标签核对 NewSubFileType=0、WhiteLevel=65535、
        CalibrationIlluminant1=23(D50)、BaselineExposure=0、ColorMatrix1 为
        P3 色域矩阵；渲染与原图（经 ICC 转 sRGB）逐像素均差约 5~8/255。

五、v2 修复记录（针对"Lightroom 打不开 + 颜色错误"）
----------------------------------------------------
  1) 标签号致命错误：v1 把 50717 当作 CalibrationIlluminant1 写成了 21，但
     50717 实际是 WhiteLevel（白电平）。ACR 读到 WhiteLevel=21（约为 65535 的
     0.03%）会把全图判为严重过曝，表现为打不开/异常渲染/颜色崩坏。v2 修正为
     WhiteLevel=65535，并把真正的 CalibrationIlluminant1(50778) 写为 D50(23)。
  2) 必备标签缺失：补上 NewSubFileType、BlackLevel、DefaultScale、
     DefaultCropOrigin/Size、BaselineExposure/Noise/Sharpness、
     LinearResponseLimit、AnalogBalance、AsShotNeutral。
  3) 色域误判：iPhone HEIC 实际是 Display P3（非 sRGB），v1 按 sRGB 处理导致
     高饱和颜色（如蓝天）偏差。v2 检测内嵌 ICC，按 P3 线性化并使用
     P3→XYZ(D50) 色彩矩阵（Bradford 适应），CalibrationIlluminant1=D50。
  4) 格式级：线性 DNG（已去马赛克的 RGB 数据）的 PhotometricInterpretation
     必须用 34892(LinearRaw)，普通 2(RGB) 会被严格 raw 读取器拒绝。v2 已修正。
  5) UniqueCameraModel 改写为 "Apple <机型> (HEIC Linear)"，避免 ACR 按真实
     iPhone 机型匹配相机校准配置。
