# 安装依赖
npm install
# 构建
npm run build
# 构建镜像
docker build -t large-screen-front .

#docker run --name large-screen-front-container -d -p 8002:80 large-screen-front