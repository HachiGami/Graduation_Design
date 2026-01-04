# 快速验收对照表

## 📋 验收标准逐条检查

### A. 结构不变

#### ✅ A1. 主干拉直（误差 ≤1px）
**如何验证**:
```javascript
window.__debugBackboneLayout = true
// 刷新页面，查看控制台输出
// 主干节点的 y 坐标应该完全一致
```

**通过标准**: 
- 主干节点 `backbone=true` 的 y 值都相同
- 视觉上主干为一条水平直线

**实现位置**: 第 241 行（设置主干 y=y0）

---

#### ✅ A2. Lane 归属不变
**如何验证**:
- 多次刷新页面
- 同一节点始终在同一侧（上方或下方）
- 同一泳道（laneIndex 不变）

**通过标准**:
- 语义规则节点（检验/订单）始终在对应方向
- 其他节点按 rootIndex 奇偶规则固定

**实现位置**: 第 407-467 行（`assignLanes()`）

---

#### ✅ A3. 确定性可复现
**如何验证**:
```javascript
// 刷新 5 次，截图对比
// 或查看控制台输出的坐标是否每次一致
```

**通过标准**:
- 同一数据，5 次刷新坐标完全一致
- 高亮/取消高亮，坐标不变

**实现位置**: 第 292-306 行（缓存机制）

---

### B. 去重叠硬指标

#### ✅ B1. Label-aware 碰撞检测
**如何验证**:
```javascript
window.__debugBackboneLayout = true
// 查看控制台输出：
// [Overlap Detection] Before: X
// [Overlap Detection] After: 0
```

**通过标准**:
- 使用真实渲染参数（Activity r=25, Resource r=17.5, labelW=100）
- 包围盒包含节点和 label

**实现位置**: 第 552-583 行（`computeCollisionRect()`）

---

#### ✅ B2. 优先局部扩大 laneGap
**如何验证**:
```javascript
// 查看控制台输出：
// [Process P001] Expanding gap above/below, lane=X, extra=Y
```

**通过标准**:
- 主干（lane=0）固定不动
- 上方 lanes 向上推，下方 lanes 向下推
- 局部扩张（不是全图统一）

**实现位置**: 第 634-717 行（`expandLaneGapsPerProcess()`）

---

#### ✅ B3. 同 lane 内小幅 jitter ≤20px
**如何验证**:
- 若 T2 后仍有重叠，T3 会微调
- 调整幅度很小，不破坏规整性

**通过标准**:
- jitterMax = 20px
- 只处理相邻节点小重叠
- 保持列内排序不变

**实现位置**: 第 733-766 行（`smallJitterInLaneIfNeeded()`）

---

#### ✅ B4. X 方向兜底
**如何验证**:
- 通常不触发（T2+T3 已足够）
- 若触发，最大追加 120px

**通过标准**:
- 仅处理 X 主导的重叠（overlapW > overlapH）
- 慎用，不影响主要布局

**实现位置**: 第 770-801 行（`expandRankSepsIfNeeded()`）

---

#### ✅ B5. overlapCount === 0 ⭐
**如何验证**:
```javascript
window.__debugBackboneLayout = true
// 必须看到以下输出：
// [Overlap Detection] After: 0 (before: X)
// ✅ No overlaps detected!
```

**通过标准**:
- `overlapCountAfter` 必须为 0
- 若 > 0，控制台显示 `⚠️ Still have X overlaps`

**实现位置**: 第 803-810 行（最终验证输出）

---

#### ✅ B6. 不使用 hideOverlap
**如何验证**:
- 视觉检查：所有 label 都可见
- 代码检查：无隐藏 label 的逻辑

**通过标准**:
- 真实调整坐标，不隐藏元素

**实现位置**: 无隐藏代码（真实去重叠）

---

## 🔍 快速验收流程（5 分钟）

### Step 1: 开启调试 (10 秒)
```javascript
// 浏览器控制台输入
window.__debugBackboneLayout = true
```

### Step 2: 触发布局 (5 秒)
点击页面右上角"重置视图"按钮

### Step 3: 检查控制台 (30 秒)
```
期望输出：
[Process P001] Backbone (X nodes): [...]
[Process P001] Node positions: ...
[Overlap Detection] Before: X
[Process P001] Expanding gap below, lane=1, extra=Y  ← 可能有多条
[Overlap Detection] After: 0 (before: X)  ← 必须为 0
✅ No overlaps detected!  ← 必须出现
```

### Step 4: 视觉检查 (1 分钟)
1. **主干**: 水平直线 ✅
2. **Label**: 所有可见，无重叠 ✅
3. **节点**: 无重叠 ✅

### Step 5: 稳定性检查 (2 分钟)
1. 刷新 5 次，坐标一致 ✅
2. 高亮节点，坐标不变 ✅

### Step 6: 参数检查 (1 分钟)
查看 `DependencyGraph.vue`:
- 第 559 行: `r = 25 / 17.5` ✅
- 第 562 行: `labelW = 100` ✅
- 第 649 行: `minLaneSeparation = 24` ✅
- 第 736 行: `jitterMax = 20` ✅

---

## ⚠️ 失败情况处理

### 情况 1: `overlapCountAfter > 0`

**原因**: 参数不够宽松

**解决**:
1. 增大 `minLaneSeparation`（24 → 32）
2. 增大 `labelMargin`（6 → 8）
3. 增大 `padding`（8 → 10）

### 情况 2: 主干不是直线

**原因**: 主干参与了推移

**解决**:
检查第 649 行 `expandLaneGapsPerProcess()`，确认主干（lane=0）不在推移逻辑中

### 情况 3: 刷新后布局变化

**原因**: 不确定性

**解决**:
1. 检查排序是否使用 `id` tie-breaker
2. 检查处理顺序是否固定
3. 确认无随机因素

### 情况 4: 布局不规整

**原因**: jitter 过大

**解决**:
减小 `jitterMax`（20 → 15 → 10）

---

## 📊 验收记录表

| 检查项 | 状态 | 备注 |
|--------|------|------|
| A1. 主干拉直 | ⬜ 通过 / ⬜ 未通过 | 主干 y 坐标: _____ |
| A2. Lane 归属不变 | ⬜ 通过 / ⬜ 未通过 | 刷新 5 次一致: ⬜ 是 / ⬜ 否 |
| A3. 确定性可复现 | ⬜ 通过 / ⬜ 未通过 | 高亮不重算: ⬜ 是 / ⬜ 否 |
| B1. Label-aware 检测 | ⬜ 通过 / ⬜ 未通过 | 参数正确: ⬜ 是 / ⬜ 否 |
| B2. 局部扩大 laneGap | ⬜ 通过 / ⬜ 未通过 | 主干固定: ⬜ 是 / ⬜ 否 |
| B3. 同 lane 内微调 | ⬜ 通过 / ⬜ 未通过 | jitterMax ≤ 20: ⬜ 是 / ⬜ 否 |
| B4. X 方向兜底 | ⬜ 通过 / ⬜ 未通过 | 极少触发: ⬜ 是 / ⬜ 否 |
| **B5. overlapCount === 0** | **⬜ 通过 / ⬜ 未通过** | **After: _____** |
| B6. 不隐藏 label | ⬜ 通过 / ⬜ 未通过 | 所有 label 可见: ⬜ 是 / ⬜ 否 |

---

## ✅ 最终验收签字

**验收人**: _________________  
**验收日期**: _________________  
**验收结果**: ⬜ 通过 / ⬜ 需修改  
**备注**: ___________________________________________

---

## 📞 问题反馈

若验收未通过，请提供：
1. 控制台完整输出（截图）
2. 页面截图（标注重叠位置）
3. 刷新前后对比（若不一致）
4. 参数配置（第 559/562/649/736 行）

**联系方式**: 在项目 issue 中提交，标题："去重叠验收未通过 - [具体问题]"


