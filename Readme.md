# PycMan

面向 2026–2027 学年 Introduction to Computation 的吃豆人大作业原型。游戏由 Python 和 pygame-ce 实现；学生通过完成基础规则，并选做进阶功能，练习状态管理、数据结构与搜索。

**当前状态：**仓库保留教师参考规则，并已加入 S1～S5 的累计任务入口、学生骨架、公开测试和学生发布包生成脚本。A/B/C 进阶功能及隐藏评分尚未实现。这个课程协作仓库含有教师参考规则，不能直接发给学生。

## 任务结构

| 部分 | 内容 | 分值 |
| --- | --- | ---: |
| 基础功能 | S1 通行与移动、S2 拾取与计时、S3 碰撞与胜负、S4 随机幽灵、S5 键盘与转弯缓存；按顺序累计完成 | 60 |
| 进阶功能 | A 道具机制、B 更强的幽灵、C 变化中的迷宫；每类两题，每题 15 分，跨类选做，最高计 30 分 | 30 |
| 实验报告 | 复现场景、行为观察、实现思路与调试记录 | 10 |

逐题行为要求和观察方法见[学生任务说明](docs/student-assignment.md)。[游戏与开发说明](docs/game-guide.md)介绍教师参考游戏。

基础阶段的 GUI 与测试使用 `src/tasks/basic/s1.py` 至 `s5.py` 中的同一份实现；未完成的函数保持可运行的初始行为。教师参考规则单独保存在 `src/teacher_reference.py`，生成的学生包不包含它及教师演示入口。进阶题仍需增加接入点、演示场景和测试。

基础规则通过 `src/rules.py` 的 `GameRules` 接入核心游戏。`Env`、`Agent`、`Player`、`Controller` 和 `Game` 在相应规则启用时直接调用学生接口；阶段规则由 `src/rules.py` 选择，地图和控制器由 `src/game.py` 组装。`src/main.py` 默认运行 S1，教师演示使用 `src/teacher_main.py`。

## 运行

需要 Python 3.10+ 和 `requirements.txt` 中的依赖。在仓库根目录运行：

```bash
python -m pip install -r requirements.txt
python src/main.py
python src/main.py --stage S1
python src/main.py --stage S2
python src/teacher_main.py
python -m tests framework
python -m tests all
python -m tests S3
python scripts/build_student_package.py
```

基础阶段可运行 `S1` 至 `S5`。`python -m tests framework` 只检查框架；`all` 在框架通过后评分 S1～S5；`S3` 在框架通过后评分 S1～S3。每阶段须同时通过该阶段的公开测试和累计游戏检查，才得到该阶段全部分数，否则为 0 分。框架测试未通过时不运行学生测试。框架测试见 `tests/test_framework.py`，学生测试见 `tests/test_basic.py`。发布脚本生成 `dist/PycMan-student.zip`。

方向键 / WASD 移动，空格 / P 暂停，R 重开，Esc 退出。教师参考游戏还支持 `python src/teacher_main.py --terminal`。

## AI 助手使用

根目录 [AGENTS.md](AGENTS.md) 约定：面向学生时，助手可以解释概念和讨论调试思路，不直接编写可提交的任务答案；教师明确要求的框架、文档和测试维护可以正常进行。这些规则不能作为识别 AI 使用或判定违规的证据。课程正式发布时应进一步明确学生的 AI 使用范围及过程材料要求。
