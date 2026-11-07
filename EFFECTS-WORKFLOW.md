# 按键、动效、音效：同一条本地编译链

## 已实现的第一段

```sh
npm run skin:full
npm run test:effects
```

`skin:full` 先调用原创底包生成器，再编译效果层，输出 `artifacts/original-full-09/`：

- `original-full-prototype-09.bds`：完整基础效果原型。
- `base/`：无动效/音效的基础包和结构报告，方便对照。
- `validation.json`：绑定、音频解码、电平、时长、哈希及验证边界。
- `preset.json`：本次编译参数。
- `original-sound-masters/`：三种原创合成 WAV 母版；BDS 同时含真正编码的 Ogg Vorbis。

支持 `--output 新目录` 与 `--preset 参数JSON`。现有目录不覆盖；失败不留下半成品输出。
标准参数见 `scripts/cloud/presets/soft-tap.json`。效果编译器只接受新生成、尚未绑定效果的基础包；不将已有动画/音效包当作通用可重编译工程，发现已有绑定会明确拒绝。

### 按键

- 字母键/功能键都有独立普通色、按下色（NM_COLOR / HL_COLOR）。
- 已有原创背景 PNG/TIL，可通过图片替换工作流更换背景。
- 按下动作绑定缩放，松开绑定恢复；不更改 VIEW_RECT、CENTER、SHOW 或方向动作。
- **尚未实现**任意键帽图集的自动生成/逐键替换。当前不是完整的定制键帽美术系统。

### 动效

- 生成 `res/anim.ini`，两段 CATEGORY=0 / TYPE=4 基础缩放。
- 默认按下 70ms 从 100% 缩到 96%，松开 100ms 回到 100%，无无限循环。
- 绑定链：KEY.ANIM_STYLE → CSS PRESS_ANIM / RELEASE_ANIM → ANIM1 / ANIM2。
- 580 个实体键绑定效果；6 个由原生引擎填充的候选区域 F55 不加装饰效果。
- 当前只编译这套有限基础动效，不支持任意图、粒子、GIF 或复杂组合。

### 音效

- 三种声音从数学波形与短包络独立合成，不取自任何商业皮肤或外部音库。
- 默认长度 55ms，普通键/空格/删除分别使用不同音高。原始峰值预算最多 0.15，参数超限会拒绝。
- WAV 经仓库已有本地 WASM 编码器转换为 Android 原生 Ogg Vorbis，绝不是改后缀。
- 绑定链：KEY.SOUND_STYLE → CSS PRESS_SOUND_PATH → 实际 Ogg 文件。
- 用同仓库解码器重新解码每个声音，检查非空、时长和峰值。系统最终响度和输入法音效开关仍需真机验证。

## 与换图衔接

把 `bds_visual.py build` 的 template 设为 full 原型，把 target 设为 `res/panel.png`。图片替换器保留所有动画、声音、配置条目逐字节不变。
`test:effects` 已覆盖这条链，不需要在网页里手工另存文件。

## 自动验收与尚未证明的事

已检查：

- 原布局/动作/SHOW/LIST 保留；所有动画与音效绑定存在。
- 普通/按下颜色不同；KeySkin 模型在 0/35/70ms 缩放采样正确，松开模型在 100ms 恢复。
- 声音真正编码/解码，峰值与时长在限制内；WAV 母版可重复生成。
- BDS 可被 KeySkin 解析、ZIP 往返一致；换图后音频、动画及动作原字节不变。

**尚未检查**：安卓百度输入法的实际九键输入、按下/松开中断与连续点击、动画时序、声音开关/音量、原生字体和视觉效果。不能把编辑器模型测试当作真机通过。

## 后续统一素材描述文件

当前 preset 是第一段参数文件，不是完整通用 manifest。后续应拆成五层：

1. layout/actions：输入语义，独立回归并冻结。
2. visuals：原创背景、键帽正常/按下 PNG 图集、TIL 与字体母版。
3. motion：基础/组合/帧/粒子，带时长、循环及粒子预算。
4. sound：原创或获授权的母版、响度预算、转换目标。
5. targets：主题、横竖屏、具体键/键类绑定。

每次保存原始参数、资源哈希、工具版本、验证报告。新增粒子/GIF和任意声音导入前，需要资源闭包检查、循环图检查、图集打包与原生运行测试，而不是只把字段塞进 ZIP。

## 支持依据及许可

- `src/atlas.ts`、`src/tiles.ts`：NM_IMG/HL_IMG、切片与拉伸。
- `src/legacy-animation.ts`、`src/legacy-animation-binding.ts`：anim.ini、事件与样式绑定。
- `src/sounds.ts`：按键声音继承、Android Ogg、本地无 document 的编码路径。
- `src/bds-package.ts`：Info CRLF、GLOBAL 位于样式表首、继承段与 128 张图资源预算。

本实现直接复用 KeySkin 的解析、动画模型、音频转换模块，遵守仓库 AGPL-3.0；未把它描述为无条件可闭源搬用的代码。
