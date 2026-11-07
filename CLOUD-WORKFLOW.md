# 云端图片 → BDS 最小工作流

完整可视示例：[雾紫轻触10](MIST-LILAC.md)，一键 `npm run skin:mist`。

需要不依赖供体的原创底包时，参见 [原创底包生成器](ORIGINAL-BASE.md)。它与下述图片替换器是两个独立入口。

不用桌面、不用 Android SDK、不用浏览器保存框，也不需要 AI API key。
本模块是明确受限的 **PNG 视觉资源替换器**，不是从整张键盘截图识别布局或一键克隆皮肤的系统。
保留模板内所有布局、点击/滑动/长按动作、文字、样式、TIL 切片和元信息。

## 环境与一键验证

Python 3.10+，Pillow 13.0.0。Node 24 用于原编辑器验证。

```sh
python -m pip install -r scripts/cloud/requirements.txt
npm run test:cloud
npm run skin:demo
```

`skin:demo` 用原创程序生成的浅蓝渐变 PNG 替换仓库附带 `public/default-template.bds` 的 `res/back1.png`，输出：

- `artifacts/cloud-demo/original-background.png`：输入素材
- `artifacts/cloud-demo/plan.json`：可重复执行的替换清单
- `artifacts/cloud-demo/result/skin.bds`：输出包
- `artifacts/cloud-demo/result/report.json`：输入/输出哈希与每一个未修改条目的哈希
- `artifacts/cloud-demo/result/assets-before-after.png`：实际资源前后对照，不是完整键盘渲染

输出目录已存在时会拒绝覆盖。再次运行可指定新目录：

```sh
npm run skin:demo -- --output artifacts/demo-2
```

## 使用自己的有权使用的素材

先列出模板的 PNG 资源与尺寸：

```sh
python scripts/cloud/bds_visual.py inspect --template my-template.bds
```

创建 `plan.json`（`image` 路径相对于该清单）：

```json
{
  "replacements": [
    {"target": "res/back1.png", "image": "background.png", "fit": "cover"},
    {"target": "res/bt.png", "image": "button-atlas.png", "fit": "exact"}
  ]
}
```

```sh
python scripts/cloud/bds_visual.py build --template my-template.bds --plan plan.json --output artifacts/my-skin
```

`exact` 是默认：宽高必须与原图一致，适合按键/图标图集。图集中每个图块的位置与透明边界须自行保持。
`cover` 是显式裁切缩放，仅适合背景等无需保持图集位置的图片。原模板可能使用九宫格拉伸，背景在真机上不一定与原图一比一对应。
目前只接受 PNG，且只修改已有 PNG。不会更改模板名称，以避免碰触元信息；因此导入时名称仍与模板一致。
不支持加密、损坏、非标准 ZIP、BDA 或 BDI；这些应先通过 KeySkin 的正式转换/修复流程处理。

## 验收边界

自动重新打开 ZIP；验证文件名与顺序不变、所有未替换条目逐字节一致、新图尺寸一致。
这会覆盖布局、按键动作、切片、CSS 等配置的回归保护，但不证明真机兼容性。
压缩流本身可能重编码，不能宣称整个 BDS 二进制只有 PNG 区域变化。
使用 KeySkin 打开结果检查横竖屏、九键/26 键、候选栏、普通/按下状态，然后在自己的安卓百度输入法实际导入、输入与切换。
没有做真机输入测试，不能把资产对照图当作最终键盘效果。

## 素材与发布

本地 demo 仅使用上游称为官方默认模板的 `public/default-template.bds`，不使用上游另列的互联网整理皮肤。
上游仓库代码有 AGPL-3.0 许可；这不等于独立确认了所有内置图片/模板的再分发权。
生产皮肤请使用自己制作或明确获授权的模板和图片。不要把含私人素材的生成物提交至公开仓库。
本模块不会上传文件、创建仓库、部署网站或发布皮肤。`artifacts/` 已被上游忽略。

## 原编辑器回归

```sh
npm ci --ignore-scripts
npm run verify
npm run build
```

本改动不修改 UI，UI/e2e 套件不作为该 CLI 的已通过项。
GitHub Actions `Cloud BDS checks` 只跑原创合成测试夹具，不上传内置模板或生成皮肤。
