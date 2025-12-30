# 安装指南

## 1. 安装Python依赖

```bash
cd backend
pip install -r requirements.txt
```

## 2. 安装Node.js依赖

```bash
cd frontend
npm install
```

## 3. 启动MongoDB

确保MongoDB正在运行：

```bash
mongod
```

或使用Docker：

```bash
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

## 4. 启动后端服务

Windows:
```bash
cd backend
start.bat
```

Linux/Mac:
```bash
cd backend
chmod +x start.sh
./start.sh
```

或手动启动：
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

后端将运行在: http://localhost:8000

## 5. 启动前端服务

Windows:
```bash
cd frontend
start.bat
```

Linux/Mac:
```bash
cd frontend
chmod +x start.sh
./start.sh
```

或手动启动：
```bash
cd frontend
npm run dev
```

前端将运行在: http://localhost:5173

## 6. 初始化演示数据

浏览器访问或使用curl：

```bash
curl -X POST http://localhost:8000/api/demo/init
```

或运行测试脚本：

```bash
cd backend
python test_api.py
```

## 7. 访问系统

打开浏览器访问: http://localhost:5173

## 常见问题

### MongoDB连接失败
确保MongoDB已启动，检查配置文件中的连接URL

### 端口冲突
修改backend/.env或frontend/vite.config.ts中的端口配置

### 依赖安装失败
使用国内镜像源：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
npm install --registry=https://registry.npmmirror.com
```

