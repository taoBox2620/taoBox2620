# -*- coding: utf-8 -*-
"""
红果影视 TVBox/猫影视爬虫插件 — https://www.shrongmai.com/
苹果CMS v10 + stui 模板 (定制版)
适配: 首页解析为主，分类页带验证码降级策略

路由:
  首页         /
  分类         /special/{type_id}_{page}.html
  详情         /synopsis/{id}.html
  搜索         /vodsearch/{wd}-------------.html  (多路径兼容)
  播放         /play/{id}-{sid}-{nid}.html
"""

import re
import json
import time
import hashlib
import threading
import warnings
from urllib.parse import urljoin, quote

try:
    warnings.filterwarnings("ignore")
    import urllib3
    urllib3.disable_warnings()
except Exception:
    pass

try:
    from base.spider import Spider
except ImportError:
    import requests as _rq
    from requests.adapters import HTTPAdapter

    class Spider:
        def __init__(self):
            self._session = _rq.Session()
            adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)

        def fetch(self, url, headers=None, timeout=15, **kw):
            headers = headers or {}
            headers.setdefault("User-Agent", UA)
            return self._session.get(url, headers=headers, timeout=timeout, verify=False, **kw)

        def destroy(self):
            try:
                self._session.close()
            except Exception:
                pass


HOST = "https://www.shrongmai.com"
UA = ("Mozilla/5.0 (Linux; Android 12; M2007J22C) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")

# 主分类 (与导航对应: /special/{id}_1.html)
CLASSES = [
    {"type_name": "电影", "type_id": "1"},
    {"type_name": "电视剧", "type_id": "2"},
    {"type_name": "综艺", "type_id": "3"},
    {"type_name": "动漫", "type_id": "4"},
    {"type_name": "短剧", "type_id": "34"},
]

# 二级分类筛选条件 (基于苹果CMS标准参数构造)
# 实际筛选URL: /special/{type_id}_{page}_{by}_{class}_{year}_{area}_{lang}_.html
# 但站点有验证码，这些筛选主要用于展示，请求时会尝试构造
FILTERS = {
    "1": [  # 电影
        {"key": "class", "name": "类型", "value": [
            {"n": "全部", "v": ""},
            {"n": "动作片", "v": "动作"},
            {"n": "喜剧片", "v": "喜剧"},
            {"n": "爱情片", "v": "爱情"},
            {"n": "科幻片", "v": "科幻"},
            {"n": "恐怖片", "v": "恐怖"},
            {"n": "剧情片", "v": "剧情"},
            {"n": "战争片", "v": "战争"},
            {"n": "动画片", "v": "动画"},
            {"n": "悬疑片", "v": "悬疑"},
            {"n": "犯罪片", "v": "犯罪"},
            {"n": "冒险片", "v": "冒险"},
        ]},
        {"key": "area", "name": "地区", "value": [
            {"n": "全部", "v": ""},
            {"n": "大陆", "v": "大陆"},
            {"n": "香港", "v": "香港"},
            {"n": "台湾", "v": "台湾"},
            {"n": "美国", "v": "美国"},
            {"n": "韩国", "v": "韩国"},
            {"n": "日本", "v": "日本"},
            {"n": "泰国", "v": "泰国"},
            {"n": "英国", "v": "英国"},
            {"n": "法国", "v": "法国"},
            {"n": "德国", "v": "德国"},
            {"n": "印度", "v": "印度"},
            {"n": "其他", "v": "其他"},
        ]},
        {"key": "year", "name": "年份", "value": [
            {"n": "全部", "v": ""},
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
            {"n": "2015", "v": "2015"},
            {"n": "2010-2014", "v": "2010-2014"},
            {"n": "2000-2009", "v": "2000-2009"},
            {"n": "更早", "v": "更早"},
        ]},
        {"key": "by", "name": "排序", "value": [
            {"n": "时间", "v": "time"},
            {"n": "人气", "v": "hits"},
            {"n": "评分", "v": "score"},
        ]},
    ],
    "2": [  # 电视剧
        {"key": "class", "name": "类型", "value": [
            {"n": "全部", "v": ""},
            {"n": "国产剧", "v": "国产"},
            {"n": "港台剧", "v": "港台"},
            {"n": "日韩剧", "v": "日韩"},
            {"n": "欧美剧", "v": "欧美"},
            {"n": "海外剧", "v": "海外"},
        ]},
        {"key": "area", "name": "地区", "value": [
            {"n": "全部", "v": ""},
            {"n": "大陆", "v": "大陆"},
            {"n": "香港", "v": "香港"},
            {"n": "台湾", "v": "台湾"},
            {"n": "韩国", "v": "韩国"},
            {"n": "日本", "v": "日本"},
            {"n": "美国", "v": "美国"},
            {"n": "泰国", "v": "泰国"},
            {"n": "英国", "v": "英国"},
            {"n": "其他", "v": "其他"},
        ]},
        {"key": "year", "name": "年份", "value": [
            {"n": "全部", "v": ""},
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
            {"n": "2015", "v": "2015"},
        ]},
        {"key": "by", "name": "排序", "value": [
            {"n": "时间", "v": "time"},
            {"n": "人气", "v": "hits"},
            {"n": "评分", "v": "score"},
        ]},
    ],
    "3": [  # 综艺
        {"key": "area", "name": "地区", "value": [
            {"n": "全部", "v": ""},
            {"n": "大陆", "v": "大陆"},
            {"n": "香港", "v": "香港"},
            {"n": "台湾", "v": "台湾"},
            {"n": "韩国", "v": "韩国"},
            {"n": "日本", "v": "日本"},
            {"n": "美国", "v": "美国"},
            {"n": "其他", "v": "其他"},
        ]},
        {"key": "lang", "name": "语言", "value": [
            {"n": "全部", "v": ""},
            {"n": "国语", "v": "国语"},
            {"n": "粤语", "v": "粤语"},
            {"n": "英语", "v": "英语"},
            {"n": "韩语", "v": "韩语"},
            {"n": "日语", "v": "日语"},
            {"n": "其他", "v": "其他"},
        ]},
        {"key": "year", "name": "年份", "value": [
            {"n": "全部", "v": ""},
            {"n": "2026", "v": "2026"},
            {"n": "2025", "v": "2025"},
            {"n": "2024", "v": "2024"},
            {"n": "2023", "v": "2023"},
            {"n": "2022", "v": "2022"},
            {"n": "2021", "v": "2021"},
            {"n": "2020", "v": "2020"},
            {"n": "2019", "v": "2019"},
        ]},
        {"key": "by", "name": "排序", "value": [
            {"n": "时间", "v": "time"},
            {"n": "人气", "v": "hits"},
            {"n": "评分", "v": "score"},
        ]},
    ],
    "4": [  # 动漫
        {"key": "class", "name": "类型", "value": [
            {"n": "全部", "v": ""},
            {"n": "国产动漫", "v": "国产"},
            {"n": "日本动漫", "v": "日本"},
            {"n": "欧美动漫", "v": "欧美"},
            {"n": "海外动漫", "v": "海外"},
        ]},
        {"key": "area", "name": "地区", "value": [
            {"n": "全部", "v": ""},
            {"n": "大陆", "v": "大陆"},
            {"n": "日本", "v": "日本"},
            {"n": "韩国", "v": "韩国"},
            {"n": "美国", "v": "美国"},
            {"n": "其他", "v": "其他"},
        ]},
        {"key": "year", "name": "年份", "value": [
            {"n": "全部", "v": ""},
            {"n": "2026", "v": "2026"},
            {"n": "2025", "v": "2025"},
            {"n": "2024", "v": "2024"},
            {"n": "2023", "v": "2023"},
            {"n": "2022", "v": "2022"},
            {"n": "2021", "v": "2021"},
            {"n": "2020", "v": "2020"},
            {"n": "2019", "v": "2019"},
        ]},
        {"key": "by", "name": "排序", "value": [
            {"n": "时间", "v": "time"},
            {"n": "人气", "v": "hits"},
            {"n": "评分", "v": "score"},
        ]},
    ],
    "34": [  # 短剧
        {"key": "by", "name": "排序", "value": [
            {"n": "时间", "v": "time"},
            {"n": "人气", "v": "hits"},
            {"n": "评分", "v": "score"},
        ]},
    ],
}

LIST_PAGE_SIZE = 24
HOME_PAGE_SIZE = 24
CACHE_TTL = 60
HOME_CACHE_TTL = 30
SEARCH_CACHE_TTL = 30
CIRCUIT_FAILS = 3
CIRCUIT_COOLDOWN = 30


def _urlencode(s):
    return quote(s or "", safe="")


def _strip(txt):
    return re.sub(r"\s+", " ", txt or "").strip()


def _unescape(txt):
    if not txt:
        return ""
    try:
        import html as _html
        return _html.unescape(txt)
    except Exception:
        return re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), txt)


def _abs_url(url, base):
    if not url:
        return ""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http"):
        return url
    if url.startswith("/"):
        return base + url
    return urljoin(base + "/", url)


class Spider(Spider):
    # 预编译正则 —— 提升解析速度
    # FIX: data-original 在 <a> 标签内部，必须在 > 之前匹配，否则会错位抓到下一个视频的图片
    _RE_HOME_VOD = re.compile(
        r'<a[^>]+href="(/synopsis/(\d+)\.html)"[^>]*title="([^"]*)"[^>]*?data-original="([^"]*)"[^>]*>'
        r'(?:[\s\S]*?<span[^>]*class="[^"]*pic-text[^"]*"[^>]*>([^<]+)</span>)?'
    )
    # FIX: 站点使用 stui-vodlist__head 而非 stui-pannel__head
    _RE_HOME_MODULE = re.compile(
        r'<div[^>]*class="[^"]*stui-vodlist__head[^"]*"[^>]*>([\s\S]*?)</div>'
        r'[\s\S]*?<ul[^>]*class="[^"]*stui-vodlist[^"]*"[^>]*>([\s\S]*?)</ul>'
    )
    _RE_DETAIL_TITLE = re.compile(r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</h1>')
    # FIX: 站点详情页图片用 lazyload 类而非 img-responsive，且支持 data-original 和 data-src
    _RE_DETAIL_PIC = re.compile(r'<img[^>]*data-original="([^"]+)"[^>]*>')
    _RE_DETAIL_PIC2 = re.compile(r'<img[^>]*data-src="([^"]+)"[^>]*>')
    _RE_DETAIL_INFO = re.compile(
        r'<p[^>]*class="[^"]*data[^"]*"[^>]*>'
        r'[\s\S]*?<span[^>]*class="[^"]*text-muted[^"]*"[^>]*>([^<]+)</span>'
        r'[\s\S]*?<a[^>]*>([^<]+)</a>'
    )
    _RE_DETAIL_INFO2 = re.compile(
        r'<p[^>]*class="[^"]*data[^"]*"[^>]*>'
        r'[\s\S]*?<span[^>]*class="[^"]*text-muted[^"]*"[^>]*>([^<]+)</span>'
        r'[\s\S]*?>([^<]+)<'
    )
    _RE_DETAIL_DESC = re.compile(r'<p[^>]*class="[^"]*desc[^"]*"[^>]*>([\s\S]*?)</p>')
    _RE_DETAIL_DESC2 = re.compile(r'<span[^>]*class="[^"]*detail-content[^"]*"[^>]*>([\s\S]*?)</span>')
    # FIX: stui-content__playlist 在 <ul> 上，不是 <div>
    _RE_PLAYLIST = re.compile(r'<ul[^>]*class="[^"]*stui-content__playlist[^"]*"[^>]*>([\s\S]*?)</ul>')
    # FIX: 站点播放链接用 /screen/ 路由，而非 /play/
    _RE_PLAY_EP = re.compile(r'<a[^>]+href="(/(?:play|screen)/(\d+)-(\d+)-(\d+)\.html)"[^>]*>([\s\S]*?)</a>')
    _RE_PLAY_TAB = re.compile(r'<a[^>]*href="#playlist(\d+)"[^>]*>([^<]+)</a>')
    _RE_PLAYER_JSON = re.compile(r'var\s+player_aaaa\s*=\s*(\{[\s\S]*?\})\s*</script>')
    # FIX: /screen/ 播放页通过 playerUrl JS 变量嵌入真实 m3u8/mp4 地址
    _RE_PLAYER_URL = re.compile(r"""playerUrl\s*=\s*['"][^'"]*\?url=(https?://[^'"]+)['"]""")
    _RE_VIDEO_URL = re.compile(r"""['"](https?://[^'"]+\.(?:m3u8|mp4|flv)[^'"]*)['"]""")
    _RE_SEARCH_VOD = re.compile(
        r'<a[^>]+href="(/synopsis/(\d+)\.html)"[^>]*title="([^"]*)"[^>]*?data-original="([^"]*)"[^>]*>'
        r'(?:[\s\S]*?<span[^>]*class="[^"]*pic-text[^"]*"[^>]*>([^<]+)</span>)?'
    )
    _RE_PAGE_TOTAL = re.compile(r'class="[^"]*hidden-xs[^"]*"[^>]*>共(\d+)条记录</a>')

    def getName(self):
        return "红果影视"

    def init(self, extend=""):
        self.header = {
            "User-Agent": UA,
            "Referer": HOST + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
        try:
            import requests
            from requests.adapters import HTTPAdapter
            self._session = requests.Session()
            adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=1)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
            self._session.trust_env = False
        except Exception as e:
            print("[红果] requests 不可用, 回退到框架 fetch: " + str(e))
            self._session = None

        self._cache = {}
        self._home_cache = None
        self._cache_lock = threading.Lock()
        self._cb_fails = 0
        self._cb_open_until = 0
        self._cb_lock = threading.Lock()

    def isVideoFormat(self, url):
        u = (url or "").lower().rstrip("?#")
        return any(u.endswith(ext) for ext in (".m3u8", ".mp4", ".flv", ".ts"))

    def destroy(self):
        sess = getattr(self, "_session", None)
        if sess is not None:
            try:
                sess.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 网络层 (带熔断 + 多降级)
    # ------------------------------------------------------------------
    def _circuit_allow(self):
        with self._cb_lock:
            if self._cb_open_until and time.time() < self._cb_open_until:
                return False
            return True

    def _circuit_record(self, ok):
        with self._cb_lock:
            if ok:
                self._cb_fails = 0
            else:
                self._cb_fails += 1
                if self._cb_fails >= CIRCUIT_FAILS:
                    self._cb_open_until = time.time() + CIRCUIT_COOLDOWN
                    print("[红果] 熔断 " + str(CIRCUIT_COOLDOWN) + "s")

    def _http_get(self, url, timeout=10):
        if not self._circuit_allow():
            return ""
        ok = False
        sess = getattr(self, "_session", None)
        if sess is not None:
            try:
                rsp = sess.get(url, headers=self.header, timeout=timeout, verify=False)
                if rsp.status_code == 200:
                    ok = True
                    # 简单反爬检测: 如果内容极短且含验证码特征，视为失败
                    if len(rsp.text) < 3000 and ("captcha" in rsp.text or "请输入验证码" in rsp.text):
                        ok = False
                        print("[红果] 遇到验证码: " + url)
                        return ""
                    return rsp.text
            except Exception as e:
                pass
        try:
            rsp = self.fetch(url, headers=self.header, timeout=timeout)
            if getattr(rsp, "status_code", 0) == 200:
                ok = True
                txt = getattr(rsp, "text", "") or ""
                if len(txt) < 3000 and ("captcha" in txt or "请输入验证码" in txt):
                    ok = False
                    return ""
                return txt
        except Exception:
            pass
        finally:
            self._circuit_record(ok)
        return ""

    def _http_post(self, url, data, timeout=10):
        sess = getattr(self, "_session", None)
        if sess is not None:
            try:
                rsp = sess.post(url, data=data, headers=self.header, timeout=timeout, verify=False)
                if rsp.status_code == 200:
                    return rsp.text
            except Exception:
                pass
        try:
            from urllib.request import Request as _Req, urlopen as _Uo
            from urllib.parse import urlencode as _Ue
            body = _Ue(data).encode("utf-8")
            req = _Req(url, data=body, headers=self.header)
            import ssl as _ssl
            ctx = _ssl._create_unverified_context()
            rsp = _Uo(req, timeout=timeout, context=ctx)
            raw = rsp.read()
            if not isinstance(raw, str):
                raw = raw.decode("utf-8", errors="replace")
            return raw
        except Exception:
            pass
        try:
            rsp = self.fetch(url, headers=self.header, timeout=timeout, data=data)
            if getattr(rsp, "status_code", 0) == 200:
                return rsp.text
        except Exception:
            pass
        return None

    def _abs(self, url):
        return _abs_url(url, HOST)

    # ------------------------------------------------------------------
    # 解析层
    # ------------------------------------------------------------------
    def _parse_vod_items(self, html):
        """从任意HTML片段中解析视频列表"""
        items = []
        seen = set()
        for m in self._RE_HOME_VOD.finditer(html):
            vid = m.group(2)
            if vid in seen:
                continue
            seen.add(vid)
            items.append({
                "vod_id": vid,
                "vod_name": _strip(_unescape(m.group(3))),
                "vod_pic": self._abs(_unescape(m.group(4))),
                "vod_remarks": _strip(_unescape(m.group(5) or "")),
            })
        return items

    def _pagecount(self, html, cur_page):
        mx = cur_page
        # 从分页链接找最大页
        for n in re.findall(r'/special/\d+_(\d+)(?:_[^/]*)*\.html', html):
            mx = max(mx, int(n))
        m = self._RE_PAGE_TOTAL.search(html)
        if m:
            total = int(m.group(1))
            mx = max(mx, (total + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE)
        return max(mx, 1)

    # ------------------------------------------------------------------
    # 首页
    # ------------------------------------------------------------------
    def homeContent(self, filter):
        return {"class": CLASSES, "filters": FILTERS}

    def homeVideoContent(self):
        now = time.time()
        with self._cache_lock:
            if self._home_cache:
                ts, payload = self._home_cache
                if now - ts < HOME_CACHE_TTL:
                    return payload

        html = self._http_get(HOST + "/", timeout=8)
        if not html:
            return {"list": []}

        items = self._parse_vod_items(html)
        payload = {"list": items[:HOME_PAGE_SIZE]}

        with self._cache_lock:
            self._home_cache = (now, payload)
        return payload

    # ------------------------------------------------------------------
    # 分类 (核心: 带验证码降级)
    # ------------------------------------------------------------------
    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg or 1)
            if page < 1:
                page = 1
            ext = extend or {}
            cls = str(ext.get("class", "") or "")
            area = str(ext.get("area", "") or "")
            year = str(ext.get("year", "") or "")
            lang = str(ext.get("lang", "") or "")
            by = str(ext.get("by", "time") or "time")
            use_tid = str(tid)

            cache_key = (use_tid, cls, area, year, lang, by, page)
            now = time.time()
            with self._cache_lock:
                hit = self._cache.get(cache_key)
                if hit and now - hit[0] < CACHE_TTL:
                    return hit[1]

            # 构造分类URL: /special/{tid}_{page}_{by}_{class}_{year}_{area}_{lang}_.html
            # 简化构造，只填有效参数
            parts = [HOST, "/special/", use_tid, "_", str(page)]
            # 苹果CMS stui 模板标准顺序: page by class year area lang letter
            # 但不同模板可能有差异，这里保守构造
            suffix = "_" + _urlencode(by) if by else "_time"
            suffix += "_" + _urlencode(cls) if cls else "_"
            suffix += "_" + _urlencode(year) if year else "_"
            suffix += "_" + _urlencode(area) if area else "_"
            suffix += "_" + _urlencode(lang) if lang else "_"
            suffix += "_.html"
            url = "".join(parts) + suffix

            html = self._http_get(url, timeout=10)

            # ---- 降级策略: 如果分类页被验证码拦截，从首页提取对应分类数据 ----
            if not html and page == 1:
                print("[红果] 分类页被拦截，尝试从首页降级提取 tid=" + use_tid)
                home_html = self._http_get(HOST + "/", timeout=8)
                if home_html:
                    # 尝试按模块标题匹配分类
                    type_name_map = {"1": "电影", "2": "电视剧", "3": "综艺", "4": "动漫", "34": "短剧"}
                    target_name = type_name_map.get(use_tid, "")
                    if target_name:
                        # 找模块: <div class="stui-pannel__head">...电影...</div> ... <ul class="stui-vodlist">...</ul>
                        modules = self._RE_HOME_MODULE.finditer(home_html)
                        for mod in modules:
                            head = mod.group(1)
                            body = mod.group(2)
                            if target_name in head:
                                items = self._parse_vod_items(body)
                                payload = {
                                    "list": items,
                                    "page": 1,
                                    "pagecount": 1,
                                    "limit": len(items),
                                    "total": len(items),
                                }
                                with self._cache_lock:
                                    self._cache[cache_key] = (now, payload)
                                return payload

            if not html:
                return {"list": [], "page": page, "pagecount": 1, "limit": LIST_PAGE_SIZE, "total": 0}

            videos = self._parse_vod_items(html)
            pagecount = self._pagecount(html, page)
            if not videos:
                pagecount = max(1, page)

            payload = {
                "list": videos,
                "page": page,
                "pagecount": pagecount,
                "limit": len(videos) or LIST_PAGE_SIZE,
                "total": pagecount * LIST_PAGE_SIZE,
            }
            with self._cache_lock:
                self._cache[cache_key] = (now, payload)
            return payload
        except Exception as e:
            print("[红果] categoryContent 异常: " + str(e))
            return {"list": [], "page": 1, "pagecount": 1, "limit": LIST_PAGE_SIZE, "total": 0}

    # ------------------------------------------------------------------
    # 详情
    # ------------------------------------------------------------------
    def detailContent(self, ids):
        try:
            if isinstance(ids, (list, tuple)):
                ids = ids[0]
            vod_id = str(ids)
            now = time.time()
            cache_key = ("detail", vod_id)
            with self._cache_lock:
                hit = self._cache.get(cache_key)
                if hit and now - hit[0] < CACHE_TTL * 5:
                    return hit[1]

            if vod_id.startswith("/"):
                url = HOST + vod_id
            else:
                url = HOST + "/synopsis/" + vod_id + ".html"

            html = self._http_get(url, timeout=10)
            if not html:
                return {"list": []}

            vod = {
                "vod_id": vod_id,
                "vod_name": "",
                "vod_pic": "",
                "vod_year": "",
                "vod_area": "",
                "vod_lang": "",
                "vod_remarks": "",
                "vod_actor": "",
                "vod_director": "",
                "vod_class": "",
                "vod_content": "",
                "vod_play_from": "",
                "vod_play_url": "",
            }

            m = self._RE_DETAIL_TITLE.search(html)
            if m:
                vod["vod_name"] = _strip(_unescape(m.group(1)))

            # FIX: 详情页图片用 lazyload+data-original，需找到第一个有效 http 图片
            for pm in self._RE_DETAIL_PIC.finditer(html):
                pic_url = _unescape(pm.group(1))
                if pic_url and pic_url.startswith("http"):
                    vod["vod_pic"] = self._abs(pic_url)
                    break
            if not vod["vod_pic"]:
                for pm in self._RE_DETAIL_PIC2.finditer(html):
                    pic_url = _unescape(pm.group(1))
                    if pic_url and pic_url.startswith("http"):
                        vod["vod_pic"] = self._abs(pic_url)
                        break

            # 提取信息项 — 先尝试 span.text-muted 正则，再降级到纯文本解析
            found_info = False
            for label, val in self._RE_DETAIL_INFO.findall(html):
                found_info = True
                label = _strip(label)
                val = _strip(_unescape(val))
                if "主演" in label:
                    vod["vod_actor"] = val
                elif "导演" in label:
                    vod["vod_director"] = val
                elif "类型" in label:
                    vod["vod_class"] = val
                elif "地区" in label:
                    vod["vod_area"] = val
                elif "年份" in label:
                    vod["vod_year"] = val
                elif "语言" in label:
                    vod["vod_lang"] = val
                elif "更新" in label or "状态" in label or "备注" in label:
                    vod["vod_remarks"] = val

            # FIX: 如果 span.text-muted 正则未匹配，降级为纯文本标签解析
            # 站点 <p class="data"> 中标签为纯文本（如 "主演：xxx"），不包裹在 span 内
            if not found_info or not vod["vod_actor"]:
                for pm in re.finditer(
                    r'<p[^>]*class="[^"]*data[^"]*"[^>]*>([\s\S]*?)</p>', html
                ):
                    raw = pm.group(1)
                    text = re.sub(r"</a>", " ", raw)
                    text = re.sub(r"<[^>]+>", "", text)
                    text = _strip(text)
                    for part in re.split(r"\s*/\s*", text):
                        m2 = re.match(r"(.+?)[:：]\s*(.+)", part)
                        if not m2:
                            continue
                        label = _strip(m2.group(1))
                        val = _strip(m2.group(2))
                        if "主演" in label and not vod["vod_actor"]:
                            vod["vod_actor"] = val
                        elif "导演" in label and not vod["vod_director"]:
                            vod["vod_director"] = val
                        elif "类型" in label and not vod["vod_class"]:
                            vod["vod_class"] = val
                        elif "地区" in label and not vod["vod_area"]:
                            vod["vod_area"] = val
                        elif "年份" in label and not vod["vod_year"]:
                            vod["vod_year"] = val
                        elif "语言" in label and not vod["vod_lang"]:
                            vod["vod_lang"] = val
                        elif ("更新" in label or "状态" in label or "备注" in label) and not vod["vod_remarks"]:
                            vod["vod_remarks"] = val

            # FIX: 简介优先取 <p class="desc">，降级取 <span class="detail-content">
            m = self._RE_DETAIL_DESC.search(html)
            if not m:
                m = self._RE_DETAIL_DESC2.search(html)
            if m:
                txt = re.sub(r"<[^>]*>", "", m.group(1))
                vod["vod_content"] = _strip(txt)[:500]

            play_from, play_url = self._collect_playlist(html)
            if play_from:
                vod["vod_play_from"] = "$$$".join(play_from)
                vod["vod_play_url"] = "$$$".join(play_url)

            payload = {"list": [vod]}
            with self._cache_lock:
                self._cache[cache_key] = (now, payload)
            return payload
        except Exception as e:
            print("[红果] detailContent 异常: " + str(e))
            return {"list": []}

    def _collect_playlist(self, html):
        play_from, play_url = [], []
        blocks = self._RE_PLAYLIST.findall(html)
        if not blocks:
            # 尝试更宽匹配
            blocks = re.findall(r'<ul[^>]*class="[^"]*playlist[^"]*"[^>]*>([\s\S]*?)</ul>', html)

        # FIX: 从 tab 链接提取真实线路名称（如 "茶杯狐"、"策驰影院"）
        tab_names = {}
        for tm in self._RE_PLAY_TAB.finditer(html):
            tab_names[int(tm.group(1))] = _strip(tm.group(2))

        for idx, chunk in enumerate(blocks):
            eps_raw = []
            seen = set()
            for em in self._RE_PLAY_EP.finditer(chunk):
                path = em.group(1)
                sid = em.group(3)
                nid = em.group(4)
                ep_name = _strip(_unescape(re.sub(r"<[^>]*>", "", em.group(5)))) or ("第" + nid + "集")
                key = path
                if key in seen:
                    continue
                seen.add(key)
                eps_raw.append((int(nid), ep_name, path))
            eps_raw.sort(key=lambda x: x[0])
            eps = [name + "$" + path for _, name, path in eps_raw]
            if eps:
                if idx in tab_names:
                    src_name = tab_names[idx]
                elif len(blocks) > 1:
                    src_name = "线路" + str(idx + 1)
                else:
                    src_name = "播放"
                play_from.append(src_name)
                play_url.append("#".join(eps))
        return play_from, play_url

    # ------------------------------------------------------------------
    # 搜索 (多路径兼容)
    # ------------------------------------------------------------------
    def searchContent(self, key, quick, pg="1"):
        try:
            page = int(pg or 1)
            if page < 1:
                page = 1
            cache_key = ("search", key, page)
            now = time.time()
            with self._cache_lock:
                hit = self._cache.get(cache_key)
                if hit and now - hit[0] < SEARCH_CACHE_TTL:
                    return hit[1]

            kw = _urlencode(key)
            # 苹果CMS标准搜索路径 (多种模板兼容)
            search_urls = [
                HOST + "/vodsearch/" + kw + "-------------.html",
                HOST + "/vodsearch/-------------.html?wd=" + kw + "&page=" + str(page),
                HOST + "/search/-------------.html?wd=" + kw + "&page=" + str(page),
                HOST + "/index.php/vod/search.html?wd=" + kw + "&page=" + str(page),
            ]

            html = ""
            for url in search_urls:
                html = self._http_get(url, timeout=10)
                if html and len(html) > 3000:
                    break

            if not html:
                return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}

            videos = self._parse_vod_items(html)
            # 搜索页通常没有明确分页，根据结果数量估算
            total = len(videos)
            pagecount = 1
            # 如果有分页链接
            for n in re.findall(r'/vodsearch/[^"]*_(\d+)\.html', html):
                pagecount = max(pagecount, int(n))

            payload = {
                "list": videos,
                "page": page,
                "pagecount": pagecount,
                "limit": len(videos) or 20,
                "total": total,
            }
            with self._cache_lock:
                self._cache[cache_key] = (now, payload)
            return payload
        except Exception as e:
            print("[红果] searchContent 异常: " + str(e))
            return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}

    # ------------------------------------------------------------------
    # 播放
    # ------------------------------------------------------------------
    def _extract_player_aaaa(self, html):
        if not html:
            return None
        m = self._RE_PLAYER_JSON.search(html)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        # 兜底: 大括号计数
        idx = html.find("player_aaaa")
        if idx < 0:
            return None
        brace_start = html.find("{", idx)
        if brace_start < 0:
            return None
        depth = 0
        for i in range(brace_start, len(html)):
            c = html[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(html[brace_start:i + 1])
                    except Exception:
                        return None
        return None

    def playerContent(self, flag, id, vipFlags):
        play_path = str(id or "")
        if not play_path:
            return {"parse": 0, "url": ""}

        if self.isVideoFormat(play_path):
            return {"parse": 0, "url": play_path, "header": {"User-Agent": UA, "Referer": HOST + "/"}}

        # FIX: 站点播放链接用 /screen/ 路由，兼容 /play/
        if "/play/" in play_path or "/screen/" in play_path:
            if play_path.startswith("http"):
                play_url = play_path
            else:
                play_url = HOST + play_path

            html = self._http_get(play_url, timeout=10)
            if not html:
                print("[红果] play页请求为空: " + play_url)

            # 1) 尝试标准 player_aaaa (苹果CMS)
            player = self._extract_player_aaaa(html)
            if player:
                real_url = player.get("url", "")
                if real_url and real_url.startswith("http"):
                    return {
                        "parse": 0,
                        "url": real_url,
                        "header": {
                            "User-Agent": UA,
                            "Referer": HOST + "/",
                        },
                    }
                if real_url:
                    print("[红果] player_aaaa.url 非直链: " + str(real_url[:80]))

            # FIX: 2) /screen/ 页通过 playerUrl JS 变量嵌入真实 m3u8/mp4 地址
            m = self._RE_PLAYER_URL.search(html)
            if m:
                real_url = m.group(1)
                if real_url and real_url.startswith("http"):
                    if self.isVideoFormat(real_url):
                        return {
                            "parse": 0,
                            "url": real_url,
                            "header": {
                                "User-Agent": UA,
                                "Referer": HOST + "/",
                            },
                        }
                    # 非直链视频，走站内解析接口
                    parser_url = HOST + "/jx/index.html?url=" + real_url
                    return {
                        "parse": 1,
                        "url": parser_url,
                        "header": {
                            "User-Agent": UA,
                            "Referer": HOST + "/",
                        },
                    }

            # FIX: 3) 兜底搜索页面中的 m3u8/mp4 直链
            m = self._RE_VIDEO_URL.search(html)
            if m:
                real_url = m.group(1)
                return {
                    "parse": 0,
                    "url": real_url,
                    "header": {
                        "User-Agent": UA,
                        "Referer": HOST + "/",
                    },
                }

            # 降级嗅探
            print("[红果] 解析失败, 降级嗅探: " + play_url)
            return {
                "parse": 1,
                "url": play_url,
                "header": {
                    "User-Agent": UA,
                    "Referer": HOST + "/",
                }
            }

        return {"parse": 0, "url": play_path, "header": {"User-Agent": UA, "Referer": HOST + "/"}}

    def localProxy(self, param):
        return [200, "video/MP2T", b"", ""]
