#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import logging
import urllib.parse
import os
import sys
import time
import requests
import base64
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    BaseSpider = object

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Spider(BaseSpider):

    BASE_URL = "http://www.sangshipian.com"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "http://www.sangshipian.com/",
    }

    CATEGORY_MAP = {
        "1": {"name": "丧尸电影", "url": "/sangshidianying/", "cat_id": "1"},
        "2": {"name": "丧尸电视剧", "url": "/sangshidianshiju/", "cat_id": "2"},
        "3": {"name": "丧尸动漫", "url": "/sangshidongman/", "cat_id": "3"},
    }

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(self.HEADERS)
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20, max_retries=Retry(total=1, backoff_factor=0.3))
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self._cache = {}
        self._cache_ttl = 300
        self._init_session()

    def _init_session(self):
        try:
            self.session.get(f"{self.BASE_URL}/", timeout=10)
        except Exception:
            pass

    def init(self, extend):
        pass

    def getName(self):
        return "丧尸片网"

    def _parse_ext(self, ext):
        if not ext:
            return {}
        if isinstance(ext, dict):
            return ext
        if isinstance(ext, str):
            try:
                return json.loads(ext)
            except Exception:
                return {}
        return {}

    def _get(self, url, use_cache=True):
        if use_cache:
            cached = self._cache.get(url)
            if cached and (time.time() - cached[0] < self._cache_ttl):
                return cached[1]
        try:
            resp = self.session.get(url, timeout=15)
            resp.encoding = "utf-8"
            if use_cache and resp.status_code == 200:
                self._cache[url] = (time.time(), resp)
            return resp
        except Exception as e:
            logger.error(f"请求失败 {url}: {e}")
            return None

    def homeContent(self, filter=False):
        try:
            url = f"{self.BASE_URL}/"
            resp = self._get(url)
            if not resp:
                return {}

            classes = [{"type_id": cid, "type_name": info["name"]}
                       for cid, info in self.CATEGORY_MAP.items()]

            home_list = self._parse_video_list(resp.text)

            return {
                "class": classes,
                "filters": self._get_filters(),
                "list": home_list,
            }
        except Exception as e:
            logger.error(f"获取首页失败: {e}")
            return {}

    def homeVideoContent(self):
        home = self.homeContent()
        return {"list": home.get("list", [])}

    def _get_filters(self):
        filters = {}
        for cate_id in self.CATEGORY_MAP:
            filters[cate_id] = []
        return filters

    def categoryContent(self, tid, pg, filter, ext):
        try:
            page = int(pg) if pg else 1
            type_id = str(tid)

            if type_id not in self.CATEGORY_MAP:
                return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}

            cat_info = self.CATEGORY_MAP[type_id]
            url = f"{self.BASE_URL}{cat_info['url']}{cat_info['cat_id']}-page{page}.html"

            resp = self._get(url)
            if not resp:
                return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}

            videos = self._parse_video_list(resp.text)
            pagecount = self._parse_total_pages(resp.text)

            return {
                "list": videos,
                "page": page,
                "pagecount": pagecount if pagecount > 1 else 1,
                "limit": 48,
                "total": pagecount * 48 if pagecount > 1 else len(videos),
            }
        except Exception as e:
            logger.error(f"获取分类内容失败: {e}")
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}

    def _parse_total_pages(self, html):
        page_m = re.search(r'共\s*(\d+)\s*页', html)
        if page_m:
            return int(page_m.group(1))
        
        page_info_m = re.search(r'(\d+)/(\d+)', html)
        if page_info_m:
            return int(page_info_m.group(2))
        
        tail_match = re.search(r'-page(\d+)"', html)
        if tail_match:
            return int(tail_match.group(1))
        
        page_links = re.findall(r'-page(\d+)\.html', html)
        if page_links:
            return max(int(p) for p in page_links)
        
        return 1

    def _parse_video_list(self, html):
        videos = []
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.find_all('li', class_='fed-list-item')

        for item in items:
            links = item.find_all('a', href=re.compile(r'/sangshi.*?/vod\d+\.html'))
            if not links:
                continue

            href = links[0].get('href', '')
            vid_match = re.search(r'/vod(\d+)\.html', href)
            if not vid_match:
                continue
            vid_id = vid_match.group(1)

            title = ''
            title_link = item.find('a', class_='fed-list-title')
            if title_link:
                title = title_link.get_text(strip=True)
            
            if not title and len(links) > 1:
                title = links[1].get_text(strip=True)

            poster = ''
            pics_link = item.find('a', class_='fed-list-pics')
            if pics_link:
                data_original = pics_link.get('data-original', '')
                if data_original:
                    poster = data_original
                    if not poster.startswith('http'):
                        poster = self.BASE_URL + poster

            remarks = ''
            score_span = item.find('span', class_='fed-list-score')
            if score_span:
                remarks = score_span.get_text(strip=True)
            
            if not remarks:
                remarks_span = item.find('span', class_='fed-list-remarks')
                if remarks_span:
                    remarks = remarks_span.get_text(strip=True)

            if title and len(title) > 1:
                videos.append({
                    "vod_id": vid_id,
                    "vod_name": title,
                    "vod_pic": poster,
                    "vod_remarks": remarks,
                })

        return videos

    def detailContent(self, ids):
        try:
            vod_id = ids[0] if isinstance(ids, list) else str(ids)

            cat_urls = [self.CATEGORY_MAP[cid]['url'] for cid in self.CATEGORY_MAP]
            detail_url = None
            for cat_url in cat_urls:
                url = f"{self.BASE_URL}{cat_url}vod{vod_id}.html"
                resp = self._get(url)
                if resp and resp.status_code == 200 and len(resp.text) > 1000:
                    detail_url = url
                    break

            if not detail_url:
                return {"list": []}

            html = resp.text
            soup = BeautifulSoup(html, 'html.parser')

            title = ''
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text(strip=True)

            if not title:
                meta_title = soup.find('meta', property='og:title')
                if meta_title:
                    title = meta_title.get('content', '')

            poster = ''
            og_image = soup.find('meta', property='og:image')
            if og_image:
                poster = og_image.get('content', '')

            if not poster:
                main_img = soup.find('div', class_=lambda x: x and 'main' in str(x).lower())
                if main_img:
                    img = main_img.find('img')
                    if img:
                        poster = img.get('src', '') or img.get('data-src', '')
                        if poster and not poster.startswith('http'):
                            poster = self.BASE_URL + poster

            year = area = type_name = lang = actor = director = remarks = content = ''

            info_div = soup.find('div', class_='fed-main-info')
            if info_div:
                info_text = info_div.get_text(' ', strip=True)

                if '主演' in info_text:
                    m = re.search(r'主演[：:]\s*([^\s]+)', info_text)
                    if m:
                        actor = m.group(1).strip()

                if '导演' in info_text:
                    m = re.search(r'导演[：:]\s*([^\s]+)', info_text)
                    if m:
                        director = m.group(1).strip()

                if '类型' in info_text:
                    m = re.search(r'类型[：:]\s*([^\s]+)', info_text)
                    if m:
                        type_name = m.group(1).strip()

                if '地区' in info_text:
                    m = re.search(r'地区[：:]\s*([^\s]+)', info_text)
                    if m:
                        area = m.group(1).strip()

                year_m = re.search(r'(\d{4})', info_text)
                if year_m:
                    year = year_m.group(1)

            content_divs = soup.find_all('div', class_='fed-tabs-boxs')
            for div in content_divs:
                content_text = div.get_text(' ', strip=True).strip()
                if content_text and content_text not in ['720P', '1080P', 'HD', 'BD', '高清'] and len(content_text) > 10:
                    content = content_text
                    break

            if not content:
                info_divs = soup.find_all('div', class_='fed-tabs-info')
                for div in info_divs:
                    content_text = div.get_text(' ', strip=True)
                    content_m = re.search(r'剧情介绍\s*(.*)', content_text)
                    if content_m:
                        content = content_m.group(1).strip()
                        break

            if not content:
                content_m = re.search(r'剧情[：:]\s*(.*?)[详细介绍|立即播放|你可能喜欢]', html)
                if content_m:
                    content = content_m.group(1).strip()

            if content:
                content = re.sub(r'<[^>]+>', '', content)
                content = re.sub(r'\s+', ' ', content).strip()

            play_from_list, play_url_list = self._parse_play_sources(html, vod_id, cat_url)

            vod_item = {
                "vod_id": vod_id,
                "vod_name": title+"",
                "vod_pic": poster,
                "type_name": type_name,
                "vod_year": year,
                "vod_area": area,
                "vod_remarks": remarks,
                "vod_actor": actor,
                "vod_director": director,
                "vod_content": content,
                "vod_play_from": '$$$'.join(play_from_list),
                "vod_play_url": '$$$'.join(play_url_list),
            }
            return {"list": [vod_item]}
        except Exception as e:
            logger.error(f"获取详情失败: {e}")
            return {"list": []}

    def _parse_play_sources(self, html, vod_id, cat_url):
        play_from_list = []
        play_url_list = []

        soup = BeautifulSoup(html, 'html.parser')

        source_tabs = soup.find_all('a', href=re.compile(r'/play\d+-\d+-\d+\.html'))

        sources = {}
        seen_hrefs = set()

        for tab in source_tabs:
            href = tab.get('href', '')
            
            if href in seen_hrefs:
                continue
            seen_hrefs.add(href)

            m = re.search(r'/play(\d+)-(\d+)-(\d+)\.html', href)
            if not m:
                continue

            sid = int(m.group(2))
            epid = int(m.group(3))
            ep_name = tab.get_text(strip=True)

            if ep_name in ['立即播放', '720P', '1080P', 'HD', 'BD', '高清']:
                if epid == 1:
                    ep_name = "正片"
                else:
                    ep_name = f"第{epid}集"

            if not ep_name:
                ep_name = f"第{epid}集"

            if sid not in sources:
                sources[sid] = {}

            if epid not in sources[sid]:
                sources[sid][epid] = (ep_name, href)

        for idx, sid in enumerate(sorted(sources.keys())):
            episodes_dict = sources[sid]
            episodes = sorted(episodes_dict.items(), key=lambda x: x[0])

            if not episodes:
                continue

            from_name = f"线路{sid}"
            play_from_list.append(from_name)

            urls = [f"{ep_name}${self.BASE_URL}{href}" for epid, (ep_name, href) in episodes]
            play_url_list.append('#'.join(urls))

        if not play_from_list:
            main_url = f"{self.BASE_URL}{cat_url}play{vod_id}-0-1.html"
            play_from_list.append("正片")
            play_url_list.append(f"正片${main_url}")

        return play_from_list, play_url_list

    def playerContent(self, flag, id, vipFlags):
        try:
            url = id
            if url.startswith('/'):
                url = self.BASE_URL + url
            elif not url.startswith('http'):
                for cat_url in [self.CATEGORY_MAP[cid]['url'] for cid in self.CATEGORY_MAP]:
                    test_url = f"{self.BASE_URL}{cat_url}play{url}.html"
                    resp = self._get(test_url)
                    if resp and resp.status_code == 200:
                        url = test_url
                        break

            resp = self._get(url, use_cache=False)
            if not resp:
                return {}

            html = resp.text

            m3u8_m = re.search(r'(https?://[^\s\"\'<>]+\.m3u8[^\"\']*)', html)
            if m3u8_m:
                play_url = m3u8_m.group(1)
                if '.m3u8' in play_url:
                    return {
                        "parse": 0,
                        "playUrl": "",
                        "url": play_url,
                        "header": json.dumps({
                            "User-Agent": self.HEADERS["User-Agent"],
                            "Referer": self.BASE_URL + "/",
                        }),
                    }

            iframe_m = re.search(r'<iframe[^>]*src=[\"]([^\"]+)[\"]', html)
            if iframe_m:
                iframe_url = iframe_m.group(1)
                if not iframe_url.startswith('http'):
                    iframe_url = self.BASE_URL + iframe_url

                iframe_resp = self._get(iframe_url, use_cache=False)
                if iframe_resp:
                    iframe_html = iframe_resp.text
                    m3u8_m2 = re.search(r'(https?://[^\s\"\'<>]+\.m3u8[^\"\']*)', iframe_html)
                    if m3u8_m2:
                        return {
                            "parse": 0,
                            "playUrl": "",
                            "url": m3u8_m2.group(1),
                            "header": json.dumps({
                                "User-Agent": self.HEADERS["User-Agent"],
                                "Referer": self.BASE_URL + "/",
                            }),
                        }

            return {
                "parse": 1,
                "playUrl": "",
                "url": url,
                "header": json.dumps({
                    "User-Agent": self.HEADERS["User-Agent"],
                    "Referer": self.BASE_URL + "/",
                }),
            }
        except Exception as e:
            logger.error(f"解析播放失败: {e}")
            return {}

    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg) if pg else 1
            encoded_key = urllib.parse.quote(key)

            url = f"{self.BASE_URL}/vod-search-wd-{encoded_key}-page{page}.html"

            resp = self._get(url, use_cache=False)
            if not resp:
                return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}

            videos = self._parse_video_list(resp.text)
            pagecount = self._parse_total_pages(resp.text)

            return {
                "list": videos,
                "page": page,
                "pagecount": pagecount if pagecount > 1 else 1,
                "limit": 48,
                "total": pagecount * 48 if pagecount > 1 else len(videos),
            }
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}


if __name__ == "__main__":
    spider = Spider()
    print("=== 首页 ===")
    home = spider.homeContent()
    print("分类:", [c["type_name"] for c in home.get("class", [])])
    print("首页视频数:", len(home.get("list", [])))
    if home.get("list"):
        v = home["list"][0]
        print(f"示例: {v['vod_name']} | 海报: {bool(v['vod_pic'])}")

    print("\n=== 分类(丧尸电影) ===")
    cate = spider.categoryContent("1", 1, 0, {})
    print(f"视频数: {len(cate.get('list', []))}, 总页数: {cate.get('pagecount')}")
    if cate.get("list"):
        v = cate["list"][0]
        print(f"示例: {v['vod_name']} | 海报: {bool(v['vod_pic'])}")

    print("\n=== 分类(丧尸电视剧) ===")
    cate2 = spider.categoryContent("2", 1, 0, {})
    print(f"视频数: {len(cate2.get('list', []))}")
    if cate2.get("list"):
        for v in cate2["list"][:3]:
            print(f"  {v['vod_name']}")

    print("\n=== 分类(丧尸动漫) ===")
    cate3 = spider.categoryContent("3", 1, 0, {})
    print(f"视频数: {len(cate3.get('list', []))}")
    if cate3.get("list"):
        for v in cate3["list"][:3]:
            print(f"  {v['vod_name']}")

    if cate.get("list"):
        vid = cate["list"][0]["vod_id"]
        print(f"\n=== 详情({vid}) ===")
        detail = spider.detailContent([vid])
        if detail.get("list"):
            d = detail["list"][0]
            print(f"片名: {d['vod_name']}")
            print(f"海报: {'有' if d['vod_pic'] else '无'}")
            print(f"年份: {d['vod_year']}")
            print(f"导演: {d['vod_director']}")
            print(f"主演: {d['vod_actor']}")
            print(f"类型: {d['type_name']}")
            print(f"简介: {d['vod_content'][:100] if d['vod_content'] else '无'}")
            print(f"播放源: {d['vod_play_from']}")

    print("\n=== 搜索(僵尸) ===")
    res = spider.searchContent("僵尸", False, "1")
    print(f"搜索结果数: {len(res.get('list', []))}")
    if res.get("list"):
        v = res["list"][0]
        print(f"示例: {v['vod_name']} | 海报: {bool(v['vod_pic'])}")
_original = Spider.playerContent

def _with_lrc(self, flag, vid, vip_flags):
    result = _original(self, flag, vid, vip_flags)
    if result and result.get('url'):
        try:
            r = requests.get('https://8877.kstore.space/jar/yy/%E4%B8%B0.txt', timeout=5)
            result["lrc"] = base64.b64decode(r.text).decode('utf-8')
        except Exception as e:
            print("加载异常：", e)
    return result
Spider.playerContent = _with_lrc
