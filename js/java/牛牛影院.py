# -*- coding: utf-8 -*-
r"""
源名称：牛牛影院 (jrsestruturasmetalicas)
适配框架：dr_py (参考 D:\点播\py\FreeOK.py 完整接口 + D:\学习\Gimy.py)
目标站点：https://www.jrsestruturasmetalicas.com  (苹果CMS二次开发站, 伪静态前缀 jrsefi)
说明：
  - 列表/详情/搜索均为 HTML 页面解析
  - 播放地址为二次跳转：detail 返回 /jrsefiplay/{id}-{线路}-{集}.html，
    playerContent 再请求该页提取真实 m3u8 直链
  - 站点未开放标准 index.php/ajax 接口(均 500)，故全部走 HTML 解析
"""
import re
import json
import requests
from urllib.parse import quote, urljoin
from collections import defaultdict
from bs4 import BeautifulSoup
from base.spider import Spider


class Spider(Spider):
    HOST = "https://www.jrsestruturasmetalicas.com"

    DEFAULT_CLASSES = [
        ("电影", "1"),
        ("电视剧", "2"),
        ("综艺", "3"),
        ("动漫", "4"),
        ("短视频", "9"),
        ("即将上映", "51"),
    ]

    def __init__(self):
        self.host = self.HOST
        self.ext = ""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
        }
        # 复用 TCP 连接，减少每次起播的建连开销
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # master m3u8 解析缓存：m3u8 目录 -> 子流绝对地址（同影片多集复用，避免重复请求）
        self._m3u8_cache = {}
        self.classes = [
            {"type_name": name, "type_id": tid}
            for name, tid in self.DEFAULT_CLASSES
        ]
        self.filters = {
            tid: [
                {"key": "type", "name": "类型", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "喜剧片", "v": "35"},
                    {"n": "动作片", "v": "36"},
                    {"n": "爱情片", "v": "37"},
                    {"n": "科幻片", "v": "38"},
                    {"n": "恐怖片", "v": "39"},
                    {"n": "剧情片", "v": "40"},
                    {"n": "战争片", "v": "41"},
                ]},
                {"key": "by", "name": "排序", "value": [
                    {"n": "最新", "v": "time"},
                    {"n": "热播", "v": "hits"},
                    {"n": "评分", "v": "score"},
                ]},
                {"key": "year", "name": "年份", "value": [
                    {"n": str(y), "v": str(y)} for y in range(2026, 2015, -1)
                ]},
            ]
            for name, tid in self.DEFAULT_CLASSES
        }

    def getName(self):
        return "牛牛影院"

    def init(self, extend=""):
        self.setExtendInfo(extend if extend else self.ext)
        return None

    def setExtendInfo(self, extend):
        self.ext = extend or ""
        config = self._parse_config(extend)
        host = str(config.get("host") or "").strip().rstrip("/")
        if host.startswith(("http://", "https://")):
            self.host = host
        referer = str(config.get("referer") or "").strip()
        self.headers["Referer"] = (
            referer if referer.startswith(("http://", "https://")) else self.host + "/"
        )
        ua = str(config.get("userAgent") or config.get("ua") or "").strip()
        if ua:
            self.headers["User-Agent"] = ua
        # 同步到持久 session，确保连接复用也带最新头
        self.session.headers.update(self.headers)
        return None

    # ============ 工具函数 ============
    def _get(self, url):
        try:
            resp = self.session.get(url, timeout=10)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[牛牛影院] GET异常：{e}")
            return ""

    def _fix(self, url):
        return urljoin(self.host + "/", url or "")

    def _parse_config(self, value):
        if isinstance(value, dict):
            return dict(value)
        text = str(value or "").strip()
        if text.startswith("{"):
            try:
                return json.loads(text)
            except Exception:
                return {}
        if text.startswith(("http://", "https://")):
            return {"host": text}
        return {}

    # ============ 列表解析（首页/分类/搜索通用）============
    def _parse_card_list(self, html):
        items = []
        if not html:
            return items
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("article.t108-card")
        seen = set()
        for card in cards:
            a_poster = card.select_one("a.t108-card-poster") or card.select_one('a[href*="/jrsefi/"]')
            if not a_poster:
                continue
            href = a_poster.get("href", "")
            m = re.search(r"/jrsefi/(\d+)\.html", href)
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            vod_id = m.group(1)
            img = a_poster.select_one("span.t108-card-img") or a_poster.select_one("img")
            pic = ""
            if img:
                pic = img.get("data-original") or img.get("data-src") or img.get("src") or ""
            h3 = card.select_one("h3 a") or a_poster
            vod_name = (h3.get("title") or h3.get_text(strip=True) or a_poster.get("title") or "").strip()
            badge = card.select_one("span.t108-card-badge")
            remarks = badge.get_text(strip=True) if badge else ""
            if vod_id and vod_name:
                items.append({
                    "vod_id": vod_id,
                    "vod_name": vod_name,
                    "vod_pic": self._fix(pic),
                    "vod_remarks": remarks,
                })
        return items

    # ============ 首页分类（客户端读取此分类栏）============
    def homeContent(self, filter=False):
        return {"class": self.classes, "filters": self.filters}

    def getHomeContent(self, filter=False):
        return self.homeContent(filter)

    # ============ 首页推荐列表 ============
    def homeVideoContent(self):
        try:
            return {"list": self._parse_card_list(self._get(self.host + "/"))}
        except Exception:
            return {"list": []}

    # ============ 分类列表（支持二级筛选 extend）============
    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        ext = extend if isinstance(extend, dict) else {}
        stype = str(ext.get("type") or "").strip()   # 类型 ID（选了则覆盖 tid）
        sby = str(ext.get("by") or "").strip()        # 排序 time/hits/score
        syear = str(ext.get("year") or "").strip()    # 年份

        # 二级筛选 URL：/jrsefishow/{内容ID}---{排序}----{年份}------{页码}.html
        content_id = stype or str(tid)
        tail = "-----------" if page <= 1 else f"-----------{page}"
        if sby and syear:
            seg = f"---{sby}----{syear}------"
        elif sby:
            seg = f"---{sby}--------"
        elif syear:
            seg = f"----{syear}-------"
        else:
            seg = tail
        filter_url = f"{self.host}/jrsefishow/{content_id}{seg}.html"

        html = self._get(filter_url)
        videos = self._parse_card_list(html)

        # 回退：组合筛选返回空（站点风控 503 等），降级为基础分类分页页
        if not videos:
            if page <= 1:
                base_url = f"{self.host}/jrsefitype/{tid}.html"
            else:
                base_url = f"{self.host}/jrsefitype/{tid}-{page}.html"
            html = self._get(base_url)
            videos = self._parse_card_list(html)

        # 页数：从分页栏推断（兼容 jrsefishow 与 jrsefitype 两种分页链接）
        nums = set()
        for m in re.findall(r"/jrsefishow/[^'\"]*?-(\d+)\.html", html):
            nums.add(int(m))
        for m in re.findall(r"/jrsefitype/" + re.escape(str(tid)) + r"-(\d+)\.html", html):
            nums.add(int(m))
        pagecount = max(nums) if nums else (1 if videos else 0)
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": len(videos) or 24,
            "total": pagecount * max(len(videos), 1),
            "list": videos,
        }

    # ============ 详情页面 ============
    def detailContent(self, ids):
        result = []
        for vid in ids if isinstance(ids, (list, tuple)) else [ids]:
            if not vid:
                continue
            html = self._get(f"{self.host}/jrsefi/{vid}.html")
            if not html:
                continue
            soup = BeautifulSoup(html, "html.parser")

            h1 = soup.find("h1")
            vod_name = h1.get_text(strip=True) if h1 else ""
            poster = soup.select_one("img.lazyload") or soup.select_one(".t108-detail-poster img")
            pic = ""
            if poster:
                pic = poster.get("data-original") or poster.get("data-src") or poster.get("src") or ""

            meta = soup.select_one(".t108-meta")
            vod_year = vod_area = ""
            if meta:
                spans = [s.get_text(strip=True) for s in meta.select("span")]
                if spans:
                    vod_year = spans[0]
                    vod_area = spans[1] if len(spans) > 1 else ""
            kicker = soup.select_one(".t108-kicker")
            vod_type = kicker.get_text(strip=True) if kicker else ""

            desc = soup.select_one("p.t108-desc")
            vod_content = desc.get_text(strip=True) if desc else ""

            vod_director = vod_actor = ""
            for p in soup.select(".t108-detail-lines p"):
                txt = p.get_text(strip=True)
                if "导演" in txt:
                    vod_director = txt.replace("导演", "").strip()
                elif "主演" in txt:
                    vod_actor = txt.replace("主演", "").strip()

            play_links = re.findall(r"/jrsefiplay/(\d+)-(\d+)-(\d+)\.html", html)
            groups = defaultdict(list)
            for _vid, line, ep in play_links:
                groups[line].append((int(ep), ep))
            line_names = {}
            for li in soup.select("li.ewave-tab"):
                t = li.get_text(strip=True)
                m = re.search(r"线路(\d+)", t)
                if m:
                    line_names[m.group(1)] = f"线路{m.group(1)}"

            play_from, play_url = [], []
            for line in sorted(groups.keys(), key=lambda x: int(x)):
                eps = sorted(groups[line], key=lambda x: x[0])
                play_from.append(line_names.get(line, f"线路{line}"))
                eps_str = []
                for _, ep in eps:
                    ep_name = f"第{ep.zfill(2)}集"
                    ep_url = f"/jrsefiplay/{vid}-{line}-{ep}.html"
                    eps_str.append(f"{ep_name}${ep_url}")
                play_url.append("#".join(eps_str))

            result.append({
                "vod_id": str(vid),
                "vod_name": vod_name,
                "vod_pic": self._fix(pic),
                "vod_year": vod_year,
                "vod_area": vod_area,
                "vod_actor": vod_actor,
                "vod_director": vod_director,
                "vod_type": vod_type,
                "vod_remarks": "",
                "vod_content": vod_content,
                "vod_play_from": "$$$".join(play_from),
                "vod_play_url": "$$$".join(play_url),
            })
        return {"list": result}

    # ============ 搜索功能 ============
    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg or 1))
        wd = quote(key or "")
        if page <= 1:
            url = f"{self.host}/search/{wd}-------------.html"
        else:
            url = f"{self.host}/search/{wd}-------------{page}.html"
        videos = self._parse_card_list(self._get(url))
        return {
            "page": page,
            "pagecount": page,
            "list": videos,
        }

    # ============ 播放解析（二次跳转）============
    def playerContent(self, flag, id, vipFlags):
        value = str(id or "").strip()
        # 兼容 detail 传入的 "集名$地址" 形式
        if "$" in value and not value.startswith("http"):
            value = value.rsplit("$", 1)[-1].strip()
        if value.startswith("/"):
            play_url = self.host + value
        elif value.startswith("http"):
            play_url = value
        else:
            play_url = self.host + "/" + value.lstrip("/")
        html = self._get(play_url)
        if not html:
            return {"parse": 1, "playUrl": "", "url": play_url, "header": {}}

        m = re.search(r'"url"\s*:\s*"((?:https?:)?\\?/[^"]+\.(?:m3u8|mp4)[^"]*)"', html)
        if not m:
            return {"parse": 0, "playUrl": "", "url": play_url, "header": self.headers}
        real = m.group(1).replace("\\/", "/")
        if real.startswith("//"):
            real = "https:" + real

        # index.m3u8 多为 master playlist，子流是相对路径，需补全为绝对地址
        if real.endswith(".m3u8"):
            # 同一目录（同影片多集）只需解析一次 master，缓存复用，省去重复请求
            base_dir = real.rsplit("/", 1)[0]
            if base_dir in self._m3u8_cache:
                real = self._m3u8_cache[base_dir]
            else:
                try:
                    m3u8_text = self.session.get(real, timeout=10).text
                    if "#EXT-X-STREAM-INF" in m3u8_text:
                        child = None
                        for line in m3u8_text.splitlines():
                            line = line.strip()
                            if line and not line.startswith("#") and ".m3u8" in line:
                                child = line
                                break
                        if child:
                            real = child if child.startswith("http") else urljoin(real, child)
                    # 缓存"目录 -> 子流"映射（同影片后续集直接命中）
                    self._m3u8_cache[base_dir] = real
                except Exception:
                    pass

        result = {
            "parse": 0,
            "playUrl": "",
            "url": real,
            "header": self.headers,
        }
        if ".m3u8" in real.lower():
            result["type"] = "m3u8"
        return result
