# coding=utf-8
# !/usr/bin/python

"""

作者 丢丢喵 内容均从互联网收集而来 仅供交流学习使用 严禁用于商业用途 请于24小时内删除
         ====================Diudiumiao====================

"""

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
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
import uuid
import json
import time
import sys
import re
import os

sys.path.append('..')

xurl = "https://sv.baidu.com"

headerx = {
    'User-Agent': 'Mozilla/5.0 (Linux; U; Android 8.0.0; zh-cn; Mi Note 2 Build/OPR1.170623.032) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/61.0.3163.128 Mobile Safari/537.36 XiaoMi/MiuiBrowser/10.1.1'
          }

ORIGINAL_FULL_URL_TEMPLATE = "https://sv.baidu.com/appui/api?cmd=video/commonlist&log=vhk&tn=1043677m&ctn=1043677m&blur=1&mac=&imei=AL5fB&cuid=B8B02D397EF5A5D8675FF92CDEDB833B%7C0&iid=A50-GZSWENRQHEZWMLJUHFSTALJUMYZDCLLBHEYWGLLCGZTDGNZQGBRGCOJQGE-OUABVLNI&c3_aid=A00-GGDKZORUQAP5GY6JC5BBPXTPVNC74IIA-V5QNYZSV&os=android&osbranch=a0&ua=900_1600_240&ut=V1938T_9_28_vivo&uh=vivo,qcom,V1938T&apiv=7.93.0.18&appv=793001&version=7.93.0.18&life=1773081846&clife=1773081846&nlife=1773081808&hid=empty&imsi=0&user_live_rec_source=yy,baijiahao,bjh_client,pc_client,bd_client&app_cpu_abi=64&device_prefer_abi=64&is_fold_screen=0&is_tablet=0&player_params=%7B%22ps%22:-1%7D&androidId=ec1280db12795506&zid=UW60kbyg6UiIf3uhVai1IDx_sCpGqcu19NSBuVuST5hB1Ho3bCpDReYbYo3zw3ZVdgFFLm7bHyMC7Kis_fOMAnA&network=1&sids=265_2-999990_2-999991_2-999989_2-999992_2-999988_2-999993_2-999999_72-123_2&young_mode=0&oaid=&honor_oaid=&nu=1&score=0.4330356&network5g=1&mpv=1&before_agree_sids=user_growth_15&fvt=1773081342&cp_isbg=0&is_playlet=1"

ORIGINAL_USER_AGENT_TEMPLATE = "Mozilla/5.0 (Linux; Android 9; V1938T Build/PQ3A.190705.08061357; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Safari/537.36 haokan/7.93.0.18 (Baidu; P1 9)/oviv_82_9_T8391V/1043677m/B8B02D397EF5A5D8675FF92CDEDB833B%7C0/1/7.93.0.18/793001/1/immersiveMode/modeV4PlusWhite/isFirstInstall/bbqMode/bbqModeV2/blackStyle/isPlaylet"

class Spider(Spider):

    def __init__(self):
        super().__init__()
        self.base_url_template = ORIGINAL_FULL_URL_TEMPLATE
        self.base_ua_template = ORIGINAL_USER_AGENT_TEMPLATE

    def getName(self):
        return "丢丢喵"

    def init(self, extend):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def homeVideoContent(self):
        pass

    def homeContent(self, filter):
        data = self._fetch_home_data()
        classes = self._parse_classes(data)
        self._add_extra_class(classes)
        return {"class": classes}

    def _fetch_home_data(self):
        payload = {"data": json.dumps({"from": "feed"})}
        urlz = f'{xurl}/haokan/ui-feed/playletShelfFeed'
        response = requests.post(url=urlz, headers=headerx, json=payload)
        return response.json()

    def _parse_classes(self, data):
        classes = []
        for vod in data['data']['playlet_tags']:
            classes.append({
                "type_id": vod['tag_id'],
                "type_name": "" + vod['name']
            })
        return classes

    def _add_extra_class(self, classes):
        classes.append({"type_id": 2, "type_name": "新剧"})

    def categoryContent(self, cid, pg, filter, ext):
        page = int(pg) if pg else 1
        payload = self._build_category_payload(cid, page)
        data = self._fetch_category_data(payload)
        videos = self._parse_category_videos(data)
        return self._format_category_result(videos, pg)

    def _build_category_payload(self, cid, page):
        return {"tag_id": cid,"pn": page,"rn": 9}

    def _fetch_category_data(self, payload):
        urlz = f'{xurl}/haokan/ui-feed/playletTagsFeed'
        response = requests.post(url=urlz, headers=headerx, data=payload)
        return response.json()

    def _parse_category_videos(self, data):
        videos = []
        for vod in data['data']['list']:
            videos.append({
                "vod_id": vod['playlet_id'],
                "vod_name": vod['playlet_title'],
                "vod_pic": vod['playlet_poster'],
                "vod_year": vod.get('hot_value', '暂无备注'),
                "vod_remarks": vod.get('episodes_num_text', '暂无备注')
            })
        return videos

    def _format_category_result(self, videos, pg):
        return {'list': videos,'page': pg,'pagecount': 9999,'limit': 90,'total': 999999}

    def generate_random_cuid(self, length=32):
        return uuid.uuid4().hex.upper()[:length] + "%7C0"

    def prepare_request_data(self, series_id, start_vid=""):
        query_params = self._get_base_query_params()
        self._update_dynamic_params(query_params)
        cleaned_url = self._build_cleaned_url(query_params)
        cleaned_user_agent = self._build_cleaned_user_agent()
        inner_params = self._build_inner_params(series_id, start_vid)
        payload_data = self._build_payload_data(inner_params)
        headers = self._build_headers(cleaned_url, cleaned_user_agent)
        return cleaned_url, payload_data, headers

    def _get_base_query_params(self):
        parsed_url = urlparse(self.base_url_template)
        return {k: v[0] for k, v in parse_qs(parsed_url.query, keep_blank_values=True).items()}

    def _update_dynamic_params(self, query_params):
        query_params['cuid'] = self.generate_random_cuid()
        query_params['androidId'] = uuid.uuid4().hex[:16]
        query_params['zid'] = uuid.uuid4().hex
        if query_params.get('imei'):
            query_params['imei'] = uuid.uuid4().hex[:15]
        if query_params.get('mac'):
            query_params['mac'] = ':'.join(['{:02x}'.format(uuid.uuid4().int >> i & 0xff) for i in range(6)])
        if 'iid' in query_params:
            query_params['iid'] = f"{uuid.uuid4().hex.upper()[:8]}-{uuid.uuid4().hex.upper()[:8]}-{uuid.uuid4().hex.upper()[:8]}-{uuid.uuid4().hex.upper()[:8]}-{uuid.uuid4().hex.upper()[:8]}"
        if 'c3_aid' in query_params:
            query_params['c3_aid'] = f"{uuid.uuid4().hex.upper()[:3]}-{uuid.uuid4().hex.upper()[:16]}-{uuid.uuid4().hex.upper()[:4]}-{uuid.uuid4().hex.upper()[:4]}-{uuid.uuid4().hex.upper()[:4]}-{uuid.uuid4().hex.upper()[:4]}"

    def _build_cleaned_url(self, query_params):
        parsed_url = urlparse(self.base_url_template)
        return urlunparse(parsed_url._replace(query=urlencode(query_params, doseq=True)))

    def _build_cleaned_user_agent(self):
        return re.sub(r'(/1043677m/)([\w%]+)(/\d+/\d+\.\d+\.\d+/\d+/)',r'\g<1>' + self.generate_random_cuid() + r'\g<3>', self.base_ua_template)

    def _build_inner_params(self, series_id, start_vid):
        current_timestamp = str(int(time.time() * 1000))
        return {
            "source_from": "kanju_shelf_playlet", "enable_enter_playlet": "0", "seek_time": "0", "hotspot": "0",
            "page_value": "playlet", "auto_show_hot_point_panel": "0", "type": "playlet",
            "commonlist_id": current_timestamp,
            "scene": "",
            "vid": start_vid,
            "enable_atlas": "0",
            "mark_pn": "", "uk": "", "ctime": "0", "from": "playlet_talos",
            "id": series_id,
            "rn": "10",
            "pn": "1",
            "direction": "3"
               }

    def _build_payload_data(self, inner_params):
        return {"video/commonlist": "&".join([f"{k}={v}" for k, v in inner_params.items()])}

    def _build_headers(self, cleaned_url, cleaned_user_agent):
        return {"Host": urlparse(cleaned_url).netloc,"User-Agent": cleaned_user_agent,"Content-Type": "application/x-www-form-urlencoded",}

    def get_all_series_episodes_by_vid_pagination(self, series_id, results_per_page=10):
        all_episodes = []
        added_vids = set()
        current_request_vid = ""
        while True:
            current_batch_episodes, has_more, last_vid = self._fetch_episode_batch(series_id, current_request_vid,results_per_page)
            if not current_batch_episodes:
                break
            newly_added = self._process_batch_episodes(current_batch_episodes, all_episodes, added_vids)
            if last_vid:
                current_request_vid = last_vid
            else:
                break
            if not has_more and newly_added == 0:
                break
            if len(current_batch_episodes) < results_per_page and not has_more:
                break
        return all_episodes

    def _fetch_episode_batch(self, series_id, start_vid, results_per_page):
        url, payload, headers = self.prepare_request_data(series_id, start_vid=start_vid)
        try:
            response = requests.post(url, data=payload, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            data_section = response_json.get('video/commonlist', {}).get('data', {})
            current_batch_episodes = data_section.get('list', data_section.get('results', []))
            has_more = data_section.get('has_more', 0) == 1
            last_vid = self._get_last_vid_in_batch(current_batch_episodes)
            return current_batch_episodes, has_more, last_vid
        except (requests.exceptions.RequestException, json.JSONDecodeError, Exception):
            return [], False, ""

    def _get_last_vid_in_batch(self, batch):
        if not batch:
            return ""
        last_vid = ""
        for episode in batch:
            vid = episode.get('content', {}).get('vid')
            if vid:
                last_vid = vid
        return last_vid

    def _process_batch_episodes(self, batch, all_episodes, added_vids):
        newly_added = 0
        for episode in batch:
            episode_vid = episode.get('content', {}).get('vid')
            if episode_vid and episode_vid not in added_vids:
                all_episodes.append(episode)
                added_vids.add(episode_vid)
                newly_added += 1
        return newly_added

    def detailContent(self, ids):
        did = ids[0]
        all_episodes = self.get_all_series_episodes_by_vid_pagination(did, results_per_page=10)
        bofang = self._build_bofang_string(all_episodes)
        videos = [self._build_video_item(did, bofang)]
        return {"list": videos}

    def _build_bofang_string(self, all_episodes):
        bofang = ""
        for video_data in all_episodes:
            if 'content' in video_data and 'title' in video_data['content']:
                name = video_data['content']['title']
                id = self._extract_video_id(video_data['content'].get('clarityUrl', []))
                bofang = bofang + name + "$" + id + "#"
        return bofang[:-1] if bofang else ""

    def _extract_video_id(self, clarity_urls):
        if len(clarity_urls) > 2:
            return clarity_urls[2]['url']
        if len(clarity_urls) > 1:
            return clarity_urls[1]['url']
        if len(clarity_urls) > 0:
            return clarity_urls[0]['url']
        return ''

    def _build_video_item(self, did, bofang):
        return {"vod_id": did,"vod_play_from": "好看专线","vod_play_url": bofang}

    def playerContent(self, flag, id, vipFlags):
        result = {}
        result["parse"] = 0
        result["playUrl"] = ''
        result["url"] = id
        result["header"] = headerx
        return result

    def searchContentPage(self, key, quick, pg):
        payload = self._build_search_payload(key)
        data = self._fetch_search_data(payload)
        videos = self._parse_search_videos(data)
        return self._format_search_result(videos, pg)

    def _build_search_payload(self, key):
        return {"search_word": key}

    def _fetch_search_data(self, payload):
        urlz = f'{xurl}/haokan/ui-interact/playlet/search/sugs'
        response = requests.post(url=urlz, headers=headerx, data=payload)
        return response.json()

    def _parse_search_videos(self, data):
        videos = []
        for vod in data['data']:
            videos.append({"vod_id": vod['id'],"vod_name": vod['title'],"vod_pic": vod['cover_url']})
        return videos

    def _format_search_result(self, videos, pg):
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








