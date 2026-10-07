# 环境坑清单（Windows）

都是实际踩过的，按「症状 → 原因 → 对策」写。

## 中文与编码

1. **PowerShell 5.1 按 GBK/ANSI 解析无 BOM 的 UTF-8 `.ps1`** → 中文字面量乱码、报语法错（`意外的标记"}"`）。
   **注释里的中文也算**。
   - 对策 A：脚本 100% ASCII，中文用码点构造 `-join (@(0x6C42,0x751F) | % {[char]$_})`
   - 对策 B：中文数据放 **UTF-8 JSON**，由脚本读取
   - ⚠️ 若要写含中文的 `.ps1`，**必须存成 UTF-8 with BOM**
2. **中文路径也不能写进 ASCII 脚本**：`Join-Path $ad 'mod备份'` 会因 GBK 解码得到不存在的路径，
   `Test-Path` **静默返回 `$false`**（不报错），看起来像"目录是空的"。对策同上。
3. **`cmd` 批处理里的中文会被按 GBK 解析** → `刷新表格.bat` 保持纯 ASCII，中文提示交给 Node/Python 子进程输出。
4. **`addonlist.txt` 是 GBK/ANSI**（Valve KeyValues）→ 读取要用 `-Encoding Default`，不能用 UTF8。
5. Python 源文件默认 UTF-8，中文可直接写；但**输出**要到控制台时先 `sys.stdout.reconfigure(encoding='utf-8')`。

## PowerShell 语法陷阱

6. **`'前缀'.($x).'后缀'` 不是字符串拼接** —— `.名字` 是成员访问，整段求值为 `$null`。
   后果实例：`-match '^('.($cats -join '|').')-'` 变成 `-match $null`（空模式**恒真**），
   白名单会把文件每一行都当条目。拼正则必须 `$rx = '^(' + ($cats -join '|') + ')-'`
7. **`@(...)` 包裹 `ConvertFrom-Json` 的结果会把整个数组变成一个元素**。
   正确：`$log = Get-Content … | ConvertFrom-Json`，然后 `foreach ($item in $log)`
8. **PSCustomObject 动态属性访问 `$obj.$($key)` 可能返回空** → 用 `$obj.PSObject.Properties[$key].Value`
9. **`-like` 的通配符把 `[ ]` 当字符类**：`$_.Name -like "*…-[Survivors] …*"` **匹配不到**。
   含方括号的文件名要用 `Test-Path -LiteralPath` 或 `.Contains()`
10. **`powershell -File script.ps1 -Path $array` 会把数组摊平成多个位置参数** → 报 `PositionalParameterNotFound`。
    但**进程内 `& script.ps1` 在部分环境会被执行策略直接拦掉**（`AuthorizationManager 检查失败` / `UnauthorizedAccess`，
    即使 `Get-ExecutionPolicy -List` 显示 `CurrentUser=Unrestricted`、文件也无 Zone.Identifier）。
    → 结论：**用 `powershell -NoProfile -ExecutionPolicy Bypass -File <脚本>` 调用，要多个路径就一次调一个**。
    传数组必须在当前会话用 `& '.\script.ps1' -Path $array`
11. **`param()` 必须是 `.ps1` 的第一条语句** —— 给脚本注入公共代码只能插在 `param()` 之后
12. **`param()` 里的默认值必须以逗号结尾**（除最后一项）。漏了逗号会报
    「函数参数列表中缺少")"」这种与真实原因无关的错
13. **`$ErrorActionPreference` 不影响原生命令**；`$LASTEXITCODE` 才反映 robocopy / node 等的退出码

## 文件与路径

14. **`Rename-Item` 对部分中文名会报 "represents a path or device name"** →
    用 `[System.IO.File]::Move([string]$src, [string]$dst)`，并显式把名称转成 `[string]`
15. **`[System.IO.Path]::ChangeExtension($p, $null)` 会保留末尾句点**（`ws_batch6.json` → `ws_batch6.`）→
    拼日志名用 `GetFileNameWithoutExtension`
16. **本机可能没有 `pwsh`**，只有 Windows PowerShell 5.1（`PSEdition=Desktop`）
17. **`python` 可能指向应用商店占位符** `%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe` —— 那不是真解释器。
    用 `sys.executable` 或显式路径
18. `node` 不一定在 PATH 上；DSH 运行时布局通常是
    `<dependencies>\python\python.exe` 与 `<dependencies>\node\bin\node.exe`（即 `python/../../node/bin/node.exe`）

## 运行环境

19. **沙箱为 workspace-write 时**，`node.exe` / `curl.exe` 经管道捕获输出会报 Access is denied；
    需要时请用户放开到 danger-full-access
20. **某些宿主会给子进程注入 `ELECTRON_RUN_AS_NODE=1`**（本意只给 pnpm），
    这会让**任何 Electron 应用退化成 Node 而静默退出** → 启动前 `Remove-Item Env:ELECTRON_RUN_AS_NODE`

## 数据与流程

21. **xlsx 被 WPS/Excel 打开时会产生 `~$xxx.xlsx` 锁文件**，写入会 EBUSY →
    刷新前必须先检测并提示用户关闭（`check_lock.mjs` 就是干这个的）
22. **`fs.accessSync(W_OK)` 对 Office 锁无效** —— 必须真正尝试 `openSync(target, 'r+')`
23. **`write` 出来的文本文件默认 LF**；`.bat` 要 `newline='\r\n'` 才稳
24. **不要用 `[System.IO.File]::WriteAllText` 却不给编码** —— 它会写 UTF-8 无 BOM；
    需要 BOM 时显式 `New-Object System.Text.UTF8Encoding($true)`
25. ⚠️ **全角化替换表必须逐字符核对码点**：`\ / : * ? " < > |` 九个都要映到**对应**的全角形 ——
    `|` 是 **U+FF5C `｜`**，不是 U+FF20 `＠`。2026-10-07 实测 `consolidate5.ps1` 的 `$illegal` 把 `|` 写成
    `0xFF20`：成品名里多出一个语义完全无关的字符，而**没人会去逐字符核对一个长中文名**（靠肉眼看是查不出来的）。
    对策：表格只写一次、由 `MC @()` 码点构造；**回归用 `self_test.py` 的 S10**（一次覆盖九个字符 + 断言不含 `＠`）。

## 自测/验证脚本本身

26. ⚠️ **跑 `self_test.py` 要用 `config.json` 里的 `pythonPath`，不要用 PATH 上的 `python`**：
    2026-10-07 实测用 PATH 里的 `pythoncore-3.14`（无 `openpyxl`）跑出 **7/14**，看起来像重大回归，
    实际是 S1/S3/S6/S6b/S4b/S7/S8 一起因缺依赖假失败。自测内部会调 `verify_fixes.py`、`plan_v4.py` 和刷新链路
    （都吃 `sys.executable`），**解释器选对，全部阶段才成立**。
    同理：`verify_rules.mjs` / `verify_fixes.py` 这类「读 `config.json` 找 workDir」的脚本要跑
    **`<workDir>\_work\` 里的部署副本**（直接跑 clone 里的 `scripts\` 会因为找不到 `_work\` 而崩），
    或先 `$env:L4D2_HOME=<workDir>`。
