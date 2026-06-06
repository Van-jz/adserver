import json
import requests
from datetime import datetime
import hmac
import hashlib
from RTBRequest import *

def hmac_sha256(key, message):
    # 将key和message编码为字节,  使用HMAC和SHA256进行加密
    hmac_result = hmac.new(message.encode(), key.encode(), hashlib.sha256)
    #hmac_result = hmac.new(key.encode(), message.encode(), hashlib.sha256)
    # 获取十六进制编码的摘要
    hex_digest = hmac_result.hexdigest()
    return hex_digest

# 发送请求并处理响应的函数
def send_request_and_process_response():
    request_id = "unique-request-id2023112911500001"
    token = "92117e18b6391b92451277e318f36d0c"
    sign = hmac_sha256(request_id, token)
    #adx_url = "https://ad-intl-web-beta.test.gifshow.com/rest/n/adintl/KwaiNetwork/getKNAd"
    adx_url = "https://ad-intl-web-beta.test.gifshow.com/rest/n/adintl/KwaiNetwork/getKNAd?sign=" + sign
    rtb_request = get_1_request(request_id, token)
    
    try:
        print("try visit adx", adx_url)
        response = requests.post(adx_url, json=rtb_request)
        #response.raise_for_status()
        
        # 处理ADX返回的数据
        if response.status_code == 200 and response.json().get("seatbid"):
            ad_data = response.json()
            log_ad_data(ad_data, rtb_request)
        elif response.status_code == 204:
            print("No ad returned")
        elif response.status_code == 400:
            print("Bad request.\n", response.headers, "\n", rtb_request)
        else:
            print(f"Error: {response.status_code}")
            
    except requests.RequestException as e:
        print(f"Error sending request: {e}")

# 将广告信息写入日志的函数
def log_ad_data(ad_data, rtb_request):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "request_data": rtb_request,
        "ad_data": ad_data
    }
    datestr = datetime.now().strftime("%Y%m%d")
    with open("log/ad_log_" + datestr + ".json", "a") as log_file:
        log_file.write(json.dumps(log_entry) + "\n")
    print("Ad logged")

# 示例使用
send_request_and_process_response()
