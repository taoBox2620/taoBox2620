# -*- coding: utf-8 -*-
"""
图图影院 Python Spider — https://www.soocen.com
maccms v10 模板(tpl_15)

URL 规律:
  首页   : /
  分类   : /vodtype/<type_id>.html  或  /vodtype/<type_id>/page/<pg>.html
  筛选   : /vodshow/<type_id>--<class>------<pg>.html  (maccms标准8参数格式)
  详情   : /ttvod/<id>.html
  播放   : /ttplay/<id>-<sid>-<nid>.html
  搜索   : /search.html?wd=<关键词>&page=<pg>
"""

import sys
import re
import json
from urllib.parse import quote, urljoin

sys.path.append('..')

# ============================================================
# 基础 Spider 兜底
# ============================================================
try:
    from base.spider import Spider
except ImportError:
    try:
        import requests as _rq
        try:
            import urllib3
            urllib3.disable_warnings()
        except Exception:
            pass

        class Spider:
            def fetch(self, url, headers=None, **kw):
                timeout = kw.pop('timeout', 15)
                r = _rq.get(url, headers=headers, timeout=timeout, verify=False, **kw)
                r.encoding = 'utf-8'
                return r
    except ImportError:
        import urllib.request as _ur

        class _Resp:
            def __init__(self, raw):
                self.text = raw.decode('utf-8', errors='ignore')
                self.encoding = 'utf-8'

        class Spider:
            def fetch(self, url, headers=None, **kw):
                timeout = kw.pop('timeout', 15)
                req = _ur.Request(url, headers=headers or {})
                return _Resp(_ur.urlopen(req, timeout=timeout).read())


# ============================================================
# 常量
# ============================================================
HOST = "https://www.soocen.com"
UA = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"

CLASSES = [
    {"type_name": "电影",     "type_id": "QLLLLQ"},
    {"type_name": "连续剧", "type_id": "RLLLLQ"},
    {"type_name": "综艺",   "type_id": "ULLLLQ"},
    {"type_name": "动漫",   "type_id": "4LLLLQ"},
    {"type_name": "短剧",   "type_id": "bLLLLQ"},
]

FILTERS = {
    "QLLLLQ": [{"key": "class", "name": "分类", "value": [
        {"n": "全部",   "v": ""},
        {"n": "动作片", "v": "动作片"},
        {"n": "喜剧片", "v": "喜剧片"},
        {"n": "爱情片", "v": "爱情片"},
        {"n": "科幻片", "v": "科幻片"},
        {"n": "恐怖片", "v": "恐怖片"},
        {"n": "剧情片", "v": "剧情片"},
        {"n": "战争片", "v": "战争片"},
        {"n": "动画片", "v": "动画片"},
        {"n": "纪录片", "v": "纪录片"},
        {"n": "悬疑片", "v": "悬疑片"},
        {"n": "奇幻片", "v": "奇幻片"},
    ]}],
    "RLLLLQ": [{"key": "class", "name": "分类", "value": [
        {"n": "全部",   "v": ""},
        {"n": "国产剧", "v": "国产剧"},
        {"n": "港台剧", "v": "港台剧"},
        {"n": "日韩剧", "v": "日韩剧"},
        {"n": "欧美剧", "v": "欧美剧"},
        {"n": "海外剧", "v": "海外剧"},
    ]}],
    "ULLLLQ": [{"key": "class", "name": "分类", "value": [
        {"n": "全部",     "v": ""},
        {"n": "大陆综艺", "v": "大陆综艺"},
        {"n": "港台综艺", "v": "港台综艺"},
        {"n": "日韩综艺", "v": "日韩综艺"},
        {"n": "欧美综艺", "v": "欧美综艺"},
    ]}],
    "4LLLLQ": [{"key": "class", "name": "分类", "value": [
        {"n": "全部",     "v": ""},
        {"n": "国产动漫", "v": "国产动漫"},
        {"n": "日韩动漫", "v": "日韩动漫"},
        {"n": "欧美动漫", "v": "欧美动漫"},
        {"n": "港台动漫", "v": "港台动漫"},
    ]}],
    "bLLLLQ": [{"key": "class", "name": "分类", "value": [
        {"n": "全部",     "v": ""},
        {"n": "古装短剧", "v": "古装短剧"},
        {"n": "现代短剧", "v": "现代短剧"},
        {"n": "悬疑短剧", "v": "悬疑短剧"},
        {"n": "甜宠短剧", "v": "甜宠短剧"},
    ]}],
}

SEARCH_PAGE_SIZE = 20


# ============================================================
# Spider 主类
# ============================================================
class Spider(Spider):

    def getName(self):
        return "图图影院"

    def init(self, extend=""):
        self.header = {
            "User-Agent": UA,
            "Referer": HOST + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self._session = None

    def _get_session(self):
        if self._session is None:
            try:
                import requests
                self._session = requests.Session()
                self._session.headers.update(self.header)
                self._session.verify = False
                try:
                    import urllib3
                    urllib3.disable_warnings()
                except Exception:
                    pass
            except Exception:
                self._session = False
        return self._session

    def isVideoFormat(self, url):
        u = (url or "").lower()
        return any(ext in u for ext in [".m3u8", ".mp4", ".flv", ".ts"])

    def _get_html(self, url, timeout=12):
        try:
            sess = self._get_session()
            if sess:
                r = sess.get(url, timeout=timeout)
                r.encoding = 'utf-8'
                return r.text
            else:
                rsp = self.fetch(url, headers=self.header, timeout=timeout)
                return rsp.text if rsp else ""
        except Exception as e:
            print(f"[图图影院] 请求失败 {url}: {e}")
            return ""

    def _abs_url(self, url):
        if not url:
            return ""
        if url.startswith('//'):
            return "https:" + url
        if url.startswith('/'):
            return HOST + url
        if not url.startswith('http'):
            return urljoin(HOST + '/', url)
        return url

    @staticmethod
    def _strip(txt):
        return re.sub(r'\s+', ' ', (txt or '')).strip()

    # ===== 通用影片卡片解析(首页/分类页) =====
    def _parse_vod_list(self, html):
        items = []
        # 方式1: data-original (懒加载)
        for m in re.finditer(
            r'<a\b[^>]*href="(/ttvod/(\d+)\.html)"[^>]*title="([^"]*)"[^>]*data-original="([^"]*)"[^>]*>'
            r'[\s\S]*?'
            r'<span\b[^>]*class="[^"]*note[^"]*"[^>]*>([^<]*)</span>',
            html,
        ):
            items.append({
                "vod_id": m.group(2),
                "vod_name": self._strip(m.group(3)),
                "vod_pic": self._abs_url(m.group(4).strip()),
                "vod_remarks": self._strip(m.group(5)),
            })

        # 方式2: src (非懒加载，备用)
        if not items:
            for m in re.finditer(
                r'<a\b[^>]*href="(/ttvod/(\d+)\.html)"[^>]*title="([^"]*)"[^>]*>'
                r'[\s\S]*?'
                r'<img\b[^>]*src="([^"]*)"[^>]*>'
                r'[\s\S]*?'
                r'<span\b[^>]*class="[^"]*note[^"]*"[^>]*>([^<]*)</span>',
                html,
            ):
                items.append({
                    "vod_id": m.group(2),
                    "vod_name": self._strip(m.group(3)),
                    "vod_pic": self._abs_url(m.group(4).strip()),
                    "vod_remarks": self._strip(m.group(5)),
                })

        seen, uniq = set(), []
        for it in items:
            if it['vod_id'] in seen:
                continue
            seen.add(it['vod_id'])
            uniq.append(it)
        return uniq

    # ===== 首页 =====
    def homeContent(self, filter):
        result = {"class": CLASSES}
        if filter:
            result["filters"] = FILTERS
        return result

    def homeVideoContent(self):
        html = self._get_html(HOST + "/", timeout=10)
        if not html:
            return {"list": []}
        items = self._parse_vod_list(html)
        return {"list": items[:30]}

    # ===== 分类列表(支持二级分类 + 分页) =====
    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
            if page < 1:
                page = 1

            sub_class = ""
            if extend and isinstance(extend, dict):
                sub_class = extend.get('class', '')

            # maccms v10 筛选URL标准格式:
            # /vodshow/<id>-<area>-<class>-<year>-<letter>-<order>-<by>-<page>.html
            # 空参数留空，共8个参数位置
            if sub_class:
                # 格式1: 标准8参数，去掉末尾空参数
                parts = [tid, "", sub_class, "", "", "", "", str(page) if page > 1 else ""]
                while len(parts) > 1 and parts[-1] == "":
                    parts.pop()
                url = f"{HOST}/vodshow/{ '-'.join(parts) }.html"
            else:
                if page == 1:
                    url = f"{HOST}/vodtype/{tid}.html"
                else:
                    url = f"{HOST}/vodtype/{tid}/page/{page}.html"

            html = self._get_html(url, timeout=12)
            videos = self._parse_vod_list(html) if html else []

            # 如果筛选URL无数据，尝试备选格式(保留8个分隔符)
            if sub_class and not videos:
                if page == 1:
                    url2 = f"{HOST}/vodshow/{tid}--{sub_class}--------.html"
                else:
                    url2 = f"{HOST}/vodshow/{tid}--{sub_class}--------{page}.html"
                html2 = self._get_html(url2, timeout=12)
                if html2:
                    videos = self._parse_vod_list(html2)
                    html = html2

            # 如果还是无数据，回退到普通分类页
            if sub_class and not videos:
                if page == 1:
                    url3 = f"{HOST}/vodtype/{tid}.html"
                else:
                    url3 = f"{HOST}/vodtype/{tid}/page/{page}.html"
                html3 = self._get_html(url3, timeout=12)
                if html3:
                    videos = self._parse_vod_list(html3)
                    html = html3

            # 解析总页数
            pagecount = page
            for pm in re.finditer(r'href="[^"]*(?:/vodtype/[^"/]+/page/|/vodshow/[^"]+?)(\d+)\.html"', html or ""):
                n = int(pm.group(1))
                if n > pagecount:
                    pagecount = n
            if not videos and page > 1:
                pagecount = max(1, page - 1)

            return {
                "list": videos,
                "page": page,
                "pagecount": pagecount,
                "limit": len(videos) or 20,
                "total": pagecount * 20,
            }
        except Exception as e:
            print(f"[图图影院] categoryContent 异常: {e}")
            return self._empty_page(int(pg or 1))

    def _empty_page(self, page):
        return {"page": page, "pagecount": 1, "limit": 20, "total": 0, "list": []}

    # ===== 详情页 =====
    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)):
            ids = ids[0]
        vod_id = str(ids)

        url = f"{HOST}/ttvod/{vod_id}.html"
        html = self._get_html(url, timeout=12)
        if not html:
            return {"list": []}

        try:
            vod = {
                "vod_id": vod_id,
                "vod_name": "",
                "vod_pic": "",
                "vod_year": "",
                "vod_area": "",
                "vod_remarks": "",
                "vod_actor": "",
                "vod_director": "",
                "vod_class": "",
                "vod_content": "",
                "vod_play_from": "",
                "vod_play_url": "",
            }

            # 标题
            m = re.search(r'<h[12][^>]*>([^<]+)</h[12]>', html)
            if m:
                vod["vod_name"] = self._strip(m.group(1))

            # 封面
            m = re.search(r'<img[^>]+class="[^"]*poster[^"]*"[^>]+src="([^"]+)"', html) or \
                re.search(r'<img[^>]+src="([^"]+)"[^>]+class="[^"]*poster[^"]*"', html) or \
                re.search(r'<div[^>]*class="[^"]*vod-detail[^"]*"[^>]*>[\s\S]*?<img[^>]+src="([^"]+)"', html)
            if m:
                vod["vod_pic"] = self._abs_url(m.group(1).strip())

            # 导演
            m = re.search(r'<strong>导演[：:]</strong>\s*<a[^>]*>([^<]+)</a>', html) or \
                re.search(r'导演[：:]\s*([^<\n]+)', html)
            if m:
                vod["vod_director"] = self._strip(m.group(1))

            # 主演
            m = re.search(r'<strong>主演[：:]</strong>([\s\S]*?)</p>', html)
            if m:
                actors = re.sub(r'<[^>]+>', ' ', m.group(1))
                vod["vod_actor"] = self._strip(actors)[:300]

            # 类型
            m = re.search(r'<strong>类型[：:]</strong>\s*<a[^>]*>([^<]+)</a>', html) or \
                re.search(r'<strong>分类[：:]</strong>\s*<a[^>]*>([^<]+)</a>', html)
            if m:
                vod["vod_class"] = self._strip(m.group(1))

            # 地区
            m = re.search(r'<strong>地区[：:]</strong>\s*<a[^>]*>([^<]+)</a>', html) or \
                re.search(r'地区[：:]\s*([^<\n,]+)', html)
            if m:
                vod["vod_area"] = self._strip(m.group(1))

            # 年代
            m = re.search(r'<strong>年代[：:]</strong>\s*<a[^>]*>(\d{4})</a>', html) or \
                re.search(r'<strong>年份[：:]</strong>\s*<a[^>]*>(\d{4})</a>', html) or \
                re.search(r'年代[：:]\s*(\d{4})', html)
            if m:
                vod["vod_year"] = m.group(1)

            # 备注
            m = re.search(r'<strong>更新[：:]</strong>\s*([^<]+)', html) or \
                re.search(r'<strong>状态[：:]</strong>\s*([^<]+)', html) or \
                re.search(r'更新[：:]\s*([^<\n]+)', html)
            if m:
                vod["vod_remarks"] = self._strip(m.group(1))

            # 简介
            m = re.search(r'<strong>简介[：:]</strong>([\s\S]*?)</p>', html) or \
                re.search(r'class="[^"]*vod-blurb[^"]*"[^>]*>([\s\S]*?)</div>', html) or \
                re.search(r'class="[^"]*detail-content[^"]*"[^>]*>([\s\S]*?)</div>', html)
            if m:
                txt = re.sub(r'<[^>]+>', '', m.group(1))
                vod["vod_content"] = self._strip(txt)[:800]

            # 播放列表解析
            play_from, play_url = self._collect_playlist(html)
            if play_from:
                vod["vod_play_from"] = "$$$".join(play_from)
                vod["vod_play_url"] = "$$$".join(play_url)

            return {"list": [vod]}
        except Exception as e:
            print(f"[图图影院] detailContent 异常: {e}")
            return {"list": []}

    def _collect_playlist(self, html):
        """解析多播放源 + 剧集列表，最后反转成正序。"""
        play_from, play_url = [], []

        # 方法1: 从 vod_play_list / vod_play_from 等JS变量提取(最准确)
        for var_name in ['vod_play_list', 'vod_play_from', 'player_list', 'play_list', 'vod_player']:
            vod_list = _extract_js_var(html, var_name)
            if vod_list:
                pf, pu = self._parse_vod_play_list(vod_list)
                if pf:
                    return pf, pu

        # 方法2: 从HTML tab结构提取
        # 先提取所有tab标题
        tab_titles = []
        # 匹配 nav-tabs / nav-pills
        for nav_m in re.finditer(r'<ul[^>]*class="[^"]*(?:nav-tabs|nav-pills)[^"]*"[^>]*>([\s\S]*?)</ul>', html):
            titles = re.findall(r'<a[^>]*>([^<]+)</a>', nav_m.group(1))
            tab_titles.extend(titles)
        # 尝试匹配 data-toggle="tab"
        if not tab_titles:
            tab_titles = re.findall(r'<a[^>]*data-toggle=["\']tab["\'][^>]*>([^<]+)</a>', html)
        # 尝试匹配 .option / .source 中的播放源名称
        if not tab_titles:
            tab_titles = re.findall(r'class="[^"]*(?:option|source|from)[^"]*"[^>]*>[\s\S]*?<span[^>]*>([^<]+)</span>', html)
        # 尝试匹配 h3/h4/h5 中包含播放相关关键词的标题
        if not tab_titles:
            for hm in re.finditer(r'<h[345][^>]*>([\s\S]*?)</h[345]>', html):
                txt = self._strip(re.sub(r'<[^>]+>', '', hm.group(1)))
                if any(k in txt for k in ['播放', '线路', '源', '集', '集数', '观看']):
                    tab_titles.append(txt)

        # 提取 tab-pane 内容
        panes = re.split(r'<div[^>]*class="[^"]*tab-pane[^"]*"[^>]*>', html)
        if len(panes) > 1:
            for i, pane in enumerate(panes[1:], 0):
                end = pane.find('<div class="tab-pane')
                if end == -1:
                    end = pane.find('section-title')
                if end == -1:
                    end = len(pane)
                chunk = pane[:end]
                eps = self._extract_eps_from_chunk(chunk)
                if eps:
                    title = tab_titles[i] if i < len(tab_titles) else f"线路{i+1}"
                    play_from.append(title)
                    play_url.append("#".join(eps))

        # 方法3: 按 .playlist / .play-list / .hy-play-list 区块提取
        if not play_from:
            # 匹配每个播放源区块(以包含ttplay链接的div为单位)
            playlist_blocks = re.findall(r'<div[^>]*class="[^"]*(?:playlist|play-list|hy-play-list|panel)[^"]*"[^>]*>([\s\S]*?)</div>', html)
            for chunk in playlist_blocks:
                eps = self._extract_eps_from_chunk(chunk)
                if eps:
                    play_from.append(f"线路{len(play_from) + 1}")
                    play_url.append("#".join(eps))

        # 方法4: 全局匹配(最后兜底)
        if not play_from:
            eps = self._extract_eps_from_chunk(html)
            if eps:
                play_from.append("默认线路")
                play_url.append("#".join(eps))

        # 反转每个播放源的剧集顺序(页面默认倒序，需要正序)
        if play_url:
            play_url = [self._reverse_eps(urls) for urls in play_url]

        return play_from, play_url

    def _extract_eps_from_chunk(self, chunk):
        """从HTML区块中提取剧集链接。"""
        eps = []
        for em in re.finditer(
            r'<a[^>]+href="(/ttplay/\d+-\d+-\d+\.html)"[^>]*>([\s\S]*?)</a>',
            chunk,
        ):
            bf_path = em.group(1)
            name = self._strip(re.sub(r'<[^>]+>', '', em.group(2))) or "正片"
            eps.append(f"{name}${bf_path}")
        return eps

    def _parse_vod_play_list(self, vod_list):
        """解析 vod_play_list JS变量。"""
        play_from, play_url = [], []
        if not isinstance(vod_list, list):
            return play_from, play_url
        for src in vod_list:
            if not isinstance(src, dict):
                continue
            pinfo = src.get('player_info', {})
            src_name = pinfo.get('show', '') or pinfo.get('from', '')
            urls = src.get('urls', [])
            eps = []
            for u in urls:
                if isinstance(u, dict):
                    name = u.get('name', '正片')
                    link = u.get('url', '')
                    if link:
                        eps.append(f"{name}${link}")
            if eps:
                play_from.append(src_name or f"线路{len(play_from) + 1}")
                play_url.append("#".join(eps))
        if play_url:
            play_url = [self._reverse_eps(urls) for urls in play_url]
        return play_from, play_url

    @staticmethod
    def _reverse_eps(urls_str):
        """将剧集字符串反转成正序(第1集在前)。"""
        if not urls_str:
            return urls_str
        eps = urls_str.split("#")
        eps.reverse()
        return "#".join(eps)

    # ===== 搜索(兼容多种结果页结构) =====
    def searchContent(self, key, quick, pg="1"):
        try:
            kw = self._strip(str(key or ""))
            if not kw:
                return {"list": []}

            page = int(pg or 1)
            if page < 1:
                page = 1

            # maccms 搜索URL常见格式:
            # 1) /search.html?wd=关键词&page=页码
            # 2) /search/page/页码/wd/关键词.html
            # 3) /vodsearch/关键词----------页码---.html
            urls_to_try = [
                f"{HOST}/search.html?wd={quote(kw)}&page={page}",
                f"{HOST}/search.html?wd={quote(kw)}",  # 第1页无page参数
            ]
            if page == 1:
                urls_to_try = urls_to_try[1:] + urls_to_try[:1]

            html = ""
            for url in urls_to_try:
                html = self._get_html(url, timeout=12)
                if html and ('ttvod' in html or 'videopic' in html or 'vod_name' in html):
                    break

            if not html:
                return {"list": []}

            # 搜索结果页可能用 src 而非 data-original
            videos = self._parse_search_list(html)

            # 解析总页数(兼容多种分页格式)
            pagecount = page
            for pm in re.finditer(r'href="[^"]*(?:search\.html[^"]*page=|/search/page/|/vodsearch/[^"]*?)(\d+)(?:\.html|"|\&)', html):
                n = int(pm.group(1))
                if n > pagecount:
                    pagecount = n
            if not videos and page > 1:
                pagecount = max(1, page - 1)

            total = pagecount * SEARCH_PAGE_SIZE

            return {
                "list": videos,
                "page": page,
                "pagecount": pagecount,
                "limit": SEARCH_PAGE_SIZE,
                "total": total,
            }
        except Exception as e:
            print(f"[图图影院] searchContent 异常: {e}")
            return {"list": []}

    def _parse_search_list(self, html):
        """解析搜索结果页，兼容 data-original(懒加载) 和 src(直接加载) 两种封面。"""
        items = []

        # 方式1: 匹配 data-original (懒加载，跟首页一样)
        for m in re.finditer(
            r'<a\b[^>]*href="(/ttvod/(\d+)\.html)"[^>]*title="([^"]*)"[^>]*data-original="([^"]*)"[^>]*>'
            r'[\s\S]*?'
            r'<span\b[^>]*class="[^"]*note[^"]*"[^>]*>([^<]*)</span>',
            html,
        ):
            items.append({
                "vod_id": m.group(2),
                "vod_name": self._strip(m.group(3)),
                "vod_pic": self._abs_url(m.group(4).strip()),
                "vod_remarks": self._strip(m.group(5)),
            })

        # 方式2: 匹配 src (非懒加载，搜索结果页常见)
        if not items:
            for m in re.finditer(
                r'<a\b[^>]*href="(/ttvod/(\d+)\.html)"[^>]*title="([^"]*)"[^>]*>'
                r'[\s\S]*?'
                r'<img\b[^>]*src="([^"]*)"[^>]*>'
                r'[\s\S]*?'
                r'<span\b[^>]*class="[^"]*note[^"]*"[^>]*>([^<]*)</span>',
                html,
            ):
                items.append({
                    "vod_id": m.group(2),
                    "vod_name": self._strip(m.group(3)),
                    "vod_pic": self._abs_url(m.group(4).strip()),
                    "vod_remarks": self._strip(m.group(5)),
                })

        # 方式3: 更宽松的匹配(有些模板结构不同)
        if not items:
            for m in re.finditer(
                r'<a\b[^>]*href="(/ttvod/(\d+)\.html)"[^>]*title="([^"]*)"[^>]*>'
                r'[\s\S]*?'
                r'(?:data-original|src)="([^"]*)"',
                html,
            ):
                # 尝试找备注
                note_m = re.search(r'<span\b[^>]*class="[^"]*note[^"]*"[^>]*>([^<]*)</span>', html[m.end():m.end()+500])
                note = note_m.group(1) if note_m else ""
                items.append({
                    "vod_id": m.group(2),
                    "vod_name": self._strip(m.group(3)),
                    "vod_pic": self._abs_url(m.group(4).strip()),
                    "vod_remarks": self._strip(note),
                })

        # 去重
        seen, uniq = set(), []
        for it in items:
            if it['vod_id'] in seen:
                continue
            seen.add(it['vod_id'])
            uniq.append(it)
        return uniq

    # ===== 播放页 =====
    def playerContent(self, flag, id, vipFlags):
        play_url = str(id or "")
        if not play_url:
            return {"parse": 0, "url": ""}

        if self.isVideoFormat(play_url):
            return {
                "parse": 0,
                "url": play_url,
                "header": {"User-Agent": UA, "Referer": HOST + "/"},
            }

        if "/ttplay/" in play_url:
            if not play_url.startswith("http"):
                play_url = HOST + play_url
            html = self._get_html(play_url, timeout=12)
            if html:
                real = self._extract_video_url(html)
                if real:
                    return {
                        "parse": 0,
                        "url": real,
                        "header": {"User-Agent": UA, "Referer": play_url},
                    }

        return {
            "parse": 0,
            "url": play_url,
            "header": {"User-Agent": UA, "Referer": HOST + "/"},
        }

    @staticmethod
    def _extract_video_url(html):
        m = re.search(r'<iframe[^>]+src=["\'](https?://[^"\']+)["\']', html)
        if m:
            iframe_url = m.group(1)
            if any(ext in iframe_url.lower() for ext in ['.m3u8', '.mp4']):
                return iframe_url
            return iframe_url

        m = re.search(r'(?:src|url|data-url)\s*=["\'](https?://[^"\']+\.(?:m3u8|mp4|flv))["\']', html)
        if m:
            return m.group(1)

        obj = _extract_player_obj(html)
        if obj and obj.get('url'):
            return obj['url']

        return ""

    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]

    def destroy(self):
        pass


# ============================================================
# 模块级辅助函数
# ============================================================
def _extract_js_var(html, var_name):
    """从HTML中提取 var xxx = [...] 或 var xxx = {...} 的JSON对象。"""
    pattern = rf'var\s+{re.escape(var_name)}\s*=\s*'
    m = re.search(pattern, html)
    if not m:
        return None
    i = m.end()
    if i >= len(html):
        return None
    start_char = html[i]
    if start_char not in '{[':
        return None
    end_char = '}' if start_char == '{' else ']'
    depth = 0
    in_str = False
    str_char = None
    start = i
    while i < len(html):
        c = html[i]
        if not in_str:
            if c == start_char:
                depth += 1
            elif c == end_char:
                depth -= 1
                if depth == 0:
                    break
            elif c in '"\'':
                in_str = True
                str_char = c
        else:
            if c == str_char and html[i - 1] != '\\':
                in_str = False
        i += 1
    if depth != 0:
        return None
    raw = html[start:i + 1]
    try:
        return json.loads(raw)
    except Exception:
        try:
            return json.loads(raw.replace("'", '"'))
        except Exception:
            return None


def _extract_player_obj(html):
    """从播放页提取 var player_xxxx = {...}; 的对象。"""
    m = re.search(r'var\s+player_\w+\s*=\s*', html)
    if not m:
        return None
    i = m.end()
    if i >= len(html) or html[i] != '{':
        return None
    depth, start = 0, i
    while i < len(html):
        c = html[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                break
        elif c == '"':
            i += 1
            while i < len(html) and html[i] != '"':
                if html[i] == '\\':
                    i += 2
                    continue
                i += 1
        i += 1
    if depth != 0:
        return None
    raw = html[start:i + 1]
    try:
        return json.loads(raw)
    except Exception:
        try:
            return json.loads(raw.replace("'", '"'))
        except Exception:
            return None
