# -*- coding: utf-8 -*-
import json
import sys
import requests
import urllib.parse
import urllib3

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://fy-musicbox-api.mu-jie.cc"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; 22127RK46C Build/UKQ1.230804.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 Mobile Safari/537.36',
            'Referer': 'https://mu-jie.cc/musicBox/'
        }

    def getName(self):
        return "江湖音乐"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass

    def _req(self, url):
        try:
            return requests.get(url, headers=self.headers, verify=False, timeout=15).json()
        except:
            return {}

    # ================= 删除了 lrc2ssa 函数 =================

    def homeContent(self, filter):
        cats = {}
        cats['theme'] = [{"n": x, "v": x} for x in ["综艺", "影视原声", "ACG", "儿童", "校园", "游戏", "70后", "80后", "90后", "00后", "网络歌曲", "KTV", "经典", "翻唱", "吉他", "钢琴", "器乐", "榜单"]]
        cats['lang'] = [{"n": x, "v": x} for x in ["华语", "欧美", "日语", "韩语", "粤语"]]
        cats['style'] = [{"n": x, "v": x} for x in ["流行", "摇滚", "民谣", "电子", "舞曲", "说唱", "轻音乐", "爵士", "乡村", "R&B/Soul", "古典", "民族", "英伦", "金属", "朋克", "蓝调", "雷鬼", "世界音乐", "拉丁", "New Age", "古风", "后摇", "Bossa Nova"]]
        cats['scene'] = [{"n": x, "v": x} for x in ["清晨", "夜晚", "学习", "工作", "午休", "下午茶", "地铁", "驾车", "运动", "旅行", "散步", "酒吧"]]
        cats['emotion'] = [{"n": x, "v": x} for x in ["怀旧", "清新", "浪漫", "伤感", "治愈", "放松", "孤独", "感动", "兴奋", "快乐", "安静", "思念"]]

        filters = {}
        for key in cats:
            filters[key] = [{"key": "cat", "name": "分类", "value": cats[key]}]

        classes = [
            {'type_name': '热歌推荐', 'type_id': 'rec'},
            {'type_name': '主题', 'type_id': 'theme'},
            {'type_name': '语种', 'type_id': 'lang'},
            {'type_name': '风格', 'type_id': 'style'},
            {'type_name': '场景', 'type_id': 'scene'},
            {'type_name': '情感', 'type_id': 'emotion'}
        ]
        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        return {'list': []}

    def categoryContent(self, tid, pg, filter, extend):
        if pg != '1' and int(pg) > 10:
            return {'list': [], 'page': pg}
        
        try:
            url = ""
            if tid == 'rec':
                url = self.host + "/netease/playlist/recommend?limit=30&page=" + pg
            else:
                defaults = {'theme': '综艺', 'lang': '华语', 'style': '流行', 'scene': '清晨', 'emotion': '怀旧'}
                cat = extend.get('cat', defaults.get(tid))
                url = self.host + "/netease/playlist/category?type=" + urllib.parse.quote(cat) + "&limit=30&page=" + pg
            
            j = self._req(url)
            data_list = []
            if isinstance(j, list):
                data_list = j
            elif isinstance(j, dict) and 'data' in j:
                data_list = j['data']
            
            videos = []
            for d in data_list:
                vid = str(d.get('id', ''))
                pic = d.get('coverImgUrl', '')
                if not pic:
                    pic = d.get('pic', '')
                name = d.get('name', '未知标题')
                remark = "播放: " + str(d.get('playCount', 0))
                
                videos.append({
                    'vod_id': vid + "@@" + pic + "@@" + name,
                    'vod_name': name,
                    'vod_pic': pic,
                    'vod_remarks': remark
                })
            return {'list': videos, 'page': int(pg), 'pagecount': 999, 'limit': 30, 'total': 9999}
        except:
            return {'list': [], 'page': 1}

    def detailContent(self, ids):
        try:
            parts = ids[0].split('@@')
            did = parts[0]
            pic = parts[1] if len(parts) > 1 else ""
            name = parts[2] if len(parts) > 2 else "音乐详情"

            vod = {
                'vod_id': ids[0],
                'vod_name': name,
                'vod_pic': pic,
                'type_name': '音乐',
                'vod_play_from': '江湖音乐'
            }
            
            song_list = []
            data_obj = None

            # 兼容多种列表接口 (榜单/歌单/专辑)
            api_list = [
                self.host + "/api/?source=netease&id=" + did + "&type=toplist",
                self.host + "/meting/?server=netease&type=playlist&id=" + did,
                self.host + "/api/?source=netease&id=" + did + "&type=album"
            ]

            for api in api_list:
                res = self._req(api)
                if not isinstance(res, dict):
                    continue
                if 'code' in res and res['code'] == 200:
                    d = res.get('data')
                    if d and isinstance(d.get('list'), list):
                        data_obj = d
                        song_list = d['list']
                        break
                if 'tracks' in res:
                    data_obj = res
                    song_list = res['tracks']
                    break

            play_list = []
            if song_list:
                new_name = data_obj.get('name')
                if new_name:
                    vod['vod_name'] = new_name
                desc = data_obj.get('description', '')
                if not desc:
                    desc = data_obj.get('desc', '')
                vod['vod_content'] = desc
                new_pic = data_obj.get('pic')
                if not new_pic:
                    new_pic = data_obj.get('coverImgUrl')
                if new_pic:
                    vod['vod_pic'] = new_pic

                for s in song_list:
                    s_name = s.get('name', '')
                    s_artist = s.get('artist', '')
                    if isinstance(s_artist, list):
                        s_artist = "/".join(s_artist)
                    
                    title = s_name + " - " + s_artist
                    title = title.replace('$', ' ').replace('#', ' ')
                    s_id = str(s.get('id', ''))
                    s_pic = s.get('pic', '')
                    play_list.append(title + "$" + s_id + "@@" + s_pic)
            else:
                play_list.append("播放单曲$" + did + "@@" + pic)

            vod['vod_play_url'] = '#'.join(play_list)
            return {'list': [vod]}
        except:
            return {'list': []}

    def searchContent(self, key, quick, pg="1"):
        try:
            videos = []
            encoded_key = urllib.parse.quote(key)

            # 1. 搜索单曲 (song$)
            url_song = self.host + "/netease/search/song/?keywords=" + encoded_key + "&pn=" + pg + "&limit=20"
            data_song = self._req(url_song)
            if isinstance(data_song, list):
                for d in data_song:
                    vid = str(d.get('id', ''))
                    pic = d.get('pic', '')
                    name = d.get('name', '')
                    artist = d.get('artist', '')
                    # 标识为单曲
                    tag_vid = "song$" + vid
                    videos.append({
                        'vod_id': tag_vid + "@@" + pic + "@@" + name,
                        'vod_name': name,
                        'vod_pic': pic,
                        'vod_remarks': artist
                    })

            # 2. 搜索歌单 (playlist$)
            url_playlist = self.host + "/netease/search/playlist/?keywords=" + encoded_key + "&limit=20"
            data_playlist = self._req(url_playlist)
            if isinstance(data_playlist, list):
                for d in data_playlist:
                    vid = str(d.get('id', ''))
                    pic = d.get('coverImgUrl', '')
                    name = d.get('name', '')
                    count = str(d.get('trackCount', 0))
                    # 标识为歌单
                    tag_vid = "playlist$" + vid
                    videos.append({
                        'vod_id': tag_vid + "@@" + pic + "@@" + name,
                        'vod_name': name,
                        'vod_pic': pic,
                        'vod_remarks': "歌单(" + count + "首)"
                    })

            return {'list': videos, 'page': pg}
        except:
            return {'list': [], 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        res = {
            "parse": 0, 
            "jx": 0, 
            "url": "", 
            "pic": "", 
            "cover": "", 
            "lrc": "", 
            "subt": "", 
            "subs": [], 
            "header": self.headers
        }
        
        real_id = id
        if '@@' in id:
            parts = id.split('@@')
            real_id = parts[0]
            res['pic'] = parts[1] if len(parts) > 1 else ""
            res['cover'] = res['pic']
        
        # 去掉搜索时添加的前缀
        if real_id.startswith("song$"):
            real_id = real_id[5:]
        elif real_id.startswith("playlist$"):
            real_id = real_id[9:]
        
        # 获取 LRC 歌词 (仅保留原始 LRC)
        try:
            lrc_url = self.host + "/meting/?server=netease&type=lrc&id=" + real_id
            r = requests.get(lrc_url, headers=self.headers, verify=False, timeout=5)
            lrc_text = r.text
            if isinstance(lrc_text, str) and '[' in lrc_text:
                res['lrc'] = lrc_text
        except:
            pass

        play_url = self.host + "/meting/?server=netease&type=url&id=" + real_id
        res['url'] = ['江湖音质', play_url]
        return res

    def localProxy(self, param):
        pass
