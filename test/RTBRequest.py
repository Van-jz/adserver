# 构建RTB 2.5请求的函数
def get_1_request(request_id, token):
    TagID = "800010002"
    AppID = "8000"

    request_payload = {
        "id": request_id,  # 唯一的请求ID
        "at": 1,  # 竞价类型，例如 2 代表第二价格拍卖
        "imp": [{  # 描述广告展示的数组
            "id": "impID_1xxxxx",  # Impression对象的唯一标识符
            "tagid": TagID,  # 广告位ID
            "video": {  # 视频广告的相关参数
                "w": 640,  # 视频宽度
                "h": 480,  # 视频高度
                "mimes": ["video/mp4"],  # 支持的视频格式
                "protocols": [1, 2, 3, 4, 5, 6, 7, 8],  # 支持的视频协议
                "startdelay": 0,  # 视频开始前的延迟时间（秒）
                "minduration": 5,  # 视频最小持续时间（秒）
                "maxduration": 30,  # 视频最大持续时间（秒）
                "linearity": 1,  # 线性视频的指示
                "skip": 0,  # 是否可跳过
                "skipmin": 5,  # 观看多少秒后可跳过
                #"skipafter": 15,  # 观看多少秒后必须播放
            },
            #"banner": {  # 横幅广告的相关参数（可选）目前不支持
            #    "w": 320,  # 宽度
            #    "h": 50,   # 高度
            #    "pos": 1,  # 广告位置
            #},
        }],
        "app": {  # 应用相关信息
            "id": AppID,  # 应用唯一标识
            "name": "AppName",  # 应用名称
            "bundle": "com.sotaai.sotaaiinportugues",  # 应用包名
            #"storeurl": "https://example.com",  # 应用商店URL
            "domain": "ssp.com",  # 应用域名
            "cat": ["IAB9", "IAB17"],  # 应用分类
            "publisher": {  # 应用发布者相关信息
                "id": token,  # 发布者唯一标识
                "name": "Publisher Name",  # 发布者名称
                "domain": "ssp.com",  # 发布者域名
                "cat": ["IAB9", "IAB17"],  # 发布者分类 
            },
        },
        "device": {  # 设备相关信息
            "ifa": "ZCXVB092-AS36-4ASD-ASDT-N0OK8UJ6YOHR",  # iOS设备的IDFA 或 Android设备的GAID
            "ua": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",  # 用户代理字符串
            "geo": {  # 地理位置信息
                "country": "BRA",  # 国家
                "lat": -23.323955792,  # 纬度
                "lon": -46.379887,  # 经度
                "type": 1,  # 地理位置类型
                "accuracy": 1000,  # 精确度
            },
            "ip": "2.16.216.4",  # 设备IP地址
            #"didsha1": "didsha1_sample_111",  # 设备ID的SHA1哈希值
            #"didmd5": "didmd5_sample_111",  # 设备ID的MD5哈希值
            #"dpidsha1": "dpidsha1_sample_111",  # 设备平台ID的SHA1哈希值
            "dpidmd5": "e7841ed70252a67a7dc2246aca9aed0a",  # 设备平台ID的MD5哈希值
            "make": "Apple",  # 设备制造商
            "model": "iPhone",  # 设备型号
            "os": "iOS",  # 操作系统
            "osv": "14.5.1",  # 操作系统版本
            "connectiontype": 3,  # 连接类型 0-未知 1-以太网 2-WIFI 3-蜂窝网络
            "devicetype": 1,  # 设备类型
            "h": 1920,  # 屏幕高度
            "w": 1080,  # 屏幕宽度
            "ppi": 450,  # 屏幕每英寸像素数
            "dnt": 0,  # 不追踪标志
            "lmt": 0,  # 限制广告标记
            "mccmnc": "72416",  # 移动国家代码和移动网络代码
        },
        "user": {  # 用户相关信息
            "id": "user-id245p98204-asd",  # 用户唯一标识
            "gender": "M",  # 性别
            "yob": 1985,  # 出生年份
        },
    }
    return request_payload
