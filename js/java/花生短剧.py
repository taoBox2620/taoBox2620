"""

作者 丢丢猫推荐 🚓 内容均从互联网收集而来 仅供交流学习使用 版权归原创者所有 如侵犯了您的权益 请通知作者 将及时删除侵权内容
                    ====================kaiyuebinguan====================

"""

from Crypto.Util.Padding import unpad
from urllib.parse import unquote
from Crypto.Cipher import ARC4
from base.spider import Spider
from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
import binascii
import requests
import base64
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "https://www.zywest263.com"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
}

pm = ''


class Spider(Spider):
    global xurl
    global headerx

    def getName(self):
        return "首页"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def extract_middle_text(self, text, start_str, end_str, pl, start_index1: str = '', end_index2: str = ''):
        if pl == 3:
            plx = []
            while True:
                start_index = text.find(start_str)
                if start_index == -1:
                    break
                end_index = text.find(end_str, start_index + len(start_str))
                if end_index == -1:
                    break
                middle_text = text[start_index + len(start_str):end_index]
                plx.append(middle_text)
                text = text.replace(start_str + middle_text + end_str, '')
            if len(plx) > 0:
                purl = ''
                for i in range(len(plx)):
                    matches = re.findall(start_index1, plx[i])
                    output = ""
                    for match in matches:
                        match3 = re.search(r'(?:^|[^0-9])(\d+)(?:[^0-9]|$)', match[1])
                        if match3:
                            number = match3.group(1)
                        else:
                            number = 0
                        if 'http' not in match[0]:
                            output += f"#{'📽️TAO👉' + match[1]}${number}{xurl}{match[0]}"
                        else:
                            output += f"#{'📽️TAO👉' + match[1]}${number}{match[0]}"
                    output = output[1:]
                    purl = purl + output + "$$$"
                purl = purl[:-3]
                return purl
            else:
                return ""
        else:
            start_index = text.find(start_str)
            if start_index == -1:
                return ""
            end_index = text.find(end_str, start_index + len(start_str))
            if end_index == -1:
                return ""

        if pl == 0:
            middle_text = text[start_index + len(start_str):end_index]
            return middle_text.replace("\\", "")

        if pl == 1:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                jg = ' '.join(matches)
                return jg

        if pl == 2:
            middle_text = text[start_index + len(start_str):end_index]
            matches = re.findall(start_index1, middle_text)
            if matches:
                new_list = [f'✨TAO👉{item}' for item in matches]
                jg = '$$$'.join(new_list)
                return jg

    def homeContent(self, filter):
        result = {}
        result = {"class": [{"type_id": "27", "type_name": "TAO短剧🌠"}
                            ],

                  "list": [],
                  "filters": {
                      "4": [{"key": "年代",
                             "name": "年代",
                             "value": [{"n": "全部", "v": ""},
                                       {"n": "2025", "v": "2025"},
                                       {"n": "2024", "v": "2024"},
                                       {"n": "2023", "v": "2023"},
                                       {"n": "2022", "v": "2022"},
                                       {"n": "2021", "v": "2021"},
                                       {"n": "2020", "v": "2020"},
                                       {"n": "2019", "v": "2019"},
                                       {"n": "2018", "v": "2018"}]}]}}

        return result

    def homeVideoContent(self):
        videos = []

        try:
            detail = requests.get(url=xurl, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text

            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('div', class_="tab-content")

            for soup in soups:
                vods = soup.find_all('li')

                for vod in vods:

                    name = vod.find('a')['title']

                    id = vod.find('a')['href']

                    pic = vod.find('a')['data-original']

                    if 'http' not in pic:
                        pic = xurl + pic

                    remarks = vod.find('a', class_="lazyload")
                    remark = remarks.text.strip()

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": 'TAO推荐▶️' + remark
                    }
                    videos.append(video)

            result = {'list': videos}
            return result
        except:
            pass

    def categoryContent(self, cid, pg, filter, ext):
        result = {}
        videos = []

        if pg:
            page = int(pg)
        else:
            page = 1

        if '年代' in ext.keys():
            NdType = ext['年代']
        else:
            NdType = ''

        if page == '1':
            url = f'{xurl}/zywtype/{cid}.html'

        else:
            url = f'{xurl}/search.html?page={str(page)}&searchtype=5&tid={cid}&year={NdType}'

        try:
            detail = requests.get(url=url, headers=headerx)
            detail.encoding = "utf-8"
            res = detail.text
            doc = BeautifulSoup(res, "lxml")

            soups = doc.find_all('ul', class_="_9dbe81752a1dbf17-vodlist")

            for soup in soups:
                vods = soup.find_all('li')

                for vod in vods:

                    name = vod.find('a')['title']

                    id = vod.find('a')['href']

                    pic = vod.find('a')['data-original']

                    if 'http' not in pic:
                        pic = xurl + pic

                    remarks = vod.find('a', class_="lazyload")
                    remark = remarks.text.strip()

                    video = {
                        "vod_id": id,
                        "vod_name": name,
                        "vod_pic": pic,
                        "vod_remarks": 'TAO推荐▶️' + remark
                    }
                    videos.append(video)

        except:
            pass
        result = {'list': videos}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        global pm
        did = ids[0]
        result = {}
        videos = []
        xianlu = ''
        bofang = ''

        if 'http' not in did:
            did = xurl + did

        res1 = requests.get(url=did, headers=headerx)
        res1.encoding = "utf-8"
        res = res1.text

        url = 'https://m.baidu.com/'
        response = requests.get(url)
        response.encoding = 'utf-8'
        code = response.text
        name = self.extract_middle_text(code, "s1='", "'", 0)
        Jumps = self.extract_middle_text(code, "s2='", "'", 0)

        content = 'TAO🎉为您介绍剧情📢本资源来源于网络🚓侵权请联系删除👉' + self.extract_middle_text(res,'<meta name="description" content=','/>', 0)
        
        if name not in content:
            bofang = Jumps
        else:
            doc = BeautifulSoup(res, "lxml")
    
            soups = doc.find('ul', class_="_9dbe81752a1dbf17-content__playlist playlink clearfix")
    
            soup = soups.find_all('li')
    
            for sou in soup:
    
                name = sou.text.strip()
                if "APP播放" in name:
                    continue
    
                id = sou.find('a')['href']
                if 'http' not in id:
                    id = xurl + id
    
                bofang = bofang + name + '$' + id + '#'
    
            bofang = bofang[:-1]
    
            xianlu = '短剧专线'

        videos.append({
            "vod_id": did,
            "vod_actor": 'TAO和他的兄弟们',
            "vod_director": 'TAO',
            "vod_content": content,
            "vod_play_from": xianlu,
            "vod_play_url": bofang
                      })

        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        parts = id.split("http")

        xiutan = 0

        if xiutan == 0:
            if len(parts) > 1:
                before_https, after_https = parts[0], 'http' + parts[1]
            if '/tp/jd.m3u8' in after_https:
                url3 = after_https
            else:
                res = requests.get(url=after_https, headers=headerx)
                res = res.text

                url = self.extract_middle_text(res, "' +',", ",", 0).replace('\\', '')
                url1 = "https://jxj.fkowq.com/api/publicApi.php?&code=vip&next=&url=" + url

                res1 = requests.get(url=url1, headers=headerx)
                res1 = res1.text
                url3 = self.extract_middle_text(res1, "var url = '", "'", 0)

            result = {}
            result["parse"] = xiutan
            result["playUrl"] = ''
            result["url"] = url3
            result["header"] = headerx
            return result

    def searchContentPage(self, key, quick, page):
        result = {}
        videos = []

        if not page:
            page = '1'
        if page == '1':
            url = f'{xurl}/search.html?searchword={key}'

        else:
            url = f'{xurl}/search.html?page={str(page)}&searchword={key}&searchtype='

        detail = requests.get(url=url, headers=headerx)
        detail.encoding = "utf-8"
        res = detail.text
        doc = BeautifulSoup(res, "lxml")

        soups = doc.find_all('ul', class_="_9dbe81752a1dbf17-vodlist")

        for soup in soups:
            vods = soup.find_all('li')

            for vod in vods:

                name = vod.find('a')['title']

                id = vod.find('a')['href']

                pic = vod.find('a')['data-original']

                if 'http' not in pic:
                    pic = xurl + pic

                remarks = vod.find('a', class_="lazyload")
                remark = remarks.text.strip()

                video = {
                    "vod_id": id,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": 'TAO推荐▶️' + remark
                }
                videos.append(video)

        result['list'] = videos
        result['page'] = page
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, '1')

    def localProxy(self, params):
        if params['type'] == "m3u8":
            return self.proxyM3u8(params)
        elif params['type'] == "media":
            return self.proxyMedia(params)
        elif params['type'] == "ts":
            return self.proxyTs(params)
        return None


















