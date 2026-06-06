import requests
from bs4 import BeautifulSoup
import json

url = "https://bj.bcebos.com/v1/pc-resource/dexguard/device_config.html"
response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

# 找到表格并提取数据
table = soup.find('table')
data = []
for row in table.find_all('tr'):
    cols = row.find_all('td')
    if len(cols) >= 2:
        data.append({
            'column1': cols[0].get_text(strip=True),
            'column2': cols[1].get_text(strip=True)
        })

print(json.dumps(data, indent=2))
