# Neo4j 集成与图可视化说明

## 存储原则

### "轻节点、重关系"架构

- **Neo4j**：存储节点标识（id + name）和关系数据
- **MongoDB**：存储完整的业务明细数据

## 数据模型

### 节点类型

1. **Activity（活动节点）**
   - `id`: 活动ID（与MongoDB _id一致）
   - `name`: 活动名称

2. **Resource（资源节点）**
   - `id`: 资源ID（与MongoDB _id一致）
   - `name`: 资源名称

3. **Personnel（人员节点）**
   - `id`: 人员ID（与MongoDB _id一致）
   - `name`: 人员名称

### 关系类型

1. **DEPENDS_ON（活动依赖关系）**
   - 方向：Activity → Activity
   - 属性：
     - `type`: 依赖类型（sequential/parallel/conditional）
     - `time_constraint`: 时间约束（分钟）
     - `status`: 依赖状态（active/inactive/pending）
     - `description`: 描述

2. **USES（资源使用关系）**
   - 方向：Activity → Resource
   - 属性：
     - `quantity`: 使用数量
     - `unit`: 单位
     - `stage`: 使用阶段

3. **ASSIGNS（人员分配关系）**
   - 方向：Activity → Personnel
   - 属性：
     - `role`: 角色（如'负责人'/'操作员'）

## 数据同步机制

### 自动同步

后端API在执行MongoDB操作时自动同步到Neo4j：

- **创建活动/资源/人员**：在Neo4j中创建对应节点
- **更新活动/资源/人员名称**：同步更新Neo4j节点
- **删除活动/资源/人员**：删除Neo4j节点及其所有关系

### 首次迁移

运行迁移脚本同步现有数据：

```bash
cd backend
python migrate_to_neo4j.py
```

## API端点

### 依赖关系管理
- `POST /api/dependencies` - 创建依赖关系
- `GET /api/dependencies` - 查询依赖关系
- `PUT /api/dependencies/{id}` - 更新依赖关系
- `DELETE /api/dependencies/{id}` - 删除依赖关系
- `GET /api/dependencies/graph/data` - 获取图数据（用于可视化）

### 资源使用关系管理
- `POST /api/resource-usage` - 创建资源使用关系
- `GET /api/resource-usage` - 查询资源使用关系
- `PUT /api/resource-usage/{id}` - 更新资源使用关系
- `DELETE /api/resource-usage/{id}` - 删除资源使用关系

### 人员分配关系管理
- `POST /api/personnel-assignment` - 创建人员分配关系
- `GET /api/personnel-assignment` - 查询人员分配关系
- `PUT /api/personnel-assignment/{id}` - 更新人员分配关系
- `DELETE /api/personnel-assignment/{id}` - 删除人员分配关系

## 图可视化规则

详见 `frontend/GRAPH_INTERACTION.md`

### 核心特性

1. **横向布局**：Activity横向排列，展示生产流程
2. **按需展开**：默认折叠资源和人员，右键展开/折叠
3. **左键详情**：点击活动节点查看完整信息
4. **实例化策略**：每个活动的资源和人员独立显示
5. **视觉优化**：不同关系类型用不同线型和颜色区分

