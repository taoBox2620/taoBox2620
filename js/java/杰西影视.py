#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
YYJC影视 (https://yyjc.us) T4 Spider 数据源
============================================
按「py写源技能 v8.4」书写规范编写：继承 base.spider.Spider，
实现 homeContent / homeVideoContent / categoryContent / detailContent /
searchContent / playerContent 六接口，供 TVBox / 影视仓 / OK影视 / 羊壳等
以 T4/py 源方式加载。

站点数据链路（2026-09 实测确认）：
  GET  /api/library/list?category=latest|hot_movies|hot_tv|shorts
                          &page=&pageSize=&keyword=
       列表 / 分页 / 搜索；data 含 list/page/pagecount/limit/total/hasMore
  GET  /api/vod-sources
       视频源列表；data.sources 含 key/name/api/enabled
  POST /api/drama/detail  {"ids":id,"source":{...},"_t":毫秒时间戳}
       详情 + 剧集；data 含 id/name/pic/actor/director/blurb/area/year
       及 episodes:[{name,url}]，url 为 m3u8 直链

用法：
  TVBox/影视仓/OK影视 → 数据源 → 添加 py 源(T4) → 填本文件路径或 http(s) URL
  环境变量 YYJC_HOST 可覆盖站点根地址（默认 https://yyjc.us）。
"""

import json
import os
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from base.spider import Spider

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
TIMEOUT = 15
DEFAULT_PAGE_SIZE = 20

# TVBox type_id -> (分类名, yyjc category 参数)，采用 MacCMS 惯例小数字 id
CLASS_MAP = [
    ("1", "最新影视", "latest"),
    ("2", "电影", "hot_movies"),
    ("3", "电视剧", "hot_tv"),
    ("4", "短剧", "shorts"),
]
# 名称 / category 别名 / 旧版 1001-1004 兼容
CATEGORY_ALIAS = {
    "latest": "1", "movies": "2", "movie": "2",
    "tv": "3", "shorts": "4", "short": "4", "all": "1",
    "1001": "1", "1002": "2", "1003": "3", "1004": "4",
}


class Spider(Spider):
    def getName(self):
        return "YYJC影视"

    def init(self, extend=""):
        self.name = "YYJC影视"
        self.host = (os.environ.get("YYJC_HOST") or "https://yyjc.us").rstrip("/")
        self.headers = {
            "User-Agent": UA,
            "Referer": self.host + "/",
            "Accept": "application/json, text/plain, */*",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._sources = None
        self._sources_at = 0.0

    # ------------------------------------------------------------------ 网络层
    def _json(self, url, params=None, body=None):
        """GET(带 params) / POST(带 body) 请求 JSON；失败返回 {}。"""
        try:
            if body is not None:
                r = self.session.post(
                    url, data=json.dumps(body).encode("utf-8"),
                    headers={**self.headers, "Content-Type": "application/json"},
                    timeout=TIMEOUT, verify=False,
                    proxies=self.session.proxies or None)
            else:
                r = self.session.get(
                    url, params=params or {}, headers=self.headers,
                    timeout=TIMEOUT, verify=False,
                    proxies=self.session.proxies or None)
            return r.json() if r.status_code == 200 else {}
        except Exception:
            return {}

    def _fix(self, url):
        return urljoin(self.host + "/", url or "")

    def _clean(self, text):
        if not text:
            return ""
        s = re.sub(r"<[^>]+>", "", str(text))
        for ent, ch in (("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                        ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"),
                        ("&ndash;", "-"), ("&mdash;", "-")):
            s = s.replace(ent, ch)
        return re.sub(r"\s+", " ", s).strip()

    # ------------------------------------------------------------------ 解析辅助
    def _is_media(self, url):
        return (urlparse(url).scheme in ("http", "https")
                and bool(re.search(r"\.(?:m3u8|mp4)(?:$|[?#])",
                                   urlparse(url).path, re.I)))

    def _probe_media(self, url):
        """真直链门禁：仅当 m3u8 实测返回 #EXTM3U、mp4 有媒体内容时才视为直链。"""
        if not self._is_media(url):
            return ""
        try:
            r = self.session.get(
                url, headers={**self.headers, "Range": "bytes=0-4095"},
                timeout=TIMEOUT, verify=False, stream=True,
                proxies=self.session.proxies or None)
            data = next(r.iter_content(4096), b"")
            ctype = r.headers.get("Content-Type", "").lower()
            final = r.url
            if not r.ok:
                return ""
            if re.search(r"\.m3u8(?:$|[?#])", urlparse(final).path, re.I):
                return final if b"#EXTM3U" in data else ""
            return final if "video/" in ctype or data[4:12].find(b"ftyp") >= 0 else ""
        except Exception:
            return ""

    def _resolve_media(self, url, depth=0):
        """播放链接解析：直链探测优先，非直链按 JS/iframe 顺序递归。"""
        url = self._fix(url)
        if self._is_media(url):
            return self._probe_media(url)
        if depth > 3:
            return ""
        body = ""
        try:
            r = self.session.get(
                url, headers=self.headers, timeout=TIMEOUT, verify=False,
                proxies=self.session.proxies or None)
            r.encoding = r.apparent_encoding or "utf-8"
            body = r.text
        except Exception:
            return ""
        m = re.search(r'player_data\s*=\s*(\{.*?\})', body, re.S)
        if m:
            try:
                value = json.loads(m.group(1)).get("url", "")
                if value:
                    return self._resolve_media(urljoin(url, value), depth + 1)
            except Exception:
                pass
        m = re.search(r'(?:var\s+now|var\s+playurl)\s*=\s*["\']([^"\']+)', body)
        if m:
            return self._resolve_media(urljoin(url, m.group(1).replace("&amp;", "&")), depth + 1)
        frame = re.search(r'<iframe[^>]+src=["\']([^"\']+)', body, re.I)
        if frame:
            return self._resolve_media(urljoin(url, frame.group(1)), depth + 1)
        scopes = re.findall(
            r'<(?:script|video|source)[^>]*>.*?</(?:script|video|source)>'
            r'|<(?:video|source)[^>]*>', body, re.I | re.S)
        haystack = "\n".join(scopes) if scopes else body
        candidates = re.findall(r'https?://[^"\'<>\s]+\.(?:m3u8|mp4)[^"\'<>\s]*',
                                haystack, re.I)
        bad = re.compile(r'(?:^|[/_.-])(ad|ads|advert|preview|trailer|'
                         r'recommend|demo|sample)(?:[/_.-]|$)', re.I)
        candidates = list(dict.fromkeys(
            x.replace("&amp;", "&") for x in candidates
            if not bad.search(urlparse(x).path)))
        tokens = re.findall(r'[A-Za-z0-9]{4,}',
                            urlparse(url).path + "?" + urlparse(url).query)
        current_ids = [x for x in tokens
                       if any(c.isdigit() for c in x)
                       and x.lower() not in ("html", "m3u8", "index")]
        candidates.sort(key=lambda x: (not any(i in x for i in current_ids), len(x)))
        if not candidates:
            return ""
        return self._resolve_media(candidates[0], depth + 1)

    # ------------------------------------------------------------------ 分类映射
    def _classes(self):
        return [{"type_id": t, "type_name": n} for t, n, _ in CLASS_MAP]

    def _category(self, tid):
        """TVBox type_id / 别名 -> yyjc category 参数；空/0 表示全站最新。"""
        key = str(tid or "").strip()
        if not key or key in ("0",):
            return CLASS_MAP[0][2]
        if key in CATEGORY_ALIAS:
            key = CATEGORY_ALIAS[key]
        for tid_, name, cat in CLASS_MAP:
            if key in (tid_, name, cat):
                return cat
        return ""

    # ------------------------------------------------------------------ 数据层
    def _get_sources(self):
        """可用视频源列表（10 分钟缓存）。"""
        now = time.time()
        if self._sources is None or now - self._sources_at > 600:
            d = self._json(self.host + "/api/vod-sources")
            srcs = (d.get("data") or {}).get("sources") or []
            self._sources = [s for s in srcs if s.get("enabled")]
            self._sources_at = now
        return list(self._sources)

    def _library(self, category, page, page_size, keyword=""):
        """调用 /api/library/list；返回 data dict 或 {}."""
        params = {"category": category, "page": int(page),
                  "pageSize": int(page_size)}
        if keyword:
            params["keyword"] = keyword
        d = self._json(self.host + "/api/library/list", params=params)
        return d.get("data") or {}

    def _item(self, v):
        """列表项 -> TVBox vod 基础字段。"""
        vod = {
            "vod_id": str(v.get("id") or ""),
            "vod_name": v.get("name") or v.get("subName") or "",
            "vod_pic": self._fix(v.get("pic") or ""),
        }
        if v.get("remarks"):
            vod["vod_remarks"] = str(v["remarks"])
        if v.get("year"):
            vod["vod_year"] = str(v["year"])
        if v.get("area"):
            vod["vod_area"] = str(v["area"])
        if v.get("actor"):
            vod["vod_actor"] = str(v["actor"])
        if v.get("director"):
            vod["vod_director"] = str(v["director"])
        if v.get("vod_class"):
            vod["vod_class"] = str(v["vod_class"])
        return vod

    def _detail_data(self, vod_id):
        """多源 fallback 拉取详情；返回 data dict 或 {}。"""
        srcs = self._get_sources()
        if not srcs:
            return {}
        prefer = None
        for s in srcs:
            if str(s.get("key") or "") == str(vod_id).split(":", 1)[0]:
                prefer = s
                break
        ordered = [prefer] + [s for s in srcs if s is not prefer]
        for source in ordered:
            if not source:
                continue
            body = {
                "ids": str(vod_id),
                "source": source,
                "_t": int(time.time() * 1000),
            }
            d = self._json(self.host + "/api/drama/detail", body=body)
            data = d.get("data") or {}
            if data.get("id") and data.get("episodes"):
                return data
        # 名称为空源名时再兜底一次（不缓存，直接用首次请求的源）
        return {}

    def _detail_vod(self, data):
        """详情 data -> TVBox vod（含线路与剧集）。"""
        vod = self._item(data)
        vod["vod_content"] = self._clean(data.get("blurb") or "")
        eps = data.get("episodes") or []
        parts = []
        for i, ep in enumerate(eps, 1):
            name = str(ep.get("name") or "").strip() or ("第%02d集" % i)
            url = str(ep.get("url") or "").strip()
            if url:
                parts.append("%s$%s" % (name, url))
        vod["vod_play_from"] = "yyjc"
        vod["vod_play_url"] = "#".join(parts)
        return vod

    # ------------------------------------------------------------------ 六接口
    def homeContent(self, filter):
        d = self._library(CLASS_MAP[0][2], 1, DEFAULT_PAGE_SIZE)
        return {
            "class": self._classes(),
            "list": [self._item(v) for v in d.get("list") or []],
            "filters": {},
        }

    def homeVideoContent(self):
        d = self._library(CLASS_MAP[0][2], 1, DEFAULT_PAGE_SIZE)
        return {"list": [self._item(v) for v in d.get("list") or []]}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if str(pg).isdigit() else 1
        category = self._category(tid)
        if not category:
            return {"page": pg, "pagecount": 0, "limit": DEFAULT_PAGE_SIZE,
                    "total": 0, "list": []}
        d = self._library(category, pg, DEFAULT_PAGE_SIZE)
        pc = int(d.get("pagecount") or 0)
        total = int(d.get("total") or 0)
        limit = int(d.get("limit") or DEFAULT_PAGE_SIZE)
        return {
            "page": int(d.get("page") or pg),
            "pagecount": pc,
            "limit": limit,
            "total": total,
            "list": [self._item(v) for v in d.get("list") or []],
        }

    def detailContent(self, ids):
        out = []
        if isinstance(ids, list):
            vid = str(ids[0]) if ids else ""
        else:
            vid = str(ids or "")
        vid = vid.split(",")[0].strip()
        if vid:
            data = self._detail_data(vid)
            if data:
                out.append(self._detail_vod(data))
        return {"list": out}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if str(pg).isdigit() else 1
        d = self._library(CLASS_MAP[0][2], page, DEFAULT_PAGE_SIZE, keyword=str(key))
        return {"page": page,
                "list": [self._item(v) for v in d.get("list") or []]}

    def playerContent(self, flag, id, vipFlags):
        url = self._resolve_media(id or "")
        return {"parse": 0 if self._is_media(url) else 1,
                "url": url,
                "header": json.dumps(self.headers)}