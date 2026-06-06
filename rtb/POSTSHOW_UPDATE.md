# Postshow 接口更新说明

## 📋 更新时间
2025-12-28

## 🔄 更新内容

### 接口路径
`/dev/rtb/kwaiadsinfo/postshow`

### 修改前
- **支持方法**: 仅 POST
- **参数**: `@RequestBody String requestBody`

### 修改后
- **支持方法**: GET 和 POST
- **参数**:
  - POST: `@RequestBody(required = false) String requestBody`
  - GET: `@RequestParam(required = false) String data`

## 📝 代码变更

### 原始代码
```java
@PostMapping("/kwaiadsinfo/postshow")
public ResponseEntity<Map<String, Object>> postShowData(@RequestBody String requestBody) {
    log.info("收到 kwaiadsinfo postshow 请求数据: {}", requestBody);

    // 封装标准响应格式
    Map<String, Object> response = new HashMap<>();
    response.put("code", 200);
    response.put("message", "OK");
    response.put("data", new HashMap<>());

    return new ResponseEntity<>(response, HttpStatus.OK);
}
```

### 更新后代码
```java
@RequestMapping(value = "/kwaiadsinfo/postshow", method = {RequestMethod.GET, RequestMethod.POST})
public ResponseEntity<Map<String, Object>> postShowData(
        @RequestBody(required = false) String requestBody,
        @RequestParam(required = false) String data) {

    // 优先使用 POST body，如果没有则使用 GET 参数
    String actualData = requestBody != null ? requestBody : data;

    if (actualData != null && !actualData.isEmpty()) {
        log.info("收到 kwaiadsinfo postshow 请求数据: {}", actualData);
    } else {
        log.warn("收到 kwaiadsinfo postshow 请求，但没有数据");
    }

    // 封装标准响应格式
    Map<String, Object> response = new HashMap<>();
    response.put("code", 200);
    response.put("message", "OK");
    response.put("data", new HashMap<>());

    return new ResponseEntity<>(response, HttpStatus.OK);
}
```

## 🎯 使用方式

### 1. POST 方式（原有方式，保持兼容）

**请求示例:**
```bash
curl -X POST http://localhost:7721/dev/rtb/kwaiadsinfo/postshow \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'data=%7B%22data%22%3A%7B%22urls%22%3A%5B%22url1%22%5D%7D%7D'
```

**Java 代码:**
```java
// 数据在 requestBody 中
String requestBody = "data=%7B%22data%22%3A%7B%22urls%22%3A%5B%22url1%22%5D%7D%7D";
```

### 2. GET 方式（新增）

**请求示例:**
```bash
curl -X GET "http://localhost:7721/dev/rtb/kwaiadsinfo/postshow?data=%7B%22data%22%3A%7B%22urls%22%3A%5B%22url1%22%5D%7D%7D"
```

**浏览器访问:**
```
http://localhost:7721/dev/rtb/kwaiadsinfo/postshow?data=%7B%22data%22%3A%7B%22urls%22%3A%5B%22url1%22%5D%7D%7D
```

**Java 代码:**
```java
// 数据在 data 参数中
String data = "%7B%22data%22%3A%7B%22urls%22%3A%5B%22url1%22%5D%7D%7D";
```

## 📊 数据格式

### URL 编码的 JSON 数据

**原始 JSON:**
```json
{
  "data": {
    "urls": ["url1", "url2"]
  }
}
```

**URL 编码后:**
```
data=%7B%22data%22%3A%7B%22urls%22%3A%5B%22url1%22%2C%22url2%22%5D%7D%7D
```

## 🔍 处理逻辑

### 数据获取优先级
1. **优先**: POST 请求的 `requestBody`
2. **其次**: GET 请求的 `data` 参数
3. **兜底**: 如果都没有，记录警告日志

### 日志输出
```java
// 有数据
log.info("收到 kwaiadsinfo postshow 请求数据: {}", actualData);

// 无数据
log.warn("收到 kwaiadsinfo postshow 请求，但没有数据");
```

## ✅ 特性

### 1. 向后兼容
- ✅ 原有的 POST 请求完全兼容
- ✅ 无需修改客户端代码

### 2. 灵活性
- ✅ 支持 GET 请求（方便浏览器测试）
- ✅ 支持 POST 请求（原有方式）
- ✅ 参数都是可选的（`required = false`）

### 3. 容错性
- ✅ 如果没有数据，不会报错，只记录警告
- ✅ 仍然返回成功响应（200）

## 🧪 测试方式

### 测试 POST 请求
```bash
# 测试1: 标准 POST 请求
curl -X POST http://localhost:7721/dev/rtb/kwaiadsinfo/postshow \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'data=%7B%22test%22%3A%22value%22%7D'

# 测试2: 空 POST 请求
curl -X POST http://localhost:7721/dev/rtb/kwaiadsinfo/postshow
```

### 测试 GET 请求
```bash
# 测试3: 标准 GET 请求
curl -X GET "http://localhost:7721/dev/rtb/kwaiadsinfo/postshow?data=%7B%22test%22%3A%22value%22%7D"

# 测试4: 空 GET 请求
curl -X GET "http://localhost:7721/dev/rtb/kwaiadsinfo/postshow"

# 测试5: 浏览器访问（复制到浏览器）
http://localhost:7721/dev/rtb/kwaiadsinfo/postshow?data=%7B%22data%22%3A%7B%22urls%22%3A%5B%22test%22%5D%7D%7D
```

### 预期响应
所有请求都应该返回：
```json
{
  "code": 200,
  "message": "OK",
  "data": {}
}
```

### 日志检查
```bash
# 查看应用日志
tail -f logs/springboot-scaffold.log

# 有数据的请求应该看到
2025-12-28 10:00:00 INFO 收到 kwaiadsinfo postshow 请求数据: data=%7B...

# 无数据的请求应该看到
2025-12-28 10:00:00 WARN 收到 kwaiadsinfo postshow 请求，但没有数据
```

## 📦 部署步骤

### 1. 编译项目
```bash
cd /Users/luoxun/dev/ads/server/ads/rtb
mvn clean package -DskipTests
```

### 2. 重启应用
```bash
# 停止当前应用
kill $(ps aux | grep 'springboot-scaffold' | grep -v grep | awk '{print $2}')

# 启动新版本
java -jar target/springboot-scaffold-0.0.1-SNAPSHOT.jar
```

### 3. 验证更新
```bash
# 测试 GET 方法
curl -X GET "http://localhost:7721/dev/rtb/kwaiadsinfo/postshow?data=test"

# 检查响应
# 应该返回: {"code":200,"message":"OK","data":{}}
```

## 🔧 配置说明

### 无需额外配置
- ✅ 不需要修改 `application.yml`
- ✅ 不需要添加依赖
- ✅ 不需要修改其他代码

### Spring Boot 自动处理
- ✅ `@RequestMapping` 自动支持多种 HTTP 方法
- ✅ `@RequestBody(required = false)` 支持可选参数
- ✅ `@RequestParam(required = false)` 支持可选参数

## ⚠️ 注意事项

### 1. 数据编码
GET 和 POST 的数据都应该是 URL 编码的：
```
原始: {"data":{"urls":["test"]}}
编码: %7B%22data%22%3A%7B%22urls%22%3A%5B%22test%22%5D%7D%7D
```

### 2. Content-Type
- POST 请求应使用: `application/x-www-form-urlencoded`
- GET 请求无需设置（在 URL 参数中）

### 3. 参数名称
- POST body: 整个 body 作为 `requestBody`
- GET 参数: 必须使用 `data` 作为参数名

### 4. 日志级别
如果不想看到无数据的警告日志，可以调整日志级别：
```yaml
logging:
  level:
    com.leeyom.scaffold.api.DevController: ERROR
```

## 📈 使用场景

### GET 方式适用于
- ✅ 浏览器测试
- ✅ 简单的日志测试
- ✅ 调试和排查问题
- ✅ 数据量较小的情况

### POST 方式适用于
- ✅ 生产环境
- ✅ 大量数据传输
- ✅ 客户端应用
- ✅ 原有代码兼容

## ✅ 总结

### 主要改进
1. ✅ 同时支持 GET 和 POST 方法
2. ✅ 参数灵活可选
3. ✅ 完全向后兼容
4. ✅ 容错性强

### 影响范围
- 📁 修改文件: `DevController.java`
- 🔧 方法: `postShowData()`
- 🌐 接口: `/dev/rtb/kwaiadsinfo/postshow`

### 测试状态
- ⏳ 待测试: 编译和运行
- ⏳ 待测试: GET 请求
- ⏳ 待测试: POST 请求
- ⏳ 待测试: 日志输出

---

**最后更新:** 2025-12-28
**修改人:** Claude
**版本:** v1.1 - 支持 GET/POST
