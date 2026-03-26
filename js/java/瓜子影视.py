# coding=utf-8
# !/usr/bin/python

"""

作者 丢丢喵 内容均从互联网收集而来 仅供交流学习使用 严禁用于商业用途 请于24小时内删除
         ====================Diudiumiao====================

"""

from Crypto.Util.Padding import unpad
from Crypto.Util.Padding import pad
from urllib.parse import urlparse
from urllib.parse import unquote
from Crypto.Cipher import ARC4
from urllib.parse import quote
from base.spider import Spider
from Crypto.Cipher import AES
from datetime import datetime
from bs4 import BeautifulSoup
from base64 import b64decode
import concurrent.futures
import urllib.request
import urllib.parse
import datetime
import binascii
import requests
import base64
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "https://api.rwkdzqpd.com"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.87 Safari/537.36'
          }

headerx = {
    "user-agent": "Dart/3.9 (dart:io)",
    "api-ver": "1.0.2.0",
    "host": "api.rwkdzqpd.com",
    "content-type": "application/json",
    "app-ver": "1.0.2.0",
    "token": "a9bebd5714f6aa203c0db0d7a179bfa5.f0b0a547d53d1e7d589a1d79ed9b7cd728cac9d706d2d5a9ef2d4db160ed7e3f11add16cd1402615d8be023293571250d87568bc0bb932c5050c93eb5fb5db514f4b448f491b84b93dae1d6470a09de9e48b1c821fc4343e9ab1b8e7933929b91466247c8867fcff3c074a533954be23e25d262682a201673654e0a571ffc19d163f1c0e6d8c7e069e88ec46266a22ae.9bf0b78a32b5f2525bd234bdf0487393610405424feea17c89eb54363bd95f26",
    "code": "QZ001",
    "Accept-Encoding": "gzip, deflate",
    "Content-Length": "19"
          }

class Spider(Spider):

    def getName(self):
        return "丢丢喵"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeContent(self, filter):
        result = {}
        result = {"class": [{"type_id": "1", "type_name": "电影"},
                            {"type_id": "2", "type_name": "剧集"},
                            {"type_id": "3", "type_name": "综艺"},
                            {"type_id": "4", "type_name": "动漫"},
                            {"type_id": "64", "type_name": "短剧"}],
                  "list": [],
                  "filters": {"1": [{"key": "地区",
                                    "name": "地区",
                                    "value": [{"n": "全部", "v": "0"},
                                              {"n": "大陆", "v": "大陆"},
                                              {"n": "香港", "v": "香港"},
                                              {"n": "台湾", "v": "台湾"},
                                              {"n": "欧美", "v": "欧美"},
                                              {"n": "日本", "v": "日本"},
                                              {"n": "韩国", "v": "韩国"},
                                              {"n": "泰国", "v": "泰国"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "列表",
                                    "name": "列表",
                                    "value": [{"n": "最新", "v": "d_addtime"},
                                              {"n": "高分", "v": "d_score"}]},
                                    {"key": "年代",
                                    "name": "年代",
                                    "value": [{"n": "全部", "v": "0"},
                                              {"n": "2026", "v": "2026"},
                                              {"n": "2025", "v": "2025"},
                                              {"n": "2024", "v": "2024"},
                                              {"n": "2023", "v": "2023"},
                                              {"n": "2022", "v": "2022"},
                                              {"n": "2021", "v": "2021"},
                                              {"n": "2020", "v": "2020"},
                                              {"n": "2019", "v": "2019"},
                                              {"n": "2018", "v": "2018"},
                                              {"n": "2017", "v": "2017"},
                                              {"n": "2016", "v": "2016"},
                                              {"n": "10-15年代", "v": "2015,2014,2013,2012,2011,2010"},
                                              {"n": "00年代", "v": "2000,2001,2002,2003,2004,2005,2006,2007,2008,2009"}]}],
                              "2": [{"key": "地区",
                                    "name": "地区",
                                    "value": [{"n": "全部", "v": "0"},
                                              {"n": "大陆", "v": "大陆"},
                                              {"n": "香港", "v": "香港"},
                                              {"n": "台湾", "v": "台湾"},
                                              {"n": "欧美", "v": "欧美"},
                                              {"n": "日本", "v": "日本"},
                                              {"n": "韩国", "v": "韩国"},
                                              {"n": "泰国", "v": "泰国"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "列表",
                                    "name": "列表",
                                    "value": [{"n": "最新", "v": "d_addtime"},
                                              {"n": "高分", "v": "d_score"}]},
                                    {"key": "年代",
                                    "name": "年代",
                                    "value": [{"n": "全部", "v": "0"},
                                              {"n": "2026", "v": "2026"},
                                              {"n": "2025", "v": "2025"},
                                              {"n": "2024", "v": "2024"},
                                              {"n": "2023", "v": "2023"},
                                              {"n": "2022", "v": "2022"},
                                              {"n": "2021", "v": "2021"},
                                              {"n": "2020", "v": "2020"},
                                              {"n": "2019", "v": "2019"},
                                              {"n": "2018", "v": "2018"},
                                              {"n": "2017", "v": "2017"},
                                              {"n": "2016", "v": "2016"},
                                              {"n": "10-15年代", "v": "2015,2014,2013,2012,2011,2010"},
                                              {"n": "00年代", "v": "2000,2001,2002,2003,2004,2005,2006,2007,2008,2009"}]}],
                              "3": [{"key": "地区",
                                    "name": "地区",
                                    "value": [{"n": "全部", "v": "0"},
                                              {"n": "大陆", "v": "大陆"},
                                              {"n": "香港", "v": "香港"},
                                              {"n": "台湾", "v": "台湾"},
                                              {"n": "欧美", "v": "欧美"},
                                              {"n": "日本", "v": "日本"},
                                              {"n": "韩国", "v": "韩国"},
                                              {"n": "泰国", "v": "泰国"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "列表",
                                    "name": "列表",
                                    "value": [{"n": "最新", "v": "d_addtime"},
                                              {"n": "高分", "v": "d_score"}]},
                                    {"key": "年代",
                                    "name": "年代",
                                    "value": [{"n": "全部", "v": "0"},
                                              {"n": "2026", "v": "2026"},
                                              {"n": "2025", "v": "2025"},
                                              {"n": "2024", "v": "2024"},
                                              {"n": "2023", "v": "2023"},
                                              {"n": "2022", "v": "2022"},
                                              {"n": "2021", "v": "2021"},
                                              {"n": "2020", "v": "2020"},
                                              {"n": "2019", "v": "2019"},
                                              {"n": "2018", "v": "2018"},
                                              {"n": "2017", "v": "2017"},
                                              {"n": "2016", "v": "2016"},
                                              {"n": "10-15年代", "v": "2015,2014,2013,2012,2011,2010"},
                                              {"n": "00年代", "v": "2000,2001,2002,2003,2004,2005,2006,2007,2008,2009"}]}],
                              "4": [{"key": "地区",
                                    "name": "地区",
                                    "value": [{"n": "全部", "v": "0"},
                                              {"n": "大陆", "v": "大陆"},
                                              {"n": "香港", "v": "香港"},
                                              {"n": "台湾", "v": "台湾"},
                                              {"n": "欧美", "v": "欧美"},
                                              {"n": "日本", "v": "日本"},
                                              {"n": "韩国", "v": "韩国"},
                                              {"n": "泰国", "v": "泰国"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "列表",
                                    "name": "列表",
                                    "value": [{"n": "最新", "v": "d_addtime"},
                                              {"n": "高分", "v": "d_score"}]},
                                    {"key": "年代",
                                    "name": "年代",
                                    "value": [{"n": "全部", "v": "0"},
                                              {"n": "2026", "v": "2026"},
                                              {"n": "2025", "v": "2025"},
                                              {"n": "2024", "v": "2024"},
                                              {"n": "2023", "v": "2023"},
                                              {"n": "2022", "v": "2022"},
                                              {"n": "2021", "v": "2021"},
                                              {"n": "2020", "v": "2020"},
                                              {"n": "2019", "v": "2019"},
                                              {"n": "2018", "v": "2018"},
                                              {"n": "2017", "v": "2017"},
                                              {"n": "2016", "v": "2016"},
                                              {"n": "10-15年代", "v": "2015,2014,2013,2012,2011,2010"},
                                              {"n": "00年代", "v": "2000,2001,2002,2003,2004,2005,2006,2007,2008,2009"}]}],
                             "64": [{"key": "地区",
                                    "name": "地区",
                                    "value": [{"n": "全部", "v": "0"},
                                              {"n": "大陆", "v": "大陆"},
                                              {"n": "香港", "v": "香港"},
                                              {"n": "台湾", "v": "台湾"},
                                              {"n": "欧美", "v": "欧美"},
                                              {"n": "日本", "v": "日本"},
                                              {"n": "韩国", "v": "韩国"},
                                              {"n": "泰国", "v": "泰国"},
                                              {"n": "其他", "v": "其他"}]},
                                    {"key": "列表",
                                    "name": "列表",
                                    "value": [{"n": "最新", "v": "d_addtime"},
                                              {"n": "高分", "v": "d_score"}]},
                                    {"key": "年代",
                                    "name": "年代",
                                    "value": [{"n": "全部", "v": "0"},
                                              {"n": "2026", "v": "2026"},
                                              {"n": "2025", "v": "2025"},
                                              {"n": "2024", "v": "2024"},
                                              {"n": "2023", "v": "2023"},
                                              {"n": "2022", "v": "2022"},
                                              {"n": "2021", "v": "2021"},
                                              {"n": "2020", "v": "2020"},
                                              {"n": "2019", "v": "2019"},
                                              {"n": "2018", "v": "2018"},
                                              {"n": "2017", "v": "2017"},
                                              {"n": "2016", "v": "2016"},
                                              {"n": "10-15年代", "v": "2015,2014,2013,2012,2011,2010"},
                                              {"n": "00年代", "v": "2000,2001,2002,2003,2004,2005,2006,2007,2008,2009"}]}]}}

        return result

    def homeVideoContent(self):
        videos = []
        for page_num in range(1, 5):
            payload = self.build_search_payload(page_num)
            urlz = self.get_search_url()
            response = self.send_search_request(urlz, payload)
            data = self.get_response_json(response)
            self.process_search_list(data['data']['list'], videos)
        result = self.build_home_video_result(videos)
        return result

    def build_search_payload(self, page_num):
        return {"keywords": "","area": "0","year": "2026","tid": "0","sort": "d_score","lang": 0,"class": "","page": page_num,"pageSize": 10}

    def get_search_url(self):
        return f'{xurl}/Pc/Search/GetConditionList'

    def send_search_request(self, url, payload):
        return requests.post(url=url, headers=headerx, json=payload)

    def get_response_json(self, response):
        return response.json()

    def process_search_list(self, vod_list, videos):
        for vod in vod_list:
            video = self.parse_search_item(vod)
            videos.append(video)

    def parse_search_item(self, vod):
        return {
            "vod_id": vod['vod_id'],
            "vod_name": vod['vod_name'],
            "vod_pic": vod['vod_pic'],
            "vod_year": vod.get('vod_year', '暂无备注'),
            "vod_remarks": vod.get('new_continue', '') or vod.get('vod_scroe', '') or '暂无备注'
               }

    def build_home_video_result(self, videos):
        return {'list': videos}

    def categoryContent(self, cid, pg, filter, ext):
        videos = []
        page = self.get_page_number(pg)
        NdType = self.get_ext_value(ext, '年代', '2026')
        DqType = self.get_ext_value(ext, '地区', '')
        LxType = self.get_ext_value(ext, '列表', 'd_addtime')
        payload = self.build_category_payload(cid, page, NdType, DqType, LxType)
        urlz = self.get_search_url()
        response = self.send_search_request(urlz, payload)
        data = self.get_response_json(response)
        self.process_search_list(data['data']['list'], videos)
        result = self.build_category_result(videos, pg)
        return result

    def get_page_number(self, pg):
        return int(pg) if pg else 1

    def get_ext_value(self, ext, key, default=''):
        return ext[key] if key in ext else default

    def build_category_payload(self, cid, page, NdType, DqType, LxType):
        return {"keywords": "","area": DqType,"year": NdType,"tid": cid,"sort": LxType,"lang": 0,"class": "","page": page,"pageSize": 10}

    def get_search_url(self):
        return f'{xurl}/Pc/Search/GetConditionList'

    def send_search_request(self, url, payload):
        return requests.post(url=url, headers=headerx, json=payload)

    def get_response_json(self, response):
        return response.json()

    def process_search_list(self, vod_list, videos):
        for vod in vod_list:
            video = self.parse_search_item(vod)
            videos.append(video)

    def parse_search_item(self, vod):
        return {
            "vod_id": vod['vod_id'],
            "vod_name": vod['vod_name'],
            "vod_pic": vod['vod_pic'],
            "vod_year": vod.get('vod_year', '暂无备注'),
            "vod_remarks": vod.get('new_continue', '') or vod.get('vod_scroe', '') or '暂无备注'
               }

    def build_category_result(self, videos, pg):
        result = {'list': videos}
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        did = self.get_first_id(ids)
        payload = self.build_detail_payload(did)
        urlz = self.get_vod_info_url()
        response = self.send_post_request(urlz, payload)
        data = self.get_response_json(response)
        content = self.build_vod_content(data)
        director = self.get_nested_value(data, 'vod_director')
        remarks = self.build_remarks(data)
        year = self.get_nested_value(data, 'vod_year')
        area = self.get_nested_value(data, 'vod_area')
        payloads = self.build_playlist_payload(did)
        urlzs = self.get_playlist_url()
        response = self.send_post_request(urlzs, payloads)
        datas = self.get_response_json(response)
        urls_list = self.get_urls_list(datas)
        if not urls_list:
            return {'msg': 'TAO提醒：📢该影片暂无上架'}
        bofang = self.build_play_string(urls_list)
        videos = self.build_video_info(did, director, remarks, year, area, content, bofang)
        result = self.build_detail_result(videos)
        return result

    def get_first_id(self, ids):
        return ids[0]

    def build_detail_payload(self, did):
        return {"vod_id": did}

    def get_vod_info_url(self):
        return f'{xurl}/Pc/Resource/GetVodInfo'

    def send_post_request(self, url, payload):
        return requests.post(url=url, headers=headerx, json=payload)

    def get_response_json(self, response):
        return response.json()

    def build_vod_content(self, data):
        raw_content = data.get('data', {}).get('vodInfo', {}).get('vod_use_content', '').strip()
        if raw_content:
            return f"TAO为您介绍剧情📢{raw_content}"
        return "TAO为您介绍剧情📢暂无剧情介绍"

    def get_nested_value(self, data, key):
        return data.get('data', {}).get('vodInfo', {}).get(key, '')

    def build_remarks(self, data):
        remarks_list = data.get('data', {}).get('vodInfo', {}).get('videoTag', '')
        if isinstance(remarks_list, list):
            return ', '.join(remarks_list)
        return str(remarks_list)

    def build_playlist_payload(self, did):
        return {"vod_id": did,"pageSize": 2000,"page": 1}

    def get_playlist_url(self):
        return f'{xurl}/Pc/Resource/GetOnePlayList'

    def get_urls_list(self, datas):
        return datas.get('data', {}).get('urls')

    def build_play_string(self, urls_list):
        bofang = ''
        for sou in urls_list:
            id = sou['vurl_id']
            name = sou['name']
            bofang = bofang + name + '$' + str(id) + '#'
        return bofang[:-1]

    def build_video_info(self, did, director, remarks, year, area, content, bofang):
        return [{
            "vod_id": did,
            "vod_director": director,
            "vod_remarks": remarks,
            "vod_year": year,
            "vod_area": area,
            "vod_content": content,
            "vod_play_from": "TAO嗑瓜子",
            "vod_play_url": bofang
                }]

    def build_detail_result(self, videos):
        result = {}
        result['list'] = videos
        return result

    def playerContent(self, flag, id, vipFlags):
        payload = self.build_player_payload(id)
        urlz = self.get_player_url()
        response = self.send_player_request(urlz, payload)
        data = self.get_response_json(response)
        play_url = self.extract_play_url(data)
        result = self.build_player_result(play_url)
        return result

    def build_player_payload(self, id):
        return {"vurl_id": id}

    def get_player_url(self):
        return f'{xurl}/Pc/Resource/vurlDetail'

    def send_player_request(self, urlz, payload):
        return requests.post(url=urlz, headers=headerx, json=payload)

    def get_response_json(self, response):
        return response.json()

    def extract_play_url(self, data):
        play_url = ''
        video_list = data.get('data', [])
        target_resolutions = ['1080', '720']
        for resolution in target_resolutions:
            for item in video_list:
                if isinstance(item, dict) and item.get('resolution') == resolution:
                    play_url = item.get('url', '')
                    if play_url:
                        break
            if play_url:
                break
        if not play_url and video_list:
            play_url = video_list[0].get('url', '')
        return play_url

    def build_player_result(self, play_url):
        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = play_url
        result["header"] = headers
        return result

    def searchContentPage(self, key, quick, pg):
        videos = []
        page = self._get_page_number(pg)
        payload = self._build_payload(key, page)
        url = f'{xurl}/Pc/Search/GetConditionList'
        data = self._fetch_data(url, headerx, payload)
        for vod in data['data']['list']:
            video = self._parse_video_item(vod)
            videos.append(video)
        return self._build_result(videos, pg)

    def _get_page_number(self, pg):
        return int(pg) if pg else 1

    def _build_payload(self, key, page):
        return {"area": 0,"class": "","keywords": key,"lang": 0,"page": page,"pageSize": 10,"sort": "d_id","tid": 0,"year": 0}

    def _fetch_data(self, url, headers, payload):
        response = requests.post(url=url, headers=headers, json=payload)
        return response.json()

    def _parse_video_item(self, vod):
        return {
            "vod_id": vod['vod_id'],
            "vod_name": vod['vod_name'],
            "vod_pic": vod['vod_pic'],
            "vod_year": vod.get('vod_year', '暂无备注'),
            "vod_remarks": vod.get('new_continue', '') or vod.get('vod_scroe', '') or '暂无备注'
               }

    def _build_result(self, videos, pg):
        return {'list': videos,'page': pg,'pagecount': 9999,'limit': 90,'total': 999999}

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
