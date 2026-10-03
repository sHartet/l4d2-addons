# Steam 创意工坊 API 与 .url 快捷方式

## 批量查条目信息（不要逐个抓网页）

```
POST https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/
Content-Type: application/x-www-form-urlencoded
body: itemcount=N&publishedfileids[0]=<id>&publishedfileids[1]=<id>...
```

- **一次最多 100 个 ID**。逐个抓网页页会被限流（「您最近作出的请求太多了」）
- 返回字段里这几个最有用：`title` / `time_created` / **`time_updated`** / `subscriptions` / `visibility` / `banned`
- **`result = 9` 表示该条目已删除 / 不可见** → 跳过重命名并在报告里写明原因
- `time_updated` 只在**两件都来自 `workshop\`** 时用来给「留新移旧」分胜负
  - ⚠️ **核心标准：未整理的（还在 `workshop\` 内的）永远按新算** ——
    `addons` 里的常驻件再新也赢不了刚从 `workshop\` 出来那件，不需要比日期

> 有些环境下 PowerShell 直连该接口会 TLS 失败。若如此，改用浏览器上下文里的 fetch（例如 agent 浏览器的 `fetch.browser`），
> 注意它返回的是**字符串**，要自己 `JSON.parse`。

## `.url` 快捷方式格式

最简单的三行版就够用：

```
[InternetShortcut]
URL=https://steamcommunity.com/sharedfiles/filedetails/?id=<id>
IconIndex=0
```

从浏览器拖拽生成的完整版（带 `[{000214A0-…}]` 头与 `Prop3=19,11`）也能用。**两者都能用，不要为了"统一格式"去改用户的文件。**

**手工件（文件名不是纯数字 ID）没有工坊 ID → 不建 `.url`。**

## 取消全部订阅

**为什么必须做**：L4D2 的工坊投递是把 `<id>.vpk` 直接放进 `left4dead2\addons\workshop\`。
整理时把 VPK 搬走后，只要**订阅还在**，下次启动游戏 Steam 就会把同样的 VPK 再下一遍，整理等于白做。
删 `workshop\` 目录、改只读都无效 —— 取消订阅是唯一的正解。

### 前置核对（两个独立来源，都要看）

1. **本地镜像**：`<Steam>\userdata\<accountid>\ugc\<appid>_subscriptions.vdf`
   - `<accountid>` 从 `userdata\` 下的数字目录取
   - 退订成功后该文件会缩到只剩 `appid` + `time_last_updated`（Steam 客户端自动同步，无需重启）
   - ⚠️ `time_last_updated` 可能是占位值 `"1"`，**不可靠**；只认有没有 `publishedfileid` 条目
2. **服务器端**：`https://steamcommunity.com/my/myworkshopfiles/?browsefilter=mysubscriptions&appid=<appid>`
   - **必须是 `/my/myworkshopfiles/`**（带 `/my/`）
   - ❌ `/workshop/browse/?appid=…&browsefilter=mysubscriptions` 的筛选**已失效**，会显示全量列表（几十万条），别被骗
   - ❌ 不带 `/my/` 的 `/myworkshopfiles/` 会 302 回首页
   - 首次访问有成人内容提示，需先点「查看社区中心」
   - 页面文案「正在显示第 1 - N 项，共 N 项条目」= 权威订阅数；清空后是「未找到符合 <用户名> 的文件。」

### 执行（一条 POST）

```js
// 先打开该游戏的订阅页，再在同一源下取 sessionid
const sid = await page.evaluate(() => window.g_sessionID);
const txt = await fetch.browser('https://steamcommunity.com/sharedfiles/unsubscribeall/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: `sessionid=${encodeURIComponent(sid)}&appid=<appid>&filetype=18`
});
// 返回 {"success":1}
```

- 页面源码里 `UnsubscribeAll()` 的 `appid` 是**写死的**，所以只清该游戏，不会波及其它游戏的订阅
  （页面上那个按钮的文案没写范围，光看界面判断不了，必须读源码）
- **不可逆**（Steam 原文「此操作无法撤销！」）。回退 = 重新订阅；
  addons 里每个 mod 都有 `.url` 可直达工坊页，所以基本可逆 ——
  但 `result=9` 的已删除条目和**手工件**没有 `.url`，退订后无处可回

### 逐项取消

物品页 `#SubscribeItemBtn` 走 `POST /sharedfiles/unsubscribe`，body `id=<fileid>&appid=<appid>&sessionid=<sid>`；
或页面上的 `UnsubscribeItem(id, appID)`（提交 `#PublishedFileUnsubscribe` 表单）。

### 授权与确认（⚠️ 默认每次都要问）

这是**账号级、不可逆**操作（Steam 原文「此操作无法撤销！」）。
**默认每次执行前都要停下来问用户一次**，问的时候必须说清三件事：

1. **退哪些** —— 列出 ID + 标题 + 总数（不要只说「3 个」）
2. **为什么要做** —— 不退订的话，下次启动游戏 Steam 会把刚搬走的 VPK 重新下一遍，整理白做
3. **不可逆 + 怎么回退** —— 回退 = 重新订阅；addons 里每个 mod 都留了 `.url` 可直达工坊页，
   但 `result=9` 的已删除条目与**手工件**没有 `.url`，退订后无处可回

**授权不跨会话**：只有用户**在当前这次会话**里明确说了「以后不用问」「直接退」之类的话，
本次才可以跳过询问。不要因为长期记忆或上一次会话授权过就默认免确认。

### 副作用（实测）

- ✅ **不会删 addons 里已整理的 mod**（执行前后逐个数过，数量完全一致）
- ✅ `workshop\` 空目录保留

## 常见目录布局

| 用途 | 路径 |
|---|---|
| Steam 根 | 常见 `C:\Program Files (x86)\Steam` 或用户自定义（如 `D:\Steam`） |
| 游戏目录 | `<Steam>\steamapps\common\Left 4 Dead 2\left4dead2\` |
| mod 库（最终落点） | `…\left4dead2\addons\` |
| 工坊暂存 | `…\left4dead2\addons\workshop\` |
| 订阅镜像 | `<Steam>\userdata\<accountid>\ugc\<appid>_subscriptions.vdf` |
