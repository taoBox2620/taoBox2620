"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: '声阅听书',
  lang: 'hipy',
})
"""

# -*- coding: utf-8 -*-
import sys
import json
import re
import urllib.parse
import requests
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "声阅听书"

    def init(self, extend=""):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def getHeader(self):
        return self.headers

    # ==================== 1. 首页与分类 ====================
    def homeContent(self, filter):
        # 对应海阔源码中的五大主分类
        classes = [
            {"type_id": "1", "type_name": "有声小说"},
            {"type_id": "2", "type_name": "热歌神曲"},
            {"type_id": "3", "type_name": "排行榜"},
            {"type_id": "4", "type_name": "相声评书"},
            {"type_id": "5", "type_name": "亲子儿童"},
        ]
        
        # 对应海阔源码中复杂的 setTabs 分类 ID
        filters = {
            "1": [{"key": "classifyId", "name": "类型", "value": [{"n": "玄幻奇幻", "v": "44"}, {"n": "武侠仙侠", "v": "48"}, {"n": "穿越架空", "v": "52"}, {"n": "都市传说", "v": "42"}, {"n": "科幻竞技", "v": "57"}, {"n": "幻想言情", "v": "169"}, {"n": "独家定制", "v": "170"}, {"n": "古代言情", "v": "207"}, {"n": "影视原著", "v": "213"}, {"n": "悬疑推理", "v": "45"}, {"n": "历史军事", "v": "56"}, {"n": "现代言情", "v": "41"}, {"n": "青春校园", "v": "55"}, {"n": "文学名著", "v": "61"}]}],
            "2": [{"key": "classifyId", "name": "类型", "value": [{"n": "全部分类", "v": "0"}, {"n": "抖音神曲", "v": "253"}, {"n": "怀旧老歌", "v": "252"}, {"n": "创作|翻唱", "v": "248"}, {"n": "催眠", "v": "254"}, {"n": "古风", "v": "255"}, {"n": "播客周刊", "v": "1423"}, {"n": "民谣", "v": "1409"}, {"n": "纯音乐", "v": "1408"}, {"n": "3D电子", "v": "249"}, {"n": "音乐课程", "v": "251"}, {"n": "音乐推荐", "v": "246"}, {"n": "音乐故事", "v": "247"}, {"n": "情感治愈", "v": "250"}, {"n": "儿童音乐", "v": "1407"}]}],
            "3": [
                {"key": "tabId", "name": "榜单", "value": [{"n": "热播榜", "v": "15"}, {"n": "免费榜", "v": "16"}, {"n": "畅销榜", "v": "2"}, {"n": "男频VIP榜", "v": "20"}, {"n": "女频VIP榜", "v": "21"}, {"n": "新品榜", "v": "8"}, {"n": "精品榜", "v": "23"}]},
                {"key": "id", "name": "分类", "value": [{"n": "有声小说", "v": "123"}, {"n": "相声评书", "v": "126"}, {"n": "历史", "v": "140"}, {"n": "影视原声", "v": "141"}, {"n": "两性情感", "v": "129"}, {"n": "人文", "v": "137"}, {"n": "音乐调频", "v": "131"}, {"n": "戏曲", "v": "139"}, {"n": "国漫游戏", "v": "130"}, {"n": "畅销书", "v": "127"}, {"n": "脱口秀", "v": "785"}, {"n": "娱乐段子", "v": "132"}, {"n": "个人提升", "v": "133"}, {"n": "儿童", "v": "125"}, {"n": "学科教育", "v": "128"}, {"n": "商业财经", "v": "134"}, {"n": "外语", "v": "138"}]}
            ],
            "4": [{"key": "classifyId", "name": "类型", "value": [{"n": "全部分类", "v": "0"}, {"n": "郭德纲", "v": "84"}, {"n": "相声新人", "v": "222"}, {"n": "张少佐", "v": "313"}, {"n": "刘立福", "v": "314"}, {"n": "评书大全", "v": "220"}, {"n": "小品合辑", "v": "221"}, {"n": "刘兰芳", "v": "309"}, {"n": "连丽如", "v": "311"}, {"n": "田占义", "v": "317"}, {"n": "单口相声", "v": "219"}, {"n": "袁阔成", "v": "310"}, {"n": "孙一", "v": "315"}, {"n": "王玥波", "v": "316"}, {"n": "单田芳", "v": "217"}, {"n": "热门相声", "v": "218"}, {"n": "相声名家", "v": "290"}, {"n": "粤语评书", "v": "320"}, {"n": "关永超", "v": "325"}, {"n": "马长辉", "v": "326"}, {"n": "赵维莉", "v": "327"}, {"n": "潮剧", "v": "1718"}, {"n": "沪剧", "v": "1719"}, {"n": "晋剧", "v": "1720"}]}],
            "5": [{"key": "classifyId", "name": "类型", "value": [{"n": "全部分类", "v": "0"}, {"n": "益智故事", "v": "209"}, {"n": "科普知识", "v": "83"}, {"n": "国学经典", "v": "2"}, {"n": "卡通动画", "v": "282"}, {"n": "儿童教育", "v": "4"}, {"n": "英语启蒙", "v": "12"}, {"n": "早教启蒙", "v": "385"}, {"n": "轻松哄睡", "v": "210"}]}]
        }
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        return self.categoryContent("1", "1", None, {})

    # ==================== 2. 列表页提取 ====================
    def categoryContent(self, tid, pg, filter, extend):
        pg_int = int(pg)
        
        # 对应源码里的 switch(str1) 逻辑，动态拼接不同 API
        if tid == "1":
            classifyId = extend.get("classifyId", "44")
            url = f"http://tingshu.kuwo.cn/v2/api/search/filter/albums?classifyId={classifyId}&sortType=pubDate&rn=20&pn={pg_int}"
        elif tid == "2":
            classifyId = extend.get("classifyId", "0")
            url = f"http://tingshu.kuwo.cn/v2/api/search/filter/albums?classifyId={classifyId}&rn=20&categoryId=37&pn={pg_int}"
        elif tid == "3":
            tabId = extend.get("tabId", "15")
            typeId = extend.get("id", "123")
            url = f"http://tingshu.kuwo.cn/v2/api/product/rank/dataList?tabId={tabId}&id={typeId}&rn=20&pn={pg_int}"
        elif tid == "4":
            classifyId = extend.get("classifyId", "0")
            url = f"http://tingshu.kuwo.cn/v2/api/search/filter/albums?classifyId={classifyId}&sortType=playCnt&rn=20&categoryId=5&pn={pg_int}"
        elif tid == "5":
            classifyId = extend.get("classifyId", "0")
            url = f"http://tingshu.kuwo.cn/v2/api/search/filter/albums?classifyId={classifyId}&sortType=playCnt&rn=20&categoryId=1&pn={pg_int}"
        else:
            url = f"http://tingshu.kuwo.cn/v2/api/search/filter/albums?classifyId=44&sortType=pubDate&rn=20&pn={pg_int}"

        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            data = r.json()
            
            # 排行榜和普通分类的数组层级不同，在此进行融合兜底
            items = data.get("data", {}).get("data", [])
            if not items:
                items = data.get("data", {}).get("rankDataList", [])
            
            videos = []
            for it in items:
                name = it.get("albumName", "") or it.get("title", "")
                if not name:
                    continue
                videos.append({
                    "vod_id": str(it.get("albumId", "")),
                    "vod_name": name,
                    "vod_pic": it.get("coverImg", "") or it.get("albumImg", ""),
                    "vod_remarks": f"集数: {it.get('songNum', '未知')}"
                })
            return {"list": videos, "page": pg_int}
        except Exception as e:
            return {"list": []}

    # ==================== 3. 详情页与线路提取 ====================
    def detailContent(self, ids):
        # 对应源码 rule2：提取专辑所有歌曲
        # TVBox 详情页只请求一次，为了拿全，将 rn 直接拉到 1000 获取超长听书列表
        url = f"http://search.kuwo.cn/r.s?stype=albuminfo&user=0&uid=0&loginUid=0&loginSid=null&prod=kwplayer_ar_9.1.8.1&bkprod=kwbook_ar_9.1.8.1&source=kwplayer_ar_9.1.8.1_t87.apk&bksource=kwbook_ar_9.1.8.1_t87.apk&corp=kuwo&albumid={ids[0]}&pn=0&rn=1000&show_copyright_off=1&vipver=MUSIC_8.2.0.0_BCS17&mobi=1&sortby=3&show_digitalmusic_off=1&iskwbook=1&rformat=json"
        
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            text = r.text
            # 酷我有时候返回的数据不纯净，安全气囊强制截取 JSON
            if not text.startswith("{"):
                match = re.search(r'\{.*\}', text, re.S)
                if match:
                    text = match.group(0)
            data = json.loads(text)
            
            play_list = []
            for it in data.get("musiclist", []):
                name = it.get("name", "未知")
                rid = it.get("musicrid", "")
                if rid:
                    # 组装线路: 音频名称$歌曲ID
                    play_list.append(f"{name}${rid}")
            
            return {
                "list": [{
                    "vod_id": ids[0],
                    "vod_name": data.get("name", "未知标题"),
                    "vod_pic": data.get("img", ""),
                    "type_name": "有声书",
                    "vod_content": data.get("info", ""),
                    "vod_play_from": "声阅听书",
                    "vod_play_url": "#".join(play_list)
                }]
            }
        except Exception as e:
            return {"list": []}

    # ==================== 4. 搜索处理 ====================
    def searchContent(self, key, quick, pg="1"):
        pg_int = int(pg)
        idx = pg_int - 1
        
        # 对应源码 search1
        url = f"http://search.kuwo.cn/r.s?client=kt&all={urllib.parse.quote(key)}&ft=album&newsearch=1&itemset=web_2013&pn={idx}&rn=20&rformat=json&encoding=utf8&show_series_listen=1&mobi=1"
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            text = r.text
            if not text.startswith("{"):
                match = re.search(r'\{.*\}', text, re.S)
                if match:
                    text = match.group(0)
            data = json.loads(text)
            
            videos = []
            for it in data.get("albumlist", []):
                videos.append({
                    "vod_id": str(it.get("albumid", "")),
                    "vod_name": it.get("name", ""),
                    "vod_pic": it.get("img", ""),
                    "vod_remarks": f"集数: {it.get('musiccnt', '未知')}"
                })
            return {"list": videos, "page": pg_int}
        except Exception as e:
            return {"list": []}

    # ==================== 5. 播放解析 ====================
    def playerContent(self, flag, id, vipFlags):
        # 通过传入的 rid 动态请求转换真实的 mp3 地址
        url = f"http://mobi.kuwo.cn/mobi.s?f=web&user=0&source=kwplayercar_ar_6.0.0.9_B_jiakong_vh.apk&type=convert_url_with_sign&rid={id}&br=128kmp3"
        try:
            r = requests.get(url, headers=self.headers, timeout=10)
            data = r.json()
            play_url = data.get("data", {}).get("url", "")
            if play_url:
                return {
                    "parse": 0,
                    "url": play_url
                }
        except Exception as e:
            pass
            
        return {"parse": 0, "url": ""}

    def localProxy(self, param):
        pass

if __name__ == "__main__":
    spider = Spider()
    print(spider.getName())
