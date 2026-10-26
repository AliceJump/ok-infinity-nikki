# Nikki 标注工程子模块

`x-anylabeling-asset/` 是《无限暖暖》的 X-AnyLabeling **标注源工程**，不属于游戏运行时资源 `assets/`。它已迁移到 [ok-infinity-nikki-x-anylabeling-asset](https://github.com/AliceJump/ok-infinity-nikki-x-anylabeling-asset)，主仓库固定 Git 子模块的特定提交，避免标注图和 JSON 混入应用代码提交与发行包。

## 检出与维护

```powershell
git clone --recurse-submodules https://github.com/AliceJump/ok-infinity-nikki.git
cd ok-infinity-nikki
# 对已存在的本地仓库
git submodule sync --recursive
git submodule update --init --recursive
```

编辑标注源工程时，在素材仓库单独提交、测试；更新主仓库的子模块指针前检查远端 SHA、文件内容和 `git diff --submodule=log`，然后经 PR 审查。不应直接改写已发布的素材仓库历史，也不应手工把原始素材复制回主仓库。

## 迁移验证

源仓库：`AliceJump/ok-infinity-nikki` 的 `main` 提交 `180859128db637f769ea478f52fbae57d46210fa` 的 `x-anylabeling-asset/` 子树。

对应拆出的提交：`592f0adf22abf7509ea88670a6a51b00d7f17a92`；子树 Git tree `b3763b6d4a47c01951152eaaab580b046c15cab6`。

对比结果：16 个原文件，53,724,740 字节，所有相对路径及 Git blob SHA 完全一致。素材仓库保留了 Git subtree 历史，母仓库通过 gitlink 固定上面的提交。

发行时确保 `deploy.txt` 不把标注源工程加入用户端安装包；正常运行时使用 `assets/` 下的生成模板。
