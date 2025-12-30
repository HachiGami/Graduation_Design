# 乳业生产运行全周期建模系统

## 技术栈

- 前端: Vue 3 + TypeScript + Element Plus + AG-Grid
- 后端: FastAPI + Python
- 数据库: MongoDB

## 安装依赖

### 后端
```bash
cd backend
pip install -r requirements.txt
```

### 前端
```bash
cd frontend
npm install
```

## 运行

### 启动MongoDB
```bash
mongod
```

### 启动后端
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 启动前端
```bash
cd frontend
npm run dev
```

访问: http://localhost:5173

## 初始化演示数据

后端启动后，访问: http://localhost:8000/api/demo/init

## 功能模块

1. 资源管理
2. 人员管理
3. 依赖关系定义
4. 生产活动管理
5. 数据面板展示

