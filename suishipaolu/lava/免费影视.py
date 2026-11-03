# -*- coding: utf-8 -*-
"""
免费追剧 - https://zhuiju.pages.dev
TVBox / FongMi / CatVod 站点源插件（MacCMS 聚合站，纯 JSON API，无需解密）

============================== 分类与线路来源说明 ==============================
本插件的一级分类、二级分类、播放线路，全部按网站（zhuiju.pages.dev）自身的结构和数据照搬，
没有自造分类。来源如下：

【一级分类】= 国产剧 / 韩剧 / 日剧 / 美剧 / 英剧（这 5 个本身就是网站首页 chips 里的入口）

【分类内容】= 每个分类都装满站内真实内容，两路合并且按片名去重（同名保留真片源那一条）
  1. /api/douban-hot?type=<分类>  网站该频道原生的豆瓣榜单（50 条）
  2. 全站索引里归入该分类的站内条目 —— 索引用 A-Z + 0-9 + 高频词并发搜索建立，
     一次拿全站几千条，再按 CATEGORY_TYPES（type_name）+ CATEGORY_AREAS（vod_area）归类。
     注：站内 60.6% 的条目 vod_area 是空的，所以主要靠 type_name 归类。
     注：泰剧/泰国剧/马泰剧 不属于这 5 个分类，只在搜索里出现。

【性能优化】
  加载：连接池放大到 64；常规并发 4→12、索引并发 24；请求最小间隔 0.35→0.1s；
        接口缓存 5→10 分钟、索引缓存 30 分钟；init() 里就后台预建索引。
  播放：直连 m3u8 线路排到最前（DIRECT_FIRST），默认线路点开即播；
        *yun 线路实测 12/12 可以直接拼 /index.m3u8，因此【零请求】解析，省掉一次 HTTP 往返；
        详情返回后后台预解析首条线路首集（PREFETCH）；播放页解析超时 12→8s。

【二级分类】= 网站数据里真实存在的 64 个 type_name（实测全量采样，无遗漏、无杜撰）
  电影解说 / 日韩动漫 / 篮球 / 日韩综艺 / 大陆综艺 / 剧情片 / 日本动漫 / 足球 / 喜剧片 /
  现代都市 / 中国动漫 / 日本剧 / 国产剧 / 欧美剧 / 动作片 / 韩国剧 / 记录片 / 港台综艺 /
  香港剧 / 纪录片 / 恐怖片 / 短剧 / AI漫剧 / 日剧 / 爱情片 / 国产动漫 / 台湾剧 / 动画片 /
  动漫电影 / 泰国剧 / 短剧大全 / 欧美综艺 / 科幻片 / 古装仙侠 / 伦理片 / 韩剧 / 战争片 /
  反转爽剧 / 脑洞悬疑 / 欧美动漫 / 内地剧 / 言情总裁 / 穿越年代 / 泰剧 / 网球 / 预告片 /
  斯诺克 / 马泰剧 / 理论片 / 悬疑片 / 现代言情 / 反转爽文 / 犯罪片 / 港澳剧 / 海外剧 /
  重生民国 / 里番动漫 / 都市脑洞 / 港台动漫 / 大陆剧 / 奇幻片 / 连续剧 / 海外动漫 / 其他赛事

【播放线路】= 网站播放页 source-tabs 里显示的全部 12 条线路（vod_play_from 原值，不改名）
  liangzi / lzm3u8 / hnyun / hnm3u8 / bfzym3u8 / jsyun / jsm3u8 / hhyun / hhm3u8 /
  iqym3u8 / xlyun / xlm3u8
  对应 7 个数据源：lz / hn / bf / js / hh / iq / xl
  源 -> 线路（实测）：
    lz -> liangzi + lzm3u8    hn -> hnyun + hnm3u8    bf -> bfzym3u8
    js -> jsyun + jsm3u8      hh -> hhyun + hhm3u8    iq -> iqym3u8
    xl -> xlyun + xlm3u8
  网站播放页只过滤 xiguam3u8（源码：e.filter(s=>s!=="xiguam3u8)），本插件同样过滤。
  注意：liangzi 只在 /api/detail?form=lz 里出现，搜索接口只给 lzm3u8，所以详情必须回查 lz 详情。

============================== 接口实测结论 ==============================
1. 纯前端 SPA（Cloudflare Pages），数据全部来自 /api/*，无 HTML 解析、无验证码、无 Cookie 预热。
2. /api/search?key=          影视搜索，一次最多 60 条（多源聚合，同片会同时出现在多个源里）。
3. /api/detail?ids=&form=    精确详情；搜索结果里 play_url 为 null 的条目必须用它兜底。
4. /api/douban-hot?type=&limit=50  豆瓣榜单，limit 上限 50；未知 type 会回退到「热门」。
5. /api/search-rank?range=   热搜词榜；/api/daily 每日推荐。
6. 播放地址都是 m3u8；liangzi 与 hn/js/hh/xl 的 *yun 线路给的是无扩展名网页地址，需取 /index.m3u8。
7. 重要：vod_id 不跨源通用！同一个 id 在不同 form 下是不同片子，只能按「片名完全一致」跨源合并线路。
8. /api/douban-hot 返回的 genres 是空数组，豆瓣榜单没有题材数据；所以用户一旦在豆瓣
   频道上选了类型/年份/地区/语言等筛选，插件会把榜单片名批量换成站内真实条目再筛。
"""

import re
import json
import time
import threading
from html import unescape
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from base.spider import Spider


class Spider(Spider):
    # ==================== 基础配置 ====================
    name = "免费追剧"
    base_url = "https://zhuiju.pages.dev"
    site_url = "https://zhuiju.pages.dev"

    searchable = 1  # 支持搜索
    quickSearch = 1  # 支持聚合快搜
    filterable = 1  # 支持筛选（二级分类）
    changeable = 1  # 支持换源聚合

    PAGE_SIZE = 24
    CACHE_TTL = 600  # 接口/列表缓存 10 分钟
    MAX_WORKERS = 12  # 常规并发取数据的线程数
    INDEX_WORKERS = 24  # 建全站索引时的并发（索引是一次几十个关键词的批量请求）
    INDEX_TTL = 1800  # 全站索引缓存 30 分钟
    REQ_TIMEOUT = 12  # 接口超时
    PLAY_TIMEOUT = 8  # 播放页解析超时
    DIRECT_FIRST = True  # 详情里把直连 m3u8 线路排在最前，起播最快
    PREFETCH = True  # 详情返回后后台预解析首条线路首集

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://zhuiju.pages.dev/",
    }
    PLAY_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Referer": "https://zhuiju.pages.dev/",
        "Accept": "*/*",
    }

    # ==================== 一级分类：5 个（按用户要求） ====================
    # (tid, 显示名, /api/douban-hot 的 type 参数)
    # 「国产剧/韩剧/日剧/美剧/英剧」本身就是网站首页 chips 里的 5 个入口
    HOME_CHIPS = [
        ("cn", "国产剧", "国产剧"),
        ("kr", "韩剧", "韩剧"),
        ("jp", "日剧", "日剧"),
        ("us", "美剧", "美剧"),
        ("uk", "英剧", "英剧"),
    ]
    DOUBAN_TYPES = {tid: t for tid, _, t in HOME_CHIPS}
    HOME_HOT = "热门"  # 网站首页 chips 第 1 项 key=热门、label=近期热播，首页推荐用它

    # ==================== 全站索引：把网站所有内容灌进这 5 个分类 ====================
    # 站内 60% 的条目 vod_area 是空的，所以主要靠 type_name 归类，area 只在有值时兜底
    # fmt: off
    CATEGORY_TYPES = {
        "cn": [
            "国产剧", "大陆剧", "内地剧", "香港剧", "台湾剧", "港澳剧",
            "国产动漫", "中国动漫", "港台动漫", "大陆综艺", "港台综艺",
            "古装仙侠", "现代都市", "言情总裁", "穿越年代", "现代言情",
            "反转爽文", "重生民国", "都市脑洞", "反转爽剧", "脑洞悬疑",
            "短剧", "短剧大全", "AI漫剧", "电影解说",
            "剧情片", "喜剧片", "动作片", "爱情片", "科幻片", "恐怖片",
            "战争片", "犯罪片", "悬疑片", "奇幻片", "伦理片", "理论片",
            "纪录片", "记录片", "预告片", "连续剧", "动画片", "动漫电影",
            "篮球", "足球", "网球", "斯诺克", "其他赛事",
        ],
        "kr": ["韩剧", "韩国剧", "日韩综艺", "日韩动漫"],
        "jp": ["日剧", "日本剧", "日本动漫", "日韩综艺", "日韩动漫"],
        "us": ["美剧", "欧美剧", "欧美综艺", "欧美动漫", "海外剧"],
        "uk": ["英剧", "欧美剧", "欧美综艺", "欧美动漫"],
    }
    CATEGORY_AREAS = {
        "cn": ["大陆", "中国大陆", "香港", "中国香港", "台湾"],
        "kr": ["韩国"],
        "jp": ["日本"],
        "us": ["美国"],
        "uk": ["英国"],
    }
    # fmt: on
    # 建索引用的关键词：A-Z + 0-9 + 站内高频词。索引一次拿到几千条，再按上面规则分到 5 个分类
    INDEX_KEYS = (
        [chr(c) for c in range(ord("a"), ord("z") + 1)]
        + [str(d) for d in range(10)]
        + [
            "我的",
            "你",
            "他",
            "中国",
            "大",
            "小",
            "之",
            "王",
            "少",
            "年",
            "爱",
            "情",
            "传",
            "说",
            "世",
            "界",
            "战",
            "神",
            "天",
            "龙",
        ]
    )
    # 泰剧 / 泰国剧 / 马泰剧 不属于这 5 个分类，只在搜索里出现
    EXCLUDE_TYPES = {"泰剧", "泰国剧", "马泰剧"}

    # ==================== 播放源与线路（网站实测全量） ====================
    # 7 个数据源，按站内出现频次排序
    ALL_SOURCES = ["lz", "hn", "bf", "js", "hh", "iq", "xl"]
    # 12 条线路（vod_play_from 原值，按数据源分组）。网站播放页只过滤 xiguam3u8
    ALL_LINES = [
        "liangzi",
        "lzm3u8",
        "hnyun",
        "hnm3u8",
        "bfzym3u8",
        "jsyun",
        "jsm3u8",
        "hhyun",
        "hhm3u8",
        "iqym3u8",
        "xlyun",
        "xlm3u8",
    ]
    SKIP_LINES = {"xiguam3u8"}
    # 本身就是 m3u8 直链的线路（无需二次解析）。DIRECT_FIRST=True 时这些排在前面，
    # 这样默认线路点开即播；*yun 与 liangzi 需要多一步解析，排在后面备用。
    DIRECT_LINES = ["lzm3u8", "hnm3u8", "jsm3u8", "hhm3u8", "xlm3u8", "iqym3u8", "bfzym3u8"]
    # 线路 -> 所属数据源（liangzi 只在 lz 的详情里出现，列表层靠源来筛）
    LINE_SOURCE = {
        "liangzi": "lz",
        "lzm3u8": "lz",
        "hnyun": "hn",
        "hnm3u8": "hn",
        "bfzym3u8": "bf",
        "jsyun": "js",
        "jsm3u8": "js",
        "hhyun": "hh",
        "hhm3u8": "hh",
        "iqym3u8": "iq",
        "xlyun": "xl",
        "xlm3u8": "xl",
    }
    # 线路中文别名（可选）：把 USE_LINE_ALIAS 改成 True 就会用中文名显示线路
    USE_LINE_ALIAS = False
    LINE_ALIAS = {
        "liangzi": "量子·云播",
        "lzm3u8": "量子·直连",
        "hnyun": "华南·云播",
        "hnm3u8": "华南·直连",
        "bfzym3u8": "非凡·直连",
        "jsyun": "极速·云播",
        "jsm3u8": "极速·直连",
        "hhyun": "黄河·云播",
        "hhm3u8": "黄河·直连",
        "iqym3u8": "爱奇艺",
        "xlyun": "迅雷·云播",
        "xlm3u8": "迅雷·直连",
    }

    # ==================== 二级分类：网站真实 type_name 全量（64 个） ====================
    # fmt: off
    ALL_TYPES = [
        "电影解说", "日韩动漫", "篮球", "日韩综艺", "大陆综艺", "剧情片", "日本动漫", "足球",
        "喜剧片", "现代都市", "中国动漫", "日本剧", "国产剧", "欧美剧", "动作片", "韩国剧",
        "记录片", "港台综艺", "香港剧", "纪录片", "恐怖片", "短剧", "AI漫剧", "日剧",
        "爱情片", "国产动漫", "台湾剧", "动画片", "动漫电影", "泰国剧", "短剧大全", "欧美综艺",
        "科幻片", "古装仙侠", "伦理片", "韩剧", "战争片", "反转爽剧", "脑洞悬疑", "欧美动漫",
        "内地剧", "言情总裁", "穿越年代", "泰剧", "网球", "预告片", "斯诺克", "马泰剧",
        "理论片", "悬疑片", "现代言情", "反转爽文", "犯罪片", "港澳剧", "海外剧", "重生民国",
        "里番动漫", "都市脑洞", "港台动漫", "大陆剧", "奇幻片", "连续剧", "海外动漫", "其他赛事",
    ]

    # 筛选公共选项：年份/地区/语言全部取自站内真实字段（实测采样，无杜撰）
    YEARS = [str(y) for y in range(2026, 1989, -1)]
    AREAS = [
        "大陆", "中国大陆", "香港", "中国香港", "台湾", "美国", "英国", "日本",
        "韩国", "泰国", "法国", "新加坡", "俄罗斯", "西班牙", "其它",
    ]
    LANGS = ["国语", "普通话", "汉语普通话", "粤语", "英语", "日语", "韩语", "泰语", "法语", "其它"]
    SORTS = [{"n": "默认", "v": ""}, {"n": "评分高", "v": "score"},
             {"n": "年份新", "v": "year"}, {"n": "集数多", "v": "eps"}]
    # 注意：豆瓣榜单接口返回的 genres 是空数组，所以没有「豆瓣题材」这一说，
    # 所有一级分类的「类型」筛选统一用上面 64 个站内真实 type_name。
    # fmt: on

    def __init__(self):
        super().__init__()
        self._session = requests.Session()
        # 连接池放大：索引/详情都是几十个并发请求，默认 10 条连接会成为瓶颈
        adapter = HTTPAdapter(pool_connections=64, pool_maxsize=64, max_retries=0)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
        self._session.headers.update(self.HEADERS)
        self._api_cache = {}  # url -> (ts, data)
        self._item_cache = {}  # vod_id -> 原始条目
        self._raw_by_name = {}  # 片名 -> [原始条目]（跨源合并线路用，不去重）
        self._list_cache = {}  # 频道缓存 key -> (ts, items)
        self._play_cache = {}  # 播放页 url -> m3u8
        self._lock = threading.Lock()
        self._index_lock = threading.RLock()  # 索引专用锁，避免和限速锁互相干扰
        self._indexing = False
        self._last_req = 0.0
        self._min_interval = 0.1
        self._re_m3u8 = re.compile(r'[\'"](https?://[^\'"\s<>]+\.m3u8[^\'"\s<>]*)[\'"]')
        # liangzi 分享页：var main = "/xxx/index.m3u8?sign=..."; var hosts = "";
        self._re_main = re.compile(r"var\s+main\s*=\s*['\"]([^'\"]+)['\"]")
        self._re_hosts = re.compile(r"var\s+hosts\s*=\s*['\"]([^'\"]*)['\"]")
        self._re_media = re.compile(r"\.(m3u8|mp4|flv|ts|mkv)(?:[?#]|$)", re.I)
        # 云播页：https://xxx/play/<token>（无扩展名）
        self._re_play_page = re.compile(r"^https?://[^/]+/play/[A-Za-z0-9_-]+/?$")

    # ==================== 通用工具 ====================
    def _log(self, msg):
        print("[%s] %s" % (self.name, msg))

    def _throttle(self):
        with self._lock:
            gap = time.time() - self._last_req
            wait = self._min_interval - gap
            self._last_req = time.time()
        if 0 < wait < 2:
            time.sleep(wait)

    def _api(self, path, retry=2, timeout=None):
        """站内 JSON 接口，带缓存/重试/限速。失败返回 {}"""
        url = self.base_url + path
        now = time.time()
        hit = self._api_cache.get(url)
        if hit and now - hit[0] < self.CACHE_TTL:
            return hit[1]
        timeout = timeout or self.REQ_TIMEOUT
        for attempt in range(retry):
            try:
                self._throttle()
                resp = self._session.get(url, timeout=timeout)
                if resp.status_code in (429, 503):
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if resp.status_code != 200:
                    time.sleep(0.8)
                    continue
                data = resp.json()
                self._api_cache[url] = (time.time(), data)
                return data
            except Exception as e:
                self._log("接口异常 %s: %s" % (path, e))
                time.sleep(1.0 + attempt)
        self._log("接口失败: " + path)
        return {}

    def _parallel(self, func, args, workers=None):
        """并发执行并保留顺序"""
        if not args:
            return []
        with ThreadPoolExecutor(max_workers=max(1, workers or min(self.MAX_WORKERS, len(args)))) as pool:
            return list(pool.map(func, args))

    def _clean(self, text):
        """去标签/多空格，并还原 HTML 实体（站内数据里常见 &#039; &amp; 等）"""
        if not text:
            return ""
        text = unescape(str(text))
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _safe_url(url):
        """播放地址里可能带中文路径（如 /第01集/index.m3u8），统一做百分号编码"""
        if not url:
            return ""
        if not any(ord(c) > 127 for c in url):
            return url
        return quote(url, safe=":/?#[]@!$&'()*+,;=%~")

    @staticmethod
    def _to_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    # ==================== 条目标准化 ====================
    def _norm_vod(self, x):
        """MacCMS 条目 -> 列表卡片"""
        src = x.get("_api_source") or ""
        vid = x.get("vod_id")
        name = self._clean(x.get("vod_name"))
        if not name or not vid:
            return None
        vod_id = "%s@%s" % (vid, src)
        self._item_cache[vod_id] = x
        year = self._clean(x.get("vod_year"))
        play_url = x.get("vod_play_url") or ""
        lines = [ln for ln in self._split_multi(x.get("vod_play_from")) if ln not in self.SKIP_LINES]
        return {
            "vod_id": vod_id,
            "vod_name": name,
            "vod_pic": self._abs_pic(x.get("vod_pic")),
            "vod_remarks": self._clean(x.get("vod_remarks")) or year,
            "_type": self._clean(x.get("type_name")),
            "_year": year,
            "_area": self._clean(x.get("vod_area")),
            "_lang": self._clean(x.get("vod_lang")),
            "_src": src,
            "_lines": ",".join(lines),
            "_score": self._to_float(x.get("vod_score") or x.get("vod_douban_score")),
            "_eps": play_url.count("#") + 1 if play_url else 0,
        }

    def _norm_douban(self, x):
        """豆瓣榜单条目 -> 列表卡片（无播放源，进详情时再匹配真实片源）"""
        title = self._clean(x.get("title"))
        if not title:
            return None
        genres = x.get("genres") or []
        if isinstance(genres, str):
            genres = [g for g in re.split(r"[/,\s]", genres) if g]
        return {
            "vod_id": "db::%s" % title,
            "vod_name": title,
            "vod_pic": self._abs_pic(x.get("pic")),
            "vod_remarks": (self._clean(x.get("rating")) and "%s分" % x.get("rating")) or "",
            "_type": "/".join(genres),
            "_year": self._clean(x.get("year")),
            "_area": "",
            "_lang": "",
            "_src": "douban",
            "_score": self._to_float(x.get("rating")),
            "_eps": 0,
        }

    def _abs_pic(self, pic):
        pic = self._clean(pic)
        if pic.startswith("//"):
            return "https:" + pic
        if pic and not pic.startswith("http"):
            return self.base_url + "/" + pic.lstrip("/")
        return pic

    def _vid_key(self, item):
        """去重键：只看片名（跨源年份字段常不一致，按年份去重会漏掉重复源）"""
        return re.sub(r"[\s:：·\-_—（）()【】\[\]]+", "", item.get("vod_name") or "").lower()

    def _dedup(self, items):
        """按片名去重，保留集数最多的一条"""
        best = {}
        for it in items:
            if not it:
                continue
            k = self._vid_key(it)
            old = best.get(k)
            if old is None or it.get("_eps", 0) > old.get("_eps", 0):
                best[k] = it
        return list(best.values())

    # ==================== 数据抓取 ====================
    def _search_raw(self, keyword):
        """搜索接口，返回标准化条目（带缓存）"""
        key = self._clean(keyword)
        if not key:
            return []
        cache_key = "search::" + key
        hit = self._list_cache.get(cache_key)
        if hit and time.time() - hit[0] < self.CACHE_TTL:
            return hit[1]
        data = self._api("/api/search?key=" + quote(key))
        items = []
        raws = []
        for x in data.get("list") or []:
            item = self._norm_vod(x)
            if item:
                items.append(item)
            raws.append(x)
        # 保留未去重的原始条目：详情页要靠它把同一部片在 7 个源上的线路全部取出
        self._raw_by_name[key] = raws
        items = self._dedup(items)
        self._list_cache[cache_key] = (time.time(), items)
        return items

    def _search_many(self, keywords, workers=None):
        """多关键词并发搜索后合并去重"""
        results = self._parallel(self._search_raw, list(keywords), workers)
        merged = []
        for group in results:
            merged.extend(group or [])
        return self._dedup(merged)

    def _douban_raw(self, dtype):
        cache_key = "douban::" + dtype
        hit = self._list_cache.get(cache_key)
        if hit and time.time() - hit[0] < self.CACHE_TTL:
            return hit[1]
        data = self._api("/api/douban-hot?type=%s&limit=50" % quote(dtype))
        items = []
        for x in data.get("list") or []:
            item = self._norm_douban(x)
            if item:
                items.append(item)
        items = self._dedup(items)
        self._list_cache[cache_key] = (time.time(), items)
        return items

    def _index_ready(self):
        hit = self._list_cache.get("index")
        return hit[1] if hit and time.time() - hit[0] < self.INDEX_TTL else None

    def _index_all(self):
        """建全站索引：几十个关键词并发搜索后去重，一次拿到站内几千条真实条目。

        用独立锁 + 二次检查，保证后台预建和用户请求之间只真正建一次；
        建索引期间关掉全局限速（并发数本身就是限流，实测 24 并发约 3.3s）。
        """
        ready = self._index_ready()
        if ready is not None:
            return ready
        with self._index_lock:  # 后台正在建时，这里会等它建完，不重复发请求
            ready = self._index_ready()
            if ready is not None:
                return ready
            t0 = time.time()
            self._log("建立站内全量索引 (%d 个关键词)…" % len(self.INDEX_KEYS))
            old_gap = self._min_interval
            self._min_interval = 0
            try:
                items = self._dedup(self._search_many(self.INDEX_KEYS, workers=self.INDEX_WORKERS))
            finally:
                self._min_interval = old_gap
            self._list_cache["index"] = (time.time(), items)
            self._log("索引完成 %d 条，用时 %.1fs" % (len(items), time.time() - t0))
            return items

    def _index_bg(self):
        """后台建索引，不阻塞当前请求"""
        if self._index_ready() is not None:
            return
        with self._lock:
            if self._indexing:
                return
            self._indexing = True

        def run():
            try:
                self._index_all()
            finally:
                with self._lock:
                    self._indexing = False

        threading.Thread(target=run, daemon=True).start()

    def _in_category(self, item, tid):
        """站内条目是否属于某个一级分类：先按 type_name，再按 vod_area"""
        tname = item.get("_type") or ""
        if tname in self.EXCLUDE_TYPES:
            return False
        if tname in self.CATEGORY_TYPES.get(tid, ()):
            return True
        area = item.get("_area") or ""
        return any(v in area for v in self.CATEGORY_AREAS.get(tid, ()))

    def _channel_raw(self, tid):
        """一级分类内容 = 网站该频道的豆瓣榜单 + 站内全量索引里归入该分类的所有条目"""
        if tid not in self.DOUBAN_TYPES:
            return self._search_raw(tid)
        douban = self._douban_raw(self.DOUBAN_TYPES[tid])
        items = self._index_all()
        inner = [i for i in items if self._in_category(i, tid)]
        # 同名条目保留站内真片源那一条（豆瓣条目 _eps=0，会被挤掉）
        return self._dedup(douban + inner)

    # ==================== 二级分类（筛选） ====================
    FILTER_KEYS = ("tid", "year", "area", "lang", "src")

    def _has_filter(self, flt):
        """豆瓣榜单条目没有 type/year/area/lang，只有用户真的选了筛选时才去换成站内真实条目"""
        return any(self._clean(flt.get(k)) for k in self.FILTER_KEYS)

    def _resolve_titles(self, titles):
        """豆瓣片名 -> 站内真实条目（批量并发，临时放宽限速，只在用户下筛选时触发）"""
        titles = [t for t in titles if t][:50]
        if not titles:
            return []
        old_gap, old_workers = self._min_interval, self.MAX_WORKERS
        self._min_interval, self.MAX_WORKERS = 0.02, 16
        try:
            self._log("按筛选条件回查站内片源 (%d 部)…" % len(titles))
            return self._dedup(self._search_many(titles, workers=16))
        finally:
            self._min_interval, self.MAX_WORKERS = old_gap, old_workers

    def _build_filters(self, tid):
        """每个一级分类都挂一套二级筛选：类型用站内真实的 64 个 type_name"""
        subs = self.ALL_TYPES
        return [
            {
                "key": "tid",
                "name": "类型",
                "value": [{"n": "全部", "v": ""}] + [{"n": s, "v": s} for s in subs],
            },
            {
                "key": "year",
                "name": "年份",
                "value": [{"n": "全部", "v": ""}] + [{"n": y, "v": y} for y in self.YEARS],
            },
            {
                "key": "area",
                "name": "地区",
                "value": [{"n": "全部", "v": ""}] + [{"n": a, "v": a} for a in self.AREAS],
            },
            {
                "key": "lang",
                "name": "语言",
                "value": [{"n": "全部", "v": ""}] + [{"n": g, "v": g} for g in self.LANGS],
            },
            {
                "key": "src",
                "name": "线路",
                "value": [{"n": "全部", "v": ""}] + [{"n": self._line_name(k), "v": k} for k in self.ALL_LINES],
            },
            {"key": "by", "name": "排序", "value": self.SORTS},
        ]

    def _line_name(self, line):
        """线路显示名：默认用网站原始名，USE_LINE_ALIAS=True 时用中文名"""
        if self.USE_LINE_ALIAS:
            return self.LINE_ALIAS.get(line, line)
        return line

    def _match_line(self, item, line):
        """线路筛选：先按线路名匹配；liangzi 这类只在详情出现的线路，按所属数据源匹配"""
        if line in (item.get("_lines") or ""):
            return True
        want = self.LINE_SOURCE.get(line)
        return bool(want) and want == (item.get("_src") or "")

    def _apply_filters(self, items, flt):
        if not flt:
            return items
        sub = self._clean(flt.get("tid"))
        year = self._clean(flt.get("year"))
        area = self._clean(flt.get("area"))
        lang = self._clean(flt.get("lang"))
        src = self._clean(flt.get("src"))
        by = self._clean(flt.get("by"))

        out = []
        for it in items:
            if sub and sub not in (it.get("_type") or ""):
                continue
            if year and (it.get("_year") or "") != year:
                continue
            if area and area not in (it.get("_area") or ""):
                continue
            if lang and lang not in (it.get("_lang") or ""):
                continue
            if src and not self._match_line(it, src):
                continue
            out.append(it)

        if by == "score":
            out.sort(key=lambda v: -v.get("_score", 0))
        elif by == "year":
            out.sort(key=lambda v: (v.get("_year") or ""), reverse=True)
        elif by == "eps":
            out.sort(key=lambda v: -v.get("_eps", 0))
        return out

    # ==================== TVBox 核心方法 ====================
    def init(self, extend=""):
        # 初始化就把全站索引在后台建起来，用户点进分类时基本已经就绪
        try:
            self._index_bg()
        except Exception as e:
            self._log("后台索引启动失败: %s" % e)
        self._log("初始化完成")

    def homeContent(self, filter=False):
        classes = [{"type_id": tid, "type_name": label} for tid, label, _ in self.HOME_CHIPS]

        result = {"class": classes}
        if filter:
            filters = {}
            for c in classes:
                filters[c["type_id"]] = self._build_filters(c["type_id"])
            result["filters"] = filters
            result["filter"] = filters
        return result

    def homeVideoContent(self):
        """首页推荐 = 网站首页默认的「近期热播」豆瓣榜单（1 个请求，秒开）"""
        try:
            items = self._douban_raw(self.HOME_HOT)
            return {"list": self._to_cards(items[: self.PAGE_SIZE])}
        except Exception as e:
            self._log("homeVideoContent异常: %s" % e)
            return {"list": []}

    def categoryContent(self, tid, pg, filter=False, content=None):
        try:
            pg = max(1, int(pg or 1))
        except (TypeError, ValueError):
            pg = 1
        try:
            flt = {}
            if content:
                flt = json.loads(content) if isinstance(content, str) else content
            items = self._channel_raw(tid)
            # 豆瓣榜单条目只有片名/评分，没有 type/year/area/lang，筛选时必然不匹配。
            # 分类里真条目够多时直接丢掉它们（秒出）；真条目很少（索引还没建好）才回查。
            if self._has_filter(flt):
                real = [i for i in items if not str(i.get("vod_id", "")).startswith("db::")]
                dbt = [i for i in items if str(i.get("vod_id", "")).startswith("db::")]
                if dbt and len(real) < 30:
                    items = self._resolve_titles([i.get("vod_name") for i in dbt]) or items
                else:
                    items = real
            items = self._apply_filters(items, flt)

            total = len(items)
            pagecount = max(1, (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
            start = (pg - 1) * self.PAGE_SIZE
            return {
                "list": self._to_cards(items[start : start + self.PAGE_SIZE]),
                "page": pg,
                "pagecount": pagecount,
                "limit": self.PAGE_SIZE,
                "total": total,
            }
        except Exception as e:
            self._log("categoryContent异常: %s" % e)
            return {"list": [], "page": pg, "pagecount": 1, "limit": self.PAGE_SIZE, "total": 0}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            pg = max(1, int(pg or 1))
        except (TypeError, ValueError):
            pg = 1
        keyword = self._clean(key)
        if not keyword:
            return {"page": pg, "pagecount": 1, "limit": self.PAGE_SIZE, "total": 0, "list": []}
        try:
            items = self._search_raw(keyword)
            if not quick:
                low = keyword.lower()

                def score(it):
                    n = (it.get("vod_name") or "").lower()
                    if n == low:
                        return 0
                    if n.startswith(low):
                        return 1
                    if low in n:
                        return 2
                    return 3

                items = sorted(items, key=score)
            total = len(items)
            pagecount = max(1, (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
            start = (pg - 1) * self.PAGE_SIZE
            return {
                "list": self._to_cards(items[start : start + self.PAGE_SIZE]),
                "page": pg,
                "pagecount": pagecount,
                "limit": self.PAGE_SIZE,
                "total": total,
            }
        except Exception as e:
            self._log("searchContent异常: %s" % e)
            return {"list": [], "page": pg, "pagecount": 1, "limit": self.PAGE_SIZE, "total": 0}

    @staticmethod
    def _to_cards(items):
        """只把标准字段交给壳子，下划线字段不下发"""
        cards = []
        for it in items:
            cards.append(
                {
                    "vod_id": it["vod_id"],
                    "vod_name": it["vod_name"],
                    "vod_pic": it.get("vod_pic", ""),
                    "vod_remarks": it.get("vod_remarks", ""),
                }
            )
        return cards

    # ==================== 详情：把网站全部线路都写出来 ====================
    def _fetch_detail(self, vid, src):
        """精确详情：/api/detail?ids=&form="""
        if not vid or not src:
            return None
        data = self._api("/api/detail?ids=%s&form=%s" % (quote(str(vid)), quote(str(src))))
        lst = data.get("list") or []
        if not lst:
            return None
        item = dict(lst[0])
        item["_api_source"] = src  # 详情接口不回传源，这里补上，供线路分组使用
        return item

    @staticmethod
    def _split_multi(text):
        """MacCMS 多线路分隔符：网站播放页按 $$$ 拆，搜索接口里有的源用逗号"""
        if not text:
            return []
        if "$$$" in text:
            return [p for p in text.split("$$$") if p.strip()]
        return [p for p in text.split(",") if p.strip()]

    def _parse_episodes(self, from_str, url_str):
        """拆出全部线路：[(线路名, [(集名, url)])]，线路名与网站 source-tabs 一致"""
        names = self._split_multi(from_str)
        groups = self._split_multi(url_str)
        if not groups:
            return []
        result = []
        for i, seg in enumerate(groups):
            label = names[i] if i < len(names) else ("线路%d" % (i + 1))
            if label in self.SKIP_LINES:  # 网站播放页同样过滤掉这条线路
                continue
            eps = []
            for j, ep in enumerate([p for p in seg.split("#") if p.strip()]):
                if "$" in ep:
                    n, u = ep.split("$", 1)
                else:
                    n, u = "", ep
                n = self._clean(n) or ("第%02d集" % (j + 1))
                u = self._safe_url(u.strip())
                if u:
                    eps.append((n, u))
            if eps:
                result.append((label, eps))
        return result

    def _collect_sources(self, raw, name):
        """收集同一部片在网站全部数据源上的条目，用于把 12 条线路都写出来。

        重要前提（实测）：vod_id 不跨源通用 —— 同一个 id 在不同 form 下是不同片子。
        所以绝不能拿主条目的 id 去别的源试探；只能：
          1) 从搜索结果里取「片名完全一致」的其它源条目（搜索接口本身是多源聚合的）；
          2) 用每个源「自己的 id + 自己的 form」回查 /api/detail，拿到该源的完整线路
             （liangzi 只在 lz 的详情里出现，搜索接口只给 lzm3u8）。
        """
        found = {}  # 源 -> 条目（先不管有没有 play_url，搜索接口里很多源是空的）

        def put(src, r):
            src = str(src or "")
            if not r or src in found:
                return
            found[src] = r

        main_src = str(raw.get("_api_source") or raw.get("form") or "")
        put(main_src, raw)

        # 1) 搜索结果里同名的其它源条目（片名必须完全一致，避免挂错片）
        if name:
            self._search_raw(name)  # 确保索引已建立
            for r in self._raw_by_name.get(name) or []:
                if self._clean(r.get("vod_name")) == name:
                    put(str(r.get("_api_source") or r.get("form") or ""), r)

        # 2) 各源用自己的 id 回查详情：既补齐空 play_url，也补齐搜索接口给不全的线路
        #    （hn/js/xl/hh 搜索里 play_url 为 null；lz 搜索只给 lzm3u8，详情才有 liangzi）
        jobs = [(s, str(r.get("vod_id"))) for s, r in found.items() if s in self.ALL_SOURCES and r.get("vod_id")]

        def job(a):
            src, vid = a
            return src, self._fetch_detail(vid, src)

        for src, r in self._parallel(job, jobs):
            if not r or self._clean(r.get("vod_name")) != name:
                continue
            if not (r.get("vod_play_url") or ""):
                continue
            r = dict(r)
            r["_api_source"] = src
            found[src] = r  # 详情的线路最全，覆盖搜索条目

        out = [r for r in found.values() if r.get("vod_play_url")]
        if not out:
            return [raw]
        order = {s: i for i, s in enumerate(self.ALL_SOURCES)}
        out.sort(key=lambda r: order.get(str(r.get("_api_source") or ""), 99))
        return out

    def detailContent(self, ids):
        try:
            vid = str(ids[0] if isinstance(ids, list) else ids)
            name = ""

            if vid.startswith("db::"):
                # 豆瓣榜单 / 今日推荐条目：用片名去站内搜真实片源
                name = vid[4:]
                found = self._search_raw(name)
                if not found:
                    self._log("豆瓣条目无匹配片源: " + name)
                    return {"list": []}
                vid = found[0]["vod_id"]
                for item in found:
                    if (item.get("vod_name") or "") == name:
                        vid = item["vod_id"]
                        break

            raw = self._item_cache.get(vid)
            if raw is None and "@" in vid:
                v, s = vid.split("@", 1)
                raw = self._fetch_detail(v, s)
            if raw is None:
                self._log("详情未命中: " + vid)
                return {"list": []}

            name = self._clean(raw.get("vod_name"))
            if not (raw.get("vod_play_url") or ""):
                fixed = self._fetch_detail(raw.get("vod_id"), raw.get("_api_source"))
                if fixed and (fixed.get("vod_play_url") or ""):
                    raw = fixed

            from_list, url_list, seen_line = [], [], set()
            for r in self._collect_sources(raw, name):
                for label, eps in self._parse_episodes(r.get("vod_play_from"), r.get("vod_play_url")):
                    show = self._line_name(label)
                    if show in seen_line:  # 同名线路只保留一条，避免重复 tab
                        continue
                    seen_line.add(show)
                    from_list.append(show)
                    url_list.append("#".join(["%s$%s" % (n, u) for n, u in eps]))

            if not from_list:
                self._log("无可用播放线路: " + name)
                return {"list": []}

            if self.DIRECT_FIRST:
                from_list, url_list = self._direct_first(from_list, url_list)

            year = self._clean(raw.get("vod_year"))
            video = {
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": self._abs_pic(raw.get("vod_pic")),
                "vod_year": year,
                "vod_area": self._clean(raw.get("vod_area")),
                "vod_actor": self._clean(raw.get("vod_actor")),
                "vod_director": self._clean(raw.get("vod_director")),
                "vod_content": self._clean(raw.get("vod_content") or raw.get("vod_blurb")),
                "vod_remarks": self._clean(raw.get("vod_remarks")) or year,
                "vod_play_from": "$$$".join(from_list),
                "vod_play_url": "$$$".join(url_list),
            }
            self._log("详情成功: %s 线路(%d): %s" % (name, len(from_list), "/".join(from_list)))
            if self.PREFETCH:
                self._prefetch(from_list[0], url_list[0].split("#")[0].split("$")[-1])
            return {"list": [video]}
        except Exception as e:
            self._log("detailContent异常: %s" % e)
            return {"list": []}

    # ==================== 播放 ====================
    @staticmethod
    def _direct_first(from_list, url_list):
        """把直连 m3u8 的线路排到最前：默认线路不用二次解析，点开即播"""
        order = {n: i for i, n in enumerate(Spider.DIRECT_LINES)}
        pairs = sorted(zip(from_list, url_list), key=lambda p: order.get(p[0], 99))
        return [p[0] for p in pairs], [p[1] for p in pairs]

    def _prefetch(self, flag, url):
        """后台预解析首条线路首集，用户点播放时直接命中缓存"""
        if not url or self._re_media.search(url):
            return  # 本身就是直连，预解析没意义
        if url in self._play_cache:
            return

        def run():
            try:
                self._resolve_m3u8(url, flag)
            except Exception:
                pass

        threading.Thread(target=run, daemon=True).start()

    def _resolve_m3u8(self, url, flag=""):
        """无扩展名的网页地址 -> 真实 m3u8

        三种情况，按代价从低到高：
          1) hn/js/hh/xl 的 *yun：https://hn.bfvvs.com/play/xxx
             实测 12/12 直接拼 /index.m3u8 就是有效的 playlist，所以【零请求】直接拼，
             省掉一次 HTTP 往返（这是起播提速最大的一笔）。
          2) lz 的 liangzi：https://v.lzfile26.com/share/<hash>  -> 页面里 var main = "/xxx/index.m3u8?sign=..."
          3) 其它未知页面 -> 抓页面正则兜底
        """
        hit = self._play_cache.get(url)
        if hit:
            return hit
        if (flag or "").endswith("yun") or self._re_play_page.search(url):
            real = url.rstrip("/") + "/index.m3u8"
            self._play_cache[url] = real
            return real
        try:
            self._throttle()
            resp = self._session.get(url, headers=self.PLAY_HEADERS, timeout=self.PLAY_TIMEOUT)
            text = resp.text or ""
            real = ""
            m = self._re_m3u8.search(text)
            if m:
                real = m.group(1)
            else:
                mm = self._re_main.search(text)
                if mm:
                    main = mm.group(1).strip()
                    if main.startswith("http"):
                        real = main
                    else:
                        host = ""
                        mh = self._re_hosts.search(text)
                        if mh and mh.group(1).strip():
                            host = mh.group(1).strip().rstrip("/")
                        else:
                            parts = url.split("/")
                            host = "/".join(parts[:3]) if len(parts) >= 3 else ""
                        real = (host + "/" + main.lstrip("/")) if host else main
            if real:
                real = self._safe_url(real)
                self._play_cache[url] = real
                return real
        except Exception as e:
            self._log("解析播放页失败: %s" % e)
        return url.rstrip("/") + "/index.m3u8"

    def playerContent(self, flag, id, vipFlags=None):
        try:
            url = str(id or "").strip()
            if not url:
                return {"parse": 0, "url": "", "header": ""}
            if not url.startswith("http"):
                # 兼容少数壳子把整段 "集名$url" 传进来
                url = url.split("$")[-1]

            if self._re_media.search(url):
                return {"parse": 0, "url": url, "header": self.PLAY_HEADERS.copy()}

            real = self._resolve_m3u8(url, flag)
            if self._re_media.search(real):
                self._log("已解析直链: " + real[:80])
                return {"parse": 0, "url": real, "header": self.PLAY_HEADERS.copy()}

            # 实在解析不出来，交给壳子的解析器
            return {"parse": 1, "url": real, "header": self.PLAY_HEADERS.copy()}
        except Exception as e:
            self._log("playerContent异常: %s" % e)
            return {"parse": 0, "url": "", "header": ""}

    # ==================== 壳子可选接口 ====================
    def getName(self):
        return self.name

    def isVideoFormat(self, url):
        return bool(self._re_media.search(str(url or "")))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        self._api_cache.clear()
        self._item_cache.clear()
        self._raw_by_name.clear()
        self._list_cache.clear()
        self._play_cache.clear()

    def localProxy(self, param):
        return None
