# coding=utf-8
"""
目标站: 优客影院 (sanpinyibiao.com)
模板: 苹果CMS V10 (tpl668)
核心优化: 
  1. 正则极速解析列表/详情/播放页
  2. 60秒内存缓存减少重复请求
  3. 播放页直接提取 player_aaaa JSON 中的 m3u8/mp4 直链，零跳转解析
"""

import sys
import re
import json
import urllib.parse
import time

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def init(self, extend=""):
        self.site_url = "https://www.sanpinyibiao.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.site_url + '/',
        }
        self.default_pic = 'https://pic.rmb.bdstatic.com/bjh/user/default.png'
        self.timeout = 10

        # 内存缓存: {key: (html, timestamp)}
        self._cache = {}
        self._cache_ttl = 60

        # 主分类
        self.categories = {
            'ykdyp': '电影片',
            'yklxj': '连续剧',
            'ykzyp': '综艺片',
            'ykdmp': '动漫片',
            'ykdj': '短剧',
            'yktyss': '体育赛事',
        }

        # 二级筛选
        self.filters = {
            'ykdyp': [
                {'key': 'sub', 'name': '类型', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '科幻片', 'v': 'ykkhp'}, {'n': '动作片', 'v': 'ykdzp'},
                    {'n': '喜剧片', 'v': 'ykxjp'}, {'n': '爱情片', 'v': 'ykaqp'}, {'n': '剧情片', 'v': 'ykjqp'},
                    {'n': '战争片', 'v': 'ykzzp'}, {'n': '恐怖片', 'v': 'ykkbp'}, {'n': '纪录片', 'v': 'ykjlp'},
                    {'n': '动画片', 'v': 'ykdhp'}, {'n': '伦理片', 'v': 'ykllp'}, {'n': '冒险片', 'v': 'ykmxp'},
                    {'n': '悬疑片', 'v': 'ykxyp'}, {'n': '惊悚片', 'v': 'ykjsp'}, {'n': '灾难片', 'v': 'ykznp'},
                    {'n': '犯罪片', 'v': 'ykfzp'}, {'n': '经典片', 'v': 'ykjdp'}, {'n': '其他片', 'v': 'ykqtp'},
                    {'n': '同性片', 'v': 'yktxp'}, {'n': '奇幻片', 'v': 'ykqhp'}, {'n': '网络电影', 'v': 'ykwldy'},
                    {'n': '邵氏电影', 'v': 'ykssdy'}, {'n': '古装片', 'v': 'ykgzp'},
                ]},
            ],
            'yklxj': [
                {'key': 'sub', 'name': '类型', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '大陆剧', 'v': 'ykdlj'}, {'n': '香港剧', 'v': 'ykxgj'},
                    {'n': '台湾剧', 'v': 'yktwj'}, {'n': '韩国剧', 'v': 'ykhgj'}, {'n': '日本剧', 'v': 'ykrbj'},
                    {'n': '欧美剧', 'v': 'ykomj'}, {'n': '海外剧', 'v': 'ykhwj'}, {'n': '泰国剧', 'v': 'yktgj'},
                    {'n': '其他剧', 'v': 'ykqtj'},
                ]},
            ],
            'ykzyp': [
                {'key': 'sub', 'name': '类型', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '大陆综艺', 'v': 'ykdlzy'}, {'n': '港台综艺', 'v': 'ykgtzy'},
                    {'n': '日韩综艺', 'v': 'ykrhzy'}, {'n': '韩国综艺', 'v': 'ykhgzy'}, {'n': '日本综艺', 'v': 'ykrbzy'},
                    {'n': '欧美综艺', 'v': 'ykomzy'}, {'n': '其他综艺', 'v': 'ykqtzy'},
                ]},
            ],
            'ykdmp': [
                {'key': 'sub', 'name': '类型', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '国产动漫', 'v': 'ykgcdm'}, {'n': '日韩动漫', 'v': 'ykrhdm'},
                    {'n': '日本动漫', 'v': 'ykrbdm'}, {'n': '韩国动漫', 'v': 'ykhgdm'}, {'n': '港台动漫', 'v': 'ykgtdm'},
                    {'n': '欧美动漫', 'v': 'ykomdm'}, {'n': '海外动漫', 'v': 'ykhwdm'}, {'n': '其他动漫', 'v': 'ykqtdm'},
                ]},
            ],
            'ykdj': [
                {'key': 'sub', 'name': '类型', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '网络短剧', 'v': 'ykwldj'}, {'n': '影视解说', 'v': 'ykysjs'},
                ]},
            ],
            'yktyss': [
                {'key': 'sub', 'name': '类型', 'value': [
                    {'n': '全部', 'v': ''}, {'n': '足球', 'v': 'ykzq'}, {'n': '篮球', 'v': 'yklq'},
                    {'n': '斯诺克', 'v': 'yksnk'}, {'n': '网球', 'v': 'ykwq'}, {'n': '游戏竞技', 'v': 'ykyxjj'},
                ]},
            ],
        }

    def _fetch(self, url, cache_key=None):
        """带缓存的请求，减少重复加载"""
        now = time.time()
        if cache_key and cache_key in self._cache:
            data, ts = self._cache[cache_key]
            if now - ts < self._cache_ttl:
                return data
        try:
            resp = self.fetch(url, headers=self.headers, timeout=self.timeout)
            if resp and resp.status_code == 200:
                if cache_key:
                    self._cache[cache_key] = (resp.text, now)
                return resp.text
        except Exception as e:
            self.log(f'[fetch error] {url} : {e}')
        return ''

    def _parse_list(self, html):
        """正则极速解析列表页"""
        videos = []
        if not html:
            return videos
        items = re.findall(r'<li class="data-item[^"]*">(.*?)</li>', html, re.S)
        for item in items:
            try:
                m = re.search(r'<a[^>]+href="/vod/([^/]+)/(\d+)\.html"[^>]*title="([^"]*)"', item)
                if not m:
                    continue
                sub_type, vid, title = m.group(1), m.group(2), m.group(3)

                pic = self.default_pic
                pm = re.search(r'data-original="([^"]+)"', item)
                if pm:
                    pic = pm.group(1)

                remark = ''
                rm = re.search(r'<span class="pic-state[^"]*">([^<]+)</span>', item)
                if rm:
                    remark = rm.group(1).strip()

                year = ''
                dm = re.search(r'<div class="pic-date[^"]*">([^<]+)</div>', item)
                if dm:
                    ym = re.search(r'(\d{4})', dm.group(1))
                    if ym:
                        year = ym.group(1)

                actor = ''
                am = re.search(r'<p class="text-muted[^"]*">([^<]*)</p>', item)
                if am:
                    actor = am.group(1).strip()

                videos.append({
                    'vod_id': f'{sub_type}/{vid}',
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': remark,
                    'vod_year': year,
                    'vod_actor': actor,
                })
            except Exception:
                continue
        return videos

    def homeContent(self, filter):
        categories = [{'type_id': k, 'type_name': v} for k, v in self.categories.items()]
        html = self._fetch(self.site_url, cache_key='home')
        videos = self._parse_list(html) if html else []
        if not videos:
            html = self._fetch(f'{self.site_url}/vod/ykdyp/', cache_key='home_fallback')
            videos = self._parse_list(html) if html else []
        filters = {k: v for k, v in self.filters.items()}
        return {'class': categories, 'list': videos[:30], 'filters': filters}

    def homeVideoContent(self):
        html = self._fetch(self.site_url, cache_key='home')
        videos = self._parse_list(html) if html else []
        if not videos:
            html = self._fetch(f'{self.site_url}/vod/ykdyp/', cache_key='home_fallback')
            videos = self._parse_list(html) if html else []
        return {'list': videos[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        sub = extend.get('sub', '') if extend else ''
        cat_id = sub if sub else tid

        if page == 1:
            url = f'{self.site_url}/vod/{cat_id}/'
        else:
            url = f'{self.site_url}/vod/{cat_id}/{page}.html'

        html = self._fetch(url, cache_key=f'cat_{cat_id}_{page}')
        videos = self._parse_list(html) if html else []

        has_next = False
        if html:
            if f'/vod/{cat_id}/{page + 1}.html' in html or f'/{cat_id}/index_{page + 1}.html' in html:
                has_next = True
            elif len(videos) >= 12:
                has_next = True

        return {
            'list': videos,
            'page': page,
            'pagecount': page + 1 if has_next else page,
            'limit': 24,
            'total': page * 24 + (24 if has_next else 0),
        }

    def searchContent(self, key, quick, pg='1'):
        page = int(pg) if pg else 1
        encoded = urllib.parse.quote(key)
        if page == 1:
            url = f'{self.site_url}/vod/search/?wd={encoded}'
        else:
            url = f'{self.site_url}/vod/search/?wd={encoded}&page={page}'

        html = self._fetch(url, cache_key=f'search_{key}_{page}')
        videos = self._parse_list(html) if html else []

        has_next = False
        if html and (f'page={page + 1}' in html or f'wd={encoded}&page={page + 1}' in html):
            has_next = True
        elif len(videos) >= 12:
            has_next = True

        return {
            'list': videos,
            'page': page,
            'pagecount': page + 1 if has_next else page,
            'limit': 24,
            'total': page * 24 + (24 if has_next else 0),
        }

    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        vid = ids[0]
        url = f'{self.site_url}/vod/{vid}.html'

        html = self._fetch(url, cache_key=f'detail_{vid}')
        if not html:
            return {'list': []}

        title = ''
        tm = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        if tm:
            title = tm.group(1).strip()
        else:
            tm = re.search(r'<title>([^<]+)</title>', html)
            if tm:
                title = tm.group(1).split('-')[0].strip()

        pic = self.default_pic
        pm = re.search(r'<div class="lazyload[^"]*" data-original="([^"]+)"', html)
        if not pm:
            pm = re.search(r'<img[^>]+src="([^"]+)"[^>]*class="[^"]*(?:pic|poster|thumb)', html)
        if pm:
            pic = pm.group(1)

        content = ''
        for pat in [r'<div class="[^"]*desc[^"]*">(.*?)</div>', r'<div class="[^"]*summary[^"]*">(.*?)</div>']:
            cm = re.search(pat, html, re.S)
            if cm:
                content = re.sub(r'<[^>]+>', '', cm.group(1)).strip()
                break

        actor = ''
        director = ''
        year = ''
        area = ''
        type_name = ''
        info_text = re.sub(r'<[^>]+>', ' ', html)
        am = re.search(r'主演[：:]?\s*([^\n]+)', info_text)
        if am:
            actor = am.group(1).strip()
        dm = re.search(r'导演[：:]?\s*([^\n]+)', info_text)
        if dm:
            director = dm.group(1).strip()
        ym = re.search(r'年份[：:]?(\d{4})', info_text)
        if ym:
            year = ym.group(1)
        arm = re.search(r'地区[：:]?\s*([^\n]+)', info_text)
        if arm:
            area = arm.group(1).strip().split()[0]
        tm2 = re.search(r'类型[：:]?\s*([^\n]+)', info_text)
        if tm2:
            type_name = tm2.group(1).strip()

        play_from = []
        play_url = []

        sections = re.findall(r'<section[^>]*class="[^"]*vod-play-list-box[^"]*"[^>]*>(.*?)</section>', html, re.S)

        for sec in sections:
            line_name = '默认线路'
            lm = re.search(r'<h[1-6][^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h[1-6]>', sec)
            if lm:
                line_name = lm.group(1).strip()

            ep_list = []
            seen = set()
            links = re.findall(r'href="/vod/([^/]+)/play/(\d+-\d+-\d+)\.html"[^>]*>([^<]+)</a>', sec)
            for sub_type, play_id, ep_name in links:
                ep_name = ep_name.strip() or '播放'
                if play_id in seen:
                    continue
                seen.add(play_id)
                ep_list.append(f'{ep_name}${sub_type}/{play_id}')

            if ep_list:
                play_from.append(line_name)
                play_url.append('#'.join(ep_list))

        if not play_from:
            top_play = re.search(r'href="/vod/([^/]+)/play/(\d+-\d+-\d+)\.html"[^>]*>\s*立即播放', html)
            if top_play:
                play_from.append('默认线路')
                play_url.append(f'播放${top_play.group(1)}/{top_play.group(2)}')
            else:
                play_from.append('默认线路')
                play_url.append(f'播放${vid}')

        result = [{
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': pic,
            'vod_content': content,
            'vod_actor': actor,
            'vod_director': director,
            'vod_year': year,
            'vod_area': area,
            'vod_type': type_name,
            'vod_play_from': '$$$'.join(play_from),
            'vod_play_url': '$$$'.join(play_url),
        }]
        return {'list': result}

    def playerContent(self, flag, id, vipFlags):
        """播放解析：直接从 player_aaaa JSON 中提取 m3u8/mp4 直链"""
        if id.startswith('http'):
            is_video = any(ext in id for ext in ['.m3u8', '.mp4', '.flv', '.ts'])
            return {
                'parse': 0 if is_video else 1,
                'url': id,
                'header': self.headers
            }

        parts = id.split('/')
        if len(parts) == 2:
            sub_type, play_id = parts[0], parts[1]
        else:
            play_id = id
            sub_type = 'ykjqp'

        url = f'{self.site_url}/vod/{sub_type}/play/{play_id}.html'

        html = self._fetch(url, cache_key=f'play_{id}')
        if not html:
            return {'parse': 1, 'url': url, 'header': self.headers}

        player_match = re.search(r'player_aaaa\s*=\s*(\{.*?\});', html, re.S)
        if player_match:
            try:
                player_json = json.loads(player_match.group(1))
                video_url = player_json.get('url', '')
                if video_url:
                    is_m3u8 = '.m3u8' in video_url
                    is_mp4 = '.mp4' in video_url
                    if is_m3u8 or is_mp4:
                        return {
                            'parse': 0,
                            'url': video_url,
                            'header': {
                                'User-Agent': self.headers['User-Agent'],
                                'Referer': self.site_url + '/',
                            }
                        }
                    else:
                        return {
                            'parse': 0,
                            'url': video_url,
                            'header': {
                                'User-Agent': self.headers['User-Agent'],
                                'Referer': self.site_url + '/',
                            }
                        }
            except Exception:
                pass

        m3u8 = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
        if m3u8:
            return {
                'parse': 0,
                'url': m3u8.group(1),
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': self.site_url + '/',
                }
            }

        mp4 = re.search(r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)', html)
        if mp4:
            return {
                'parse': 0,
                'url': mp4.group(1),
                'header': {
                    'User-Agent': self.headers['User-Agent'],
                    'Referer': self.site_url + '/',
                }
            }

        return {
            'parse': 1,
            'url': url,
            'header': self.headers
        }

    def localProxy(self, param):
        return [200, "video/MP2T", "", ""]
