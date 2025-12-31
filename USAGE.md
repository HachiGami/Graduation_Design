# 使用说明

## 系统功能

### 1. 数据面板
- 查看所有资源分配情况
- 查看人力使用状况
- 查看生产活动状态
- 查看依赖关系
- 支持排序、筛选、分页

### 2. 资源管理
- 添加生产资源（原材料、设备、包装材料等）
- 编辑资源信息
- 删除资源
- 查看资源状态

### 3. 人员管理
- 添加人员信息
- 管理人员技能
- 分配工作任务
- 查看人员状态

### 4. 依赖关系定义
- 定义生产环节之间的依赖
- 设置依赖类型（顺序/并行/条件）
- 配置时间约束
- 添加条件描述

### 5. 生产活动管理
- 创建生产活动
- 定义SOP流程步骤
- 关联所需资源和人员
- 跟踪活动状态

## 操作流程

### 添加资源
1. 点击"资源管理"菜单
2. 点击"添加资源"按钮
3. 填写资源信息
4. 保存

### 添加人员
1. 点击"人员管理"菜单
2. 点击"添加人员"按钮
3. 填写人员信息和技能
4. 保存

### 定义依赖关系
1. 点击"依赖关系"菜单
2. 点击"添加依赖"按钮
3. 选择前置和后置环节
4. 设置依赖类型和时间约束
5. 保存

### 创建生产活动
1. 点击"生产活动"菜单
2. 点击"添加活动"按钮
3. 填写活动基本信息
4. 添加SOP流程步骤
5. 保存

## API接口

### 资源管理
- GET /api/resources - 获取所有资源
- POST /api/resources - 创建资源
- PUT /api/resources/{id} - 更新资源
- DELETE /api/resources/{id} - 删除资源

### 人员管理
- GET /api/personnel - 获取所有人员
- POST /api/personnel - 创建人员
- PUT /api/personnel/{id} - 更新人员
- DELETE /api/personnel/{id} - 删除人员

### 依赖关系
- GET /api/dependencies - 获取所有依赖
- POST /api/dependencies - 创建依赖
- PUT /api/dependencies/{id} - 更新依赖
- DELETE /api/dependencies/{id} - 删除依赖

### 生产活动
- GET /api/activities - 获取所有活动
- POST /api/activities - 创建活动
- PUT /api/activities/{id} - 更新活动
- DELETE /api/activities/{id} - 删除活动

### 演示数据
- POST /api/demo/init - 初始化演示数据




