from urllib.parse import quote
from base.spider import Spider
import requests
import json
import re

class Spider(Spider):
    def __init__(self):
        super().__init__()
        
    def getName(self):
        return "甜圈短剧"

    def init(self, extend):
        self.host = "https://mov.cenguigui.cn"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Referer': 'https://mov.cenguigui.cn/'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def homeContent(self, filter):
        categories = [
            {'type_id': '逆袭', 'type_name': '逆袭'},
            {'type_id': '霸总', 'type_name': '霸总'},
            {'type_id': '现代言情', 'type_name': '现代言情'},
            {'type_id': '打脸虐渣', 'type_name': '打脸虐渣'},
            {'type_id': '豪门恩怨', 'type_name': '豪门恩怨'},
            {'type_id': '神豪', 'type_name': '神豪'},
            {'type_id': '马甲', 'type_name': '马甲'},
            {'type_id': '都市日常', 'type_name': '都市日常'},
            {'type_id': '战神归来', 'type_name': '战神归来'},
            {'type_id': '小人物', 'type_name': '小人物'},
            {'type_id': '女性成长', 'type_name': '女性成长'},
            {'type_id': '大女主', 'type_name': '大女主'},
            {'type_id': '穿越', 'type_name': '穿越'},
            {'type_id': '都市修仙', 'type_name': '都市修仙'},
            {'type_id': '强者回归', 'type_name': '强者回归'},
            {'type_id': '亲情', 'type_name': '亲情'},
            {'type_id': '古装', 'type_name': '古装'},
            {'type_id': '重生', 'type_name': '重生'},
            {'type_id': '闪婚', 'type_name': '闪婚'},
            {'type_id': '赘婿逆袭', 'type_name': '赘婿逆袭'},
            {'type_id': '虐恋', 'type_name': '虐恋'},
            {'type_id': '追妻', 'type_name': '追妻'},
            {'type_id': '天下无敌', 'type_name': '天下无敌'},
            {'type_id': '家庭伦理', 'type_name': '家庭伦理'},
            {'type_id': '萌宝', 'type_name': '萌宝'},
            {'type_id': '古风权谋', 'type_name': '古风权谋'},
            {'type_id': '职场', 'type_name': '职场'},
            {'type_id': '奇幻脑洞', 'type_name': '奇幻脑洞'},
            {'type_id': '异能', 'type_name': '异能'},
            {'type_id': '无敌神医', 'type_name': '无敌神医'},
            {'type_id': '古风言情', 'type_name': '古风言情'},
            {'type_id': '传承觉醒', 'type_name': '传承觉醒'},
            {'type_id': '现言甜宠', 'type_name': '现言甜宠'},
            {'type_id': '奇幻爱情', 'type_name': '奇幻爱情'},
            {'type_id': '乡村', 'type_name': '乡村'},
            {'type_id': '历史古代', 'type_name': '历史古代'},
            {'type_id': '王妃', 'type_name': '王妃'},
            {'type_id': '高手下山', 'type_name': '高手下山'},
            {'type_id': '娱乐圈', 'type_name': '娱乐圈'},
            {'type_id': '强强联合', 'type_name': '强强联合'},
            {'type_id': '破镜重圆', 'type_name': '破镜重圆'},
            {'type_id': '暗恋成真', 'type_name': '暗恋成真'},
            {'type_id': '民国', 'type_name': '民国'},
            {'type_id': '欢喜冤家', 'type_name': '欢喜冤家'},
            {'type_id': '系统', 'type_name': '系统'},
            {'type_id': '真假千金', 'type_name': '真假千金'},
            {'type_id': '龙王', 'type_name': '龙王'},
            {'type_id': '校园', 'type_name': '校园'},
            {'type_id': '穿书', 'type_name': '穿书'},
            {'type_id': '女帝', 'type_name': '女帝'},
            {'type_id': '团宠', 'type_name': '团宠'},
            {'type_id': '年代爱情', 'type_name': '年代爱情'},
            {'type_id': '玄幻仙侠', 'type_name': '玄幻仙侠'},
            {'type_id': '青梅竹马', 'type_name': '青梅竹马'},
            {'type_id': '悬疑推理', 'type_name': '悬疑推理'},
            {'type_id': '皇后', 'type_name': '皇后'},
            {'type_id': '替身', 'type_name': '替身'},
            {'type_id': '大叔', 'type_name': '大叔'},
            {'type_id': '喜剧', 'type_name': '喜剧'},
            {'type_id': '剧情', 'type_name': '剧情'}
        ]
        return {"class": categories}

    def categoryContent(self, cid, pg, filter, ext):
        try:
            page = int(pg) if pg else 1
            offset = (page - 1) * 13
            
            url = f"{self.host}/duanju/api.php?classname={quote(cid)}&offset={offset}"
            res = self.session.get(url, timeout=10)
            res.encoding = 'utf-8'
            
            json_data = res.json()
            data_list = json_data.get('data', [])
            
            videos = []
            for item in data_list:
                episode_cnt = item.get('episode_cnt', '未知')
                score = item.get('score', '0')
                videos.append({
                    "vod_id": str(item.get('book_id', '')),
                    "vod_name": item.get('title', '未知标题'),
                    "vod_pic": item.get('cover', ''),
                    "vod_remarks": f"{episode_cnt}集 | ⭐{score}"
                })
            
            has_more = len(data_list) > 0 
            return {
                'list': videos,
                'page': page,
                'pagecount': page + 1 if has_more else page,
                'limit': len(videos) if videos else 20,
                'total': 9999
            }
        except Exception:
            return {'list': []}

    def detailContent(self, ids):
        try:
            book_id = ids[0]
            url = f"{self.host}/duanju/api.php?book_id={book_id}"
            
            res = self.session.get(url, timeout=10)
            res.encoding = 'utf-8'
            json_data = res.json()
            
            episodes_data = json_data.get('data', [])
            play_urls = []
            
            if isinstance(episodes_data, list):
                for i in episodes_data:
                    title = i.get('title', '').replace('$', ' ').replace('#', ' ')
                    video_id = i.get('video_id', '')
                    if video_id:
                        play_urls.append(f"{title}${video_id}")
            
            vod = {
                "vod_id": book_id,
                "vod_name": json_data.get('title', '未知名称'),
                "type_name": json_data.get('category', ''),
                "vod_year": json_data.get('time', ''),
                "vod_remarks": f"共{json_data.get('episode_cnt', '')}集",
                "vod_content": json_data.get('desc', '暂无简介'),
                "vod_play_from": "甜圈短剧",
                "vod_play_url": "#".join(play_urls)
            }
            return {'list': [vod]}
        except Exception:
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        return self.categoryContent(key, pg, None, None)

    def playerContent(self, flag, id, vipFlags):
        try:
            url = f"{self.host}/duanju/api.php?video_id={id}&type=mp4"
            res = self.session.get(url, allow_redirects=False, timeout=8)
            
            location = res.headers.get('Location') or res.headers.get('location')
            
            if location:
                play_url = f"{location}#.mp4"
            else:
                play_url = url
                
            return {
                "parse": 0,
                "playUrl": "",
                "url": play_url,
                "header": {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'
                }
            }
        except Exception:
            return {
                "parse": 0,
                "url": "",
                "header": self.headers
            }

    def localProxy(self, param):
        return []

