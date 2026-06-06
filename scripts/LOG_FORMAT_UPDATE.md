# 日志格式更新说明

## 📋 更新时间
2025-12-28

## 🔄 日志格式变化

### 旧格式
```json
{
  "type": 1,
  "url": "KwaiNetwork/sdk/getSdkAd",
  "responseData": "{\"data\":{\"knAdInfo\":[{\"knPackInfo\":{\"riaidBase64Str\":\"base64编码的字符串\"}}]}}"
}
```

处理逻辑：
1. 检查 type 和 url 字段
2. 解析 responseData JSON 字符串
3. 提取 knAdInfo[0].knPackInfo.riaidBase64Str
4. Base64 解码
5. 使用正则表达式提取 URL
6. 过滤和验证 URL

### 新格式
```json
{
  "data": {
    "urls": [
      "https://www.adsnebula.com/log/common/click?pixel_id=xxx&click_id=yyy",
      "https://example.com/track?pixel_id=aaa&click_id=bbb"
    ]
  }
}
```

处理逻辑：
1. 直接从 data.urls 数组获取 URL
2. 过滤和验证 URL
3. 应用比例控制
4. 检查 pixel_id 匹配

---

## ✅ 更新的代码文件

### 1. extract_log_incremental.py

#### 新增函数

**`extract_urls_from_data(json_data: Dict[str, Any]) -> list`**
```python
def extract_urls_from_data(json_data: Dict[str, Any]) -> list:
    """
    从新格式的 JSON 数据中提取 URLs

    新格式：
    {
        "data": {
            "urls": ["url1", "url2", "url3"]
        }
    }
    """
    try:
        if 'data' in json_data and isinstance(json_data['data'], dict):
            urls = json_data['data'].get('urls', [])
            if isinstance(urls, list):
                return urls
        return []
    except Exception as e:
        print(f"警告: 提取URLs失败: {e}", file=sys.stderr)
        return []
```

#### 简化的主处理逻辑

**旧逻辑（已移除）：**
- 检查 `should_filter_json()` - type 和 url 字段验证
- 调用 `extract_and_decode_ad_info()` - Base64 解码
- 使用正则表达式提取 URL
- 检查 click_id 和 play store

**新逻辑：**
```python
# 解析 JSON 数据
json_data = parse_url_encoded_data(request_body_str)
if json_data is None:
    continue

# 从新格式中提取 URLs 数组
urls = extract_urls_from_data(json_data)
if not urls:
    continue

# 处理每个 URL
for url in urls:
    # 过滤域名
    # 清理URL
    # 检查必需参数 (click_id, pixel_id)
    # 应用比例控制
    # 检查 pixel_id 匹配
```

---

## 📊 处理流程对比

### 旧流程
```
日志行
  ↓
提取 requestBody
  ↓
URL 解码 + JSON 解析
  ↓
检查 type=1 和 url 包含 "KwaiNetwork/sdk/getSdkAd"
  ↓
检查 responseData.data.knAdInfo 不为空
  ↓
提取 knAdInfo[0].knPackInfo.riaidBase64Str
  ↓
Base64 解码
  ↓
检查包含 click_id 或不包含 play.google.com
  ↓
正则提取所有 https:// 开头的 URL
  ↓
过滤域名 + 清理 + 验证参数
  ↓
应用比例控制
  ↓
检查 pixel_id 匹配
  ↓
输出到文件
```

### 新流程（简化）
```
日志行
  ↓
提取 requestBody
  ↓
URL 解码 + JSON 解析
  ↓
直接从 data.urls 获取 URL 数组 ← 简化！
  ↓
遍历 URL 数组
  ↓
过滤域名 + 清理 + 验证参数
  ↓
应用比例控制
  ↓
检查 pixel_id 匹配
  ↓
输出到文件
```

**简化的步骤：**
- ❌ 不再需要检查 type 和 url 字段
- ❌ 不再需要检查 knAdInfo
- ❌ 不再需要 Base64 解码
- ❌ 不再需要正则表达式提取 URL
- ✅ 直接从 data.urls 获取

---

## 🎯 保持不变的部分

### 1. URL 过滤规则
- 排除域名：`ad.ap4r.com`, `s16.kwai.net`, `adx.opera.com`, `liftoff-creatives.io`
- 必需参数：`click_id`, `pixel_id`

### 2. 比例控制
- 总体比例：4% (或配置的 total_ratio)
- 使用 MD5 哈希确保确定性

### 3. pixel_id 匹配
- 只输出 pixelid_token.txt 中存在的 pixel_id

### 4. 后续处理
- `url_frequency_controller.py` - 无需修改
- `convert_enhanced.py` - 无需修改
- `orchestrator.py` - 无需修改

---

## 📝 统计信息

统计指标含义保持不变：

| 指标 | 含义 |
|------|------|
| total_log_count | 匹配到 requestBody 的日志行数 |
| filtered_count | 成功解析 JSON 的行数 |
| url_count | 提取的 URL 总数 |
| url_selected_by_ratio | 通过比例筛选的 URL |
| skipped_by_ratio | 因比例限制跳过的 URL |
| matched_url_count | 匹配 pixel_id 的 URL |

---

## 🧪 测试建议

### 1. 测试新格式解析

创建测试日志：
```
2025-12-28 10:00:00 INFO 收到 kwaiadsinfo postshow 请求数据: data=%7B%22data%22%3A%7B%22urls%22%3A%5B%22https%3A%2F%2Fwww.adsnebula.com%2Flog%2Fcommon%2Fclick%3Fpixel_id%3D123%26click_id%3Dabc%22%5D%7D%7D
```

解码后：
```json
{
  "data": {
    "urls": ["https://www.adsnebula.com/log/common/click?pixel_id=123&click_id=abc"]
  }
}
```

### 2. 运行测试

```bash
# 测试 extract
python3 extract_log_incremental.py \
  --log-file test.log \
  --output test_output.txt \
  --ratio 0.04 \
  --pixelid-token-file pixelid_token.txt

# 检查输出
cat test_output.txt
```

### 3. 验证统计信息

运行后检查：
- ✅ filtered_count 应该等于成功解析的 JSON 行数
- ✅ url_count 应该等于所有 URL 的总数
- ✅ url_selected_by_ratio ≈ url_count × 4%
- ✅ matched_url_count ≤ url_selected_by_ratio

---

## ⚠️ 兼容性说明

### 向后兼容
由于日志格式完全改变，此更新**不兼容**旧格式的日志。

如果需要同时支持新旧格式：
1. 可以在 `extract_urls_from_data()` 中添加格式检测
2. 保留旧的 `extract_and_decode_ad_info()` 函数
3. 根据数据结构自动选择处理方式

### 建议方案
- 方案A：完全切换到新格式（推荐）
- 方案B：保留旧代码，添加格式检测（复杂）

---

## 📦 部署步骤

### 1. 备份
```bash
cp extract_log_incremental.py extract_log_incremental.py.bak
```

### 2. 更新脚本
已更新：`extract_log_incremental.py`

### 3. 测试
```bash
# 使用真实日志测试
python3 extract_log_incremental.py \
  --log-file /data/disk0/home/luoxun/logs/springboot-scaffold/info.prod0320_2025-12-28.part_0.log \
  --output test_clicks_temp.txt \
  --ratio 0.04 \
  --pixelid-token-file pixelid_token.txt
```

### 4. 检查输出
```bash
# 检查提取的 URL
head -5 test_clicks_temp.txt

# 验证 URL 格式
grep -E "pixel_id|click_id" test_clicks_temp.txt | wc -l
```

### 5. 完整流程测试
```bash
# 运行完整编排
python3 orchestrator.py --config orchestrator_config.json
```

---

## 🔍 故障排查

### 问题1：没有提取到 URL

**检查：**
1. 日志格式是否正确（data.urls 结构）
2. URLs 数组是否为空
3. URL 是否包含必需的参数

**解决：**
```bash
# 查看原始日志
grep "收到 kwaiadsinfo postshow 请求数据" log_file.log | head -1

# 手动解析测试
python3 -c "
import urllib.parse
import json
data = 'data=%7B%22data%22...'  # 从日志中复制
decoded = urllib.parse.unquote(data.split('data=')[1])
print(json.dumps(json.loads(decoded), indent=2))
"
```

### 问题2：统计信息异常

**检查：**
- filtered_count 是否为 0（JSON 解析失败）
- url_count 是否为 0（没有提取到 URL）

**解决：**
添加调试日志，查看中间步骤的数据。

---

## ✅ 变更总结

### 简化的部分
- ✅ 移除了复杂的 Base64 解码逻辑
- ✅ 移除了 OpenRTB 响应解析逻辑
- ✅ 移除了正则表达式 URL 提取
- ✅ 移除了 type/url 字段检查

### 新增的部分
- ✅ `extract_urls_from_data()` 函数
- ✅ 直接从 data.urls 数组获取 URL

### 保持不变的部分
- ✅ 比例控制逻辑（4%）
- ✅ pixel_id 匹配逻辑
- ✅ URL 过滤规则
- ✅ 统计信息输出
- ✅ 后续处理流程（frequency_control, convert）

---

**最后更新：** 2025-12-28
**更新类型：** 日志格式适配
**版本：** v3.0 - 简化版
