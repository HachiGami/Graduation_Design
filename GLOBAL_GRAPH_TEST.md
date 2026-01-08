# 全局图+高亮定位功能 - 自测清单

## 功能概述
系统已改造为"全局图+流程高亮定位"模式：
- 后端提供全局图数据（默认返回所有domain/process_id的活动和关系）
- 前端默认加载并渲染全局图
- 流程选择器用于定位并高亮特定流程，而非过滤数据
- 支持清除高亮，恢复全局视图

## 后端改动

### 1. 新增全局图接口
**接口**: `GET /api/dependencies/graph/data`

**参数**:
- `scope`: 查询范围 (可选，默认`global`)
  - `global`: 返回全部数据
  - `domain`: 返回指定domain的所有process
  - `process`: 返回指定domain+process_id的数据
- `domain`: 流程域 (scope=domain或process时必填)
- `process_id`: 流程实例ID (scope=process时必填)
- `include_cross`: 是否包含跨流程关联 (可选，默认false)

**返回结构**:
```json
{
  "nodes": [
    {
      "id": "活动ID",
      "name": "活动名称",
      "category": "Activity",
      "type": "活动类型",
      "status": "状态",
      "domain": "production",
      "process_id": "P001",
      "description": "描述",
      "estimated_duration": 60
    }
  ],
  "edges": [
    {
      "source": "源活动ID",
      "target": "目标活动ID",
      "relation": "DEPENDS_ON",
      "type": "sequential",
      "domain": "production",
      "process_id": "P001"
    }
  ],
  "resource_nodes": [...],
  "resource_edges": [...],
  "personnel_nodes": [...],
  "personnel_edges": [...]
}
```

### 2. Cypher查询逻辑
- **全局模式**: 不加WHERE条件，返回所有节点和边
- **域级模式**: WHERE s.domain = $domain OR t.domain = $domain
- **流程级模式**: WHERE r.domain = $domain AND r.process_id = $process_id

## 前端改动

### 1. 数据加载逻辑
- **页面加载**: 调用`loadGlobalGraphData()` - 一次性拉取全局图
- **流程切换**: 不重新请求图数据，仅调用`applyProcessHighlight()`应用高亮
- **活动列表**: 仍按domain/process_id过滤加载（用于表格显示）

### 2. 高亮状态管理
```typescript
const highlightActive = ref(false)
const highlightSet = ref<{nodeIds: Set<string>, edgeIds: Set<string>}>({
  nodeIds: new Set(),
  edgeIds: new Set()
})
```

### 3. 高亮渲染规则
**高亮节点**:
- 边框加粗 (3px)
- 边框颜色: 橙色 (#ff6b00)
- 字体加粗
- 不透明度: 1

**非高亮节点**:
- 不透明度: 0.3 (灰化)

**高亮边**:
- 颜色: 橙色 (#ff6b00)
- 线宽: 4px
- 不透明度: 1

**非高亮边**:
- 不透明度: 0.2 (灰化)

### 4. ProcessSelector组件
**按钮**:
- "定位并高亮": 触发`@change`事件，应用高亮
- "清除高亮": 触发`@clear`事件，恢复全局视图

### 5. 活动详情增强
点击节点查看详情时，显示:
- 流程域 (domain)
- 流程ID (process_id)
- 活动名称、类型、状态等

## 自测步骤 (必须全部通过)

### ✅ 测试1: 默认加载全局图
**步骤**:
1. 启动后端服务
2. 启动前端服务
3. 打开浏览器访问依赖管理页面

**预期结果**:
- 页面加载完成后，图表显示所有流程的活动节点和边
- 至少能看到 production/P001, transport/T001, sales/S001, quality/Q001 的节点
- 所有节点和边均为正常颜色（无灰化）
- 网络请求中只有一次 `/api/dependencies/graph/data?scope=global`

### ✅ 测试2: 定位并高亮 production/P001
**步骤**:
1. 在流程选择器中选择"生产 - P001"
2. 点击"定位并高亮"按钮

**预期结果**:
- production/P001 的所有节点边框变为橙色加粗
- production/P001 的所有边变为橙色加粗
- 其他流程的节点和边被灰化（opacity降低）
- 图表自动聚焦到 production/P001 区域
- 显示成功消息："已定位到 production/P001"
- **不应有新的网络请求**

### ✅ 测试3: 切换高亮到 transport/T001
**步骤**:
1. 在流程选择器中选择"运输 - T001"
2. 点击"定位并高亮"按钮

**预期结果**:
- 高亮切换到 transport/T001
- production/P001 的高亮消失，被灰化
- transport/T001 的节点和边被高亮
- 图表自动聚焦到 transport/T001 区域
- **不应有新的网络请求**

### ✅ 测试4: 清除高亮恢复全局
**步骤**:
1. 点击"清除高亮"按钮

**预期结果**:
- 所有节点和边恢复正常颜色
- 没有任何灰化效果
- 图表恢复全局视图（fitView到所有节点）
- 显示消息："已清除高亮"

### ✅ 测试5: 刷新页面保持状态
**步骤**:
1. 选择 sales/S001 并点击"定位并高亮"
2. 刷新浏览器页面

**预期结果**:
- 页面重新加载后，URL中包含 `?domain=sales&process_id=S001`
- 全局图正确加载
- sales/S001 自动被高亮显示
- 其他流程被灰化

### ✅ 测试6: 节点详情显示domain/process_id
**步骤**:
1. 左键点击任意活动节点

**预期结果**:
- 右侧抽屉打开，显示活动详情
- 详情中包含"流程域"和"流程ID"字段
- 字段值正确对应该节点的domain和process_id

### ✅ 测试7: 活动列表与高亮联动
**步骤**:
1. 选择 production/P001 并高亮
2. 查看下方的活动列表

**预期结果**:
- 活动列表只显示 production/P001 的活动
- 列表中的活动与图中高亮的节点一致

### ✅ 测试8: 跨流程边可见性
**步骤**:
1. 清除高亮，查看全局图
2. 寻找跨流程的依赖边（如 production入库 -> transport出库装车）

**预期结果**:
- 在全局视图下，跨流程边可见
- 边连接不同domain/process_id的节点
- 边的颜色与普通边一致

### ✅ 测试9: 高亮模式下跨流程边处理
**步骤**:
1. 高亮 production/P001
2. 观察是否有边连接到其他流程

**预期结果**:
- 如果有跨流程边（源或目标在P001），该边应该：
  - 如果边的domain/process_id匹配P001，则高亮
  - 否则被灰化
- 跨流程边的另一端节点被灰化

### ✅ 测试10: 多次切换高亮无异常
**步骤**:
1. 依次高亮: production/P001 -> transport/T001 -> sales/S001 -> quality/Q001
2. 每次切换后观察图表

**预期结果**:
- 每次切换都能正确高亮目标流程
- 没有残留的高亮效果
- 图表聚焦正确
- 没有控制台错误

## 验收标准

所有10个测试必须通过，且满足以下条件：

1. ✅ 页面默认加载全局图（所有流程可见）
2. ✅ 流程选择器只触发前端高亮，不触发后端请求
3. ✅ 高亮模式下目标流程突出显示，其他流程灰化但仍可见
4. ✅ 清除高亮后恢复全局正常视图
5. ✅ 节点详情包含domain和process_id信息
6. ✅ 刷新页面后状态保持
7. ✅ 无控制台错误
8. ✅ 网络请求合理（只在初始加载时请求全局图）

## 关键代码位置

### 后端
- `backend/app/routers/dependencies.py`: `get_graph_data()` 函数
  - 支持 scope 参数 (global/domain/process)
  - 节点和边包含 domain/process_id

### 前端
- `frontend/src/views/DependencyManagement.vue`:
  - `loadGlobalGraphData()`: 加载全局图
  - `applyProcessHighlight()`: 应用高亮
  - `clearHighlight()`: 清除高亮
  - `highlightActive` 和 `highlightSet` 状态管理

- `frontend/src/components/DependencyGraph.vue`:
  - 节点样式: 根据 `highlightActive` 和 `highlightSet` 动态设置 opacity 和 borderColor
  - 边样式: 根据高亮状态设置颜色和线宽

- `frontend/src/components/ProcessSelector.vue`:
  - "定位并高亮" 按钮: 触发 `@change` 事件
  - "清除高亮" 按钮: 触发 `@clear` 事件

- `frontend/src/api/dependency.ts`:
  - `getGraphData()`: 支持 scope 参数

## 注意事项

1. **不要再按 domain/process_id 去过滤后端返回的数据**
2. **页面必须默认加载全局大图**
3. **选择器只做前端定位+高亮，并提供清除取消高亮**
4. **高亮是"灰化其他"而非"隐藏其他"**
5. **所有节点和边必须包含 domain 和 process_id 属性**





