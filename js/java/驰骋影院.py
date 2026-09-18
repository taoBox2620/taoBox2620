# -*- coding: utf-8 -*-
import re
import json
import time
import hashlib
from urllib.parse import urljoin, quote
from requests import Session
from lxml import etree
from base.spider import Spider as BaseSpider

try:
    from references.过盾方案.shield_helper import solve_slider
    _HAS_SLIDER = True
except Exception:
    _HAS_SLIDER = False

BASE_URL = "https://jtzn168.com"
CATEGORY_MAP = {
    "tv": "电视剧", "movie": "电影", "anime": "动漫", "variety": "综艺",
}
CHANNEL_SLUG = {
    "tv": "jtz-jttv", "movie": "jtz-jtfilm",
    "anime": "jtz-jtcg", "variety": "jtz-jtvariety",
}
CATEGORY_PAGE = {
    "tv": "/jtz-jttv.html", "movie": "/jtz-jtfilm.html",
    "anime": "/jtz-jtcg.html", "variety": "/jtz-jtvariety.html",
}
SITE_FEATURES = ["module-item", "webPlayers", "驰骋影院", "播放列表"]
CF_SHIELD = ["Just a moment", "cf-chl-widget", "cf-turnstile",
             "window._cf_chl_opt", "challenge-form", "cf-mitigated"]
SLIDER_SHIELD = ["滑动验证", "slideBox", "huadong_"]
OTHER_SHIELD = ["404 Not Found", "403 Forbidden", "正在验证", "请稍候"]

# 中文 -> 拼音 slug（用于影片库 URL）
TYPE_TV = [
    ("剧情", "juqing"), ("爱情", "aiqing"), ("喜剧", "xiju"), ("悬疑", "xuanyi"),
    ("犯罪", "fanzui"), ("古装", "guzhuang"), ("动作", "dongzuo"), ("奇幻", "qihuan"),
    ("惊悚", "jingsong"), ("家庭", "jiating"), ("科幻", "kehuan"), ("历史", "lishi"),
    ("战争", "zhanzheng"), ("冒险", "maoxian"), ("同性", "tongxing"), ("恐怖", "kongbu"),
    ("武侠", "wuxia"), ("传记", "zhuanji"), ("短片", "duanpian"), ("音乐", "yinyue"),
    ("儿童", "ertong"), ("动画", "donghua"), ("歌舞", "gewu"), ("故事", "gushi"),
    ("灾难", "zainan"), ("美食", "meishi"), ("青春", "qingchun"), ("搞笑", "gaoxiao"),
    ("情色", "qingse"), ("情感", "qinggan"), ("韩国", "hanguo"), ("明星", "mingxing"),
    ("后宫", "hougong"), ("运动", "yundong"),
]
TYPE_MOVIE = [
    ("剧情", "juqing"), ("喜剧", "xiju"), ("爱情", "aiqing"), ("动作", "dongzuo"),
    ("惊悚", "jingsong"), ("犯罪", "fanzui"), ("恐怖", "kongbu"), ("悬疑", "xuanyi"),
    ("奇幻", "qihuan"), ("冒险", "maoxian"), ("科幻", "kehuan"), ("战争", "zhanzheng"),
    ("家庭", "jiating"), ("历史", "lishi"), ("古装", "guzhuang"), ("传记", "zhuanji"),
    ("音乐", "yinyue"), ("武侠", "wuxia"), ("运动", "yundong"), ("同性", "tongxing"),
    ("情色", "qingse"), ("伦理", "lunli"), ("歌舞", "gewu"), ("儿童", "ertong"),
    ("灾难", "zainan"), ("戏曲", "xiqu"), ("搞笑", "gaoxiao"), ("文艺", "wenyi"),
    ("电影", "dianying"), ("韩国", "hanguo"), ("日本", "riben"), ("节目", "jiemu"),
    ("短片", "duanpian"), ("芬兰", "fenlan"), ("魔法", "mofa"), ("内地", "neidi"),
    ("演艺", "yanyi"), ("瑞士", "ruishi"),
]
TYPE_ANIME = [
    ("动画", "donghua"), ("喜剧", "xiju"), ("剧情", "juqing"), ("冒险", "maoxian"),
    ("奇幻", "qihuan"), ("动作", "dongzuo"), ("科幻", "kehuan"), ("爱情", "aiqing"),
    ("家庭", "jiating"), ("短片", "duanpian"), ("悬疑", "xuanyi"), ("儿童", "ertong"),
    ("惊悚", "jingsong"), ("犯罪", "fanzui"), ("运动", "yundong"), ("武侠", "wuxia"),
    ("古装", "guzhuang"), ("音乐", "yinyue"), ("恐怖", "kongbu"), ("战争", "zhanzheng"),
    ("歌舞", "gewu"), ("同性", "tongxing"), ("历史", "lishi"), ("电影", "dianying"),
    ("情色", "qingse"), ("搞笑", "gaoxiao"), ("故事", "gushi"), ("灾难", "zainan"),
    ("传记", "zhuanji"), ("魔法", "mofa"), ("后宫", "hougong"), ("内地", "neidi"),
    ("中国", "zhongguo"), ("文艺", "wenyi"), ("青春", "qingchun"), ("情感", "qinggan"),
    ("日本", "riben"), ("美食", "meishi"),
]
TYPE_VARIETY = [
    ("音乐", "yinyue"), ("歌舞", "gewu"), ("节目", "jiemu"), ("喜剧", "xiju"),
    ("剧情", "juqing"), ("爱情", "aiqing"), ("历史", "lishi"), ("综艺", "zongyi"),
    ("运动", "yundong"), ("犯罪", "fanzui"), ("悬疑", "xuanyi"), ("冒险", "maoxian"),
    ("晚会", "wanhui"), ("儿童", "ertong"), ("家庭", "jiating"), ("明星", "mingxing"),
    ("故事", "gushi"), ("旅行", "lvxing"), ("演艺", "yanyi"),
]
AREA_LIST = [
    ("中国大陆", "zhongguodalu"), ("美国", "meiguo"), ("中国", "zhongguo"),
    ("香港", "xianggang"), ("日本", "riben"), ("英国", "yingguo"),
    ("法国", "faguo"), ("德国", "deguo"), ("韩国", "hanguo"), ("内地", "neidi"),
    ("加拿大", "jianada"), ("中国台湾", "zhongguotaiwan"), ("意大利", "yidali"),
    ("大陆", "dalu"), ("印度", "yindu"), ("西班牙", "xibanya"),
    ("澳大利亚", "aodaliya"), ("泰国", "taiguo"), ("比利时", "bilishi"),
    ("俄罗斯", "eluosi"), ("瑞典", "ruidian"), ("墨西哥", "moxige"),
    ("丹麦", "danmai"), ("波兰", "bolan"), ("荷兰", "helan"),
    ("爱尔兰", "aierlan"), ("瑞士", "ruishi"), ("挪威", "nuowei"),
    ("巴西", "baxi"), ("阿根廷", "agenting"), ("苏联", "sulian"),
    ("西德", "xide"), ("奥地利", "aodili"), ("新加坡", "xinjiapo"),
    ("匈牙利", "xiongyali"), ("新西兰", "xinxilan"), ("芬兰", "fenlan"),
    ("南非", "nanfei"), ("捷克", "jieke"),
]
SORT_LIST = [("更新排序", ""), ("人气排序", "hits"), ("评分排序", "gold")]


def _cn_to_slug(cn, table):
    if not cn:
        return ""
    cn = str(cn).strip()
    if cn in ("全部", "全部类型", "全部地区", "全部年份", ""):
        return ""
    for n, v in table:
        if cn == n or cn == v:
            return v
    # 已经是拼音则直接透传
    if re.match(r"^[a-z0-9]+$", cn):
        return cn
    return ""


class Spider(BaseSpider):
    def getName(self):
        return "驰骋影院"

    def init(self, extend=""):
        self.session = Session()
        self.session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Linux; Android 16; Mobile) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Mobile Safari/537.36"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": BASE_URL + "/",
        })

    def _is_real_content(self, html):
        if not html or len(html) < 1500:
            return False
        head = html[:5000]
        for m in CF_SHIELD + SLIDER_SHIELD + OTHER_SHIELD:
            if m in head:
                return False
        return any(k in html for k in SITE_FEATURES)

    def _is_cf_challenge(self, html):
        if not html:
            return False
        return any(m in html[:5000] for m in CF_SHIELD)

    def _is_slider_challenge(self, html):
        if not html:
            return False
        return any(m in html[:5000] for m in SLIDER_SHIELD)

    def _solve_slider(self, target_url):
        if _HAS_SLIDER:
            try:
                ok, _ = solve_slider(self.session, BASE_URL,
                                     target_url=target_url)
                return ok
            except Exception:
                pass
        try:
            r = self.session.get(target_url, timeout=15)
            html = r.text
            if r.status_code != 403 and "滑动验证" not in html:
                return True
            m = re.search(r'src="(/huadong_[^"]+\.js)\?id=(\d+)"', html)
            if not m:
                return False
            js_path, ts = m.group(1), m.group(2)
            rjs = self.session.get(
                BASE_URL + js_path + "?id=" + ts,
                headers={"Referer": target_url}, timeout=15)
            js = rjs.text
            key = js_path.rsplit("_", 1)[-1].replace(".js", "")
            vm = re.search(r'value\s*=\s*"([^"]+)"', js)
            if not (key and vm):
                return False
            sign_src = "".join(str(ord(c) + 1) for c in vm.group(1))
            sign = hashlib.md5(sign_src.encode("utf-8")).hexdigest()
            pm = re.search(
                r'c\.get\("(/[a-z0-9_]+_yanzheng_huadong\.php)'
                r'\?type=([a-f0-9]+)&key="', js)
            if pm:
                vpath, vtype = pm.group(1), pm.group(2)
            else:
                vpath = "/a20be899_96a6_40b2_88ba_32f1f75f1552_yanzheng_huadong.php"
                vtype = "ad82060c2e67cc7e2cc47552a4fc1242"
            php_url = "%s%s?type=%s&key=%s&value=%s" % (
                BASE_URL, vpath, vtype, key, sign)
            self.session.get(php_url, headers={"Referer": target_url}, timeout=15)
            return True
        except Exception:
            return False

    def _fetch_raw(self, url, referer=None):
        headers = {
            "User-Agent": self.session.headers["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": referer or BASE_URL + "/",
        }
        try:
            r = self.fetch(url, headers=headers, timeout=(10, 20))
            text = r.text if hasattr(r, "text") else str(r)
            return text, 200
        except Exception:
            return "", 0

    def _get_with_fallback(self, url, referer=None):
        for attempt in range(3):
            html, status = self._fetch_raw(url, referer)
            if self._is_real_content(html):
                return html
            if self._is_cf_challenge(html):
                wait = 3.0 * (attempt + 1)
                time.sleep(wait)
                continue
            if self._is_slider_challenge(html):
                if self._solve_slider(url or BASE_URL + "/"):
                    time.sleep(1.5)
                    html2, _ = self._fetch_raw(url, referer)
                    if self._is_real_content(html2):
                        return html2
                break
            if status in (404, 403):
                break
            if attempt < 2:
                time.sleep(2)
        try:
            hd = {
                "User-Agent": self.session.headers["User-Agent"],
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Referer": referer or BASE_URL + "/",
            }
            r = self.session.get(url, headers=hd, timeout=(5, 15))
            if r.status_code == 200 and self._is_real_content(r.text):
                return r.text
        except Exception:
            pass
        return ""

    def _get(self, url, timeout=15):
        for i in range(3):
            try:
                r = self.session.get(url, timeout=(5, timeout),
                                     headers={"Referer": BASE_URL + "/"})
                if r.status_code == 404:
                    return ""
                r.raise_for_status()
                r.encoding = r.apparent_encoding or "utf-8"
                return r.text
            except Exception:
                time.sleep(1.5)
        return ""

    # 筛选：影片库 URL /{slug}/{type}_{area}_{year}_{sort}_{page}.html
    def _build_filter_url(self, tid, pg, extend):
        extend = extend or {}
        if tid in CHANNEL_SLUG:
            slug = CHANNEL_SLUG[tid]
            if tid == "tv":
                ttable = TYPE_TV
            elif tid == "movie":
                ttable = TYPE_MOVIE
            elif tid == "anime":
                ttable = TYPE_ANIME
            else:
                ttable = TYPE_VARIETY
            raw_t = extend.get("type", "") or extend.get("class", "") or extend.get("tag", "")
            raw_a = extend.get("area", "") or extend.get("place", "")
            raw_y = extend.get("year", "") or extend.get("time", "")
            raw_s = extend.get("sort", "") or extend.get("by", "") or extend.get("order", "")
            t = _cn_to_slug(raw_t, ttable)
            a = _cn_to_slug(raw_a, AREA_LIST)
            y = str(raw_y).strip() if raw_y else ""
            if y in ("全部",):
                y = ""
            if y and not re.match(r"^\d{4}$", y):
                # 兼容中文年份/全部
                ym = re.search(r"(19\d{2}|20\d{2})", y)
                y = ym.group(1) if ym else ""
            s = ""
            if raw_s:
                rs = str(raw_s).strip()
                if rs in ("hits", "gold", "人气排序", "评分排序", "人气", "评分"):
                    s = "hits" if rs in ("hits", "人气排序", "人气") else ("gold" if rs in ("gold", "评分排序", "评分") else "")
                    if rs == "更新排序":
                        s = ""
                elif rs == "":
                    s = ""
                else:
                    s = _cn_to_slug(rs, SORT_LIST)
            if pg and int(pg) > 1:
                page = str(int(pg))
            else:
                page = ""
            path = "_".join([t, a, y, s, page]) + ".html"
            return "%s/%s/%s" % (BASE_URL, slug, path)
        elif tid == "top":
            return BASE_URL + "/top/"
        elif tid == "update":
            return BASE_URL + "/update.html"
        else:
            return ""

    def homeContent(self, filter):
        classes = [{"type_id": c, "type_name": n}
                   for c, n in CATEGORY_MAP.items()]
        classes.append({"type_id": "top", "type_name": "排行榜"})
        classes.append({"type_id": "update", "type_name": "最近更新"})

        def _fv(table):
            return [{"n": "全部", "v": ""}] + [{"n": n, "v": v} for n, v in table]

        year_vals = [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(2026, 1998, -1)]
        filters = {
            "tv": [
                {"key": "type", "name": "类型", "value": _fv(TYPE_TV)},
                {"key": "area", "name": "地区", "value": _fv(AREA_LIST)},
                {"key": "year", "name": "年份", "value": year_vals},
                {"key": "sort", "name": "排序", "value": [{"n": n, "v": v} for n, v in SORT_LIST]},
            ],
            "movie": [
                {"key": "type", "name": "类型", "value": _fv(TYPE_MOVIE)},
                {"key": "area", "name": "地区", "value": _fv(AREA_LIST)},
                {"key": "year", "name": "年份", "value": year_vals},
                {"key": "sort", "name": "排序", "value": [{"n": n, "v": v} for n, v in SORT_LIST]},
            ],
            "anime": [
                {"key": "type", "name": "类型", "value": _fv(TYPE_ANIME)},
                {"key": "area", "name": "地区", "value": _fv(AREA_LIST)},
                {"key": "year", "name": "年份", "value": year_vals},
                {"key": "sort", "name": "排序", "value": [{"n": n, "v": v} for n, v in SORT_LIST]},
            ],
            "variety": [
                {"key": "type", "name": "类型", "value": _fv(TYPE_VARIETY)},
                {"key": "area", "name": "地区", "value": _fv(AREA_LIST)},
                {"key": "year", "name": "年份", "value": year_vals},
                {"key": "sort", "name": "排序", "value": [{"n": n, "v": v} for n, v in SORT_LIST]},
            ],
        }
        return {"class": classes, "filters": filters}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg)
        url = self._build_filter_url(tid, pg, extend or {})
        if not url:
            return {"page": pg, "pagecount": 0, "limit": 0, "total": 0, "list": []}
        html = self._get_with_fallback(url)
        if not html:
            return {"page": pg, "pagecount": 0, "limit": 0, "total": 0, "list": []}
        items = self._parse_items(html)
        try:
            tree = etree.HTML(html)
            has_next = bool(tree.xpath('//a[contains(text(), "下一页")]/@href')) if tree is not None else False
        except Exception:
            has_next = False
        # 影片库总数：影片库为你选出35525部影片
        total = len(items)
        try:
            m = re.search(r"影片库为你选出(\d+)部", html)
            if m:
                total = int(m.group(1))
        except Exception:
            pass
        if has_next:
            pagecount = pg + 1
        else:
            pagecount = pg
        # 第一页且有下一页时至少给 2，保证壳继续翻页
        if pg == 1 and has_next:
            pagecount = 2
        return {"page": pg, "pagecount": pagecount,
                "limit": len(items), "total": total, "list": items}

    def _parse_items(self, html):
        if not html:
            return []
        tree = etree.HTML(html)
        if tree is None:
            return []
        items = []
        seen = set()
        # token 匹配 module-item，避免漏掉 module-item xone，同时排除 module-item-cover 等
        cards = tree.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " module-item ")]')
        if not cards:
            cards = tree.xpath('//div[@class="module-item"]')
        for card in cards:
            try:
                a = card.xpath('.//a[contains(@href, "/nb/")]')
                if not a:
                    continue
                href = a[0].get("href", "").strip()
                m = re.search(r'/nb/(\d+)\.html', href)
                if not m:
                    continue
                vod_id = m.group(1)
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                title = (a[0].get("title", "") or "").strip() or (a[0].text_content() or "").strip()
                if not title:
                    try:
                        title = card.xpath('string(.//div[@class="module-item-title"])').strip()
                    except Exception:
                        title = ""
                if not title:
                    try:
                        title = card.xpath('string(.//a[@class="module-item-title"])').strip()
                    except Exception:
                        pass
                img = card.xpath('.//img')
                pic = ""
                if img:
                    pic = img[0].get("data-src") or img[0].get("data-original") or img[0].get("src") or ""
                    pic = (pic or "").strip()
                    # 过滤占位图
                    if "1732942998" in pic and img[0].get("data-src"):
                        pic = img[0].get("data-src").strip()
                    if not pic:
                        style = img[0].get("style", "")
                        bg = re.search(r'background-image\s*:\s*url\(["\']?([^"\')\s]+)', style)
                        if bg:
                            pic = bg.group(1)
                try:
                    txt = card.xpath("string(.//div[@class='module-item-text'])")
                except Exception:
                    txt = ""
                year = ""
                tag = ""
                ym = re.search(r'(\d{4})年', txt or "")
                year = ym.group(1) if ym else ""
                if not year:
                    try:
                        cap = card.xpath('string(.//div[@class="module-item-caption"])')
                        ym2 = re.search(r"(19\d{2}|20\d{2})", cap or "")
                        if ym2:
                            year = ym2.group(1)
                    except Exception:
                        pass
                parts = [p.strip() for p in (txt or "").split('/') if p.strip()]
                if len(parts) >= 2:
                    tag = parts[-1]
                if not tag:
                    try:
                        tag = card.xpath('string(.//div[contains(@class,"video-tag")])').strip()
                    except Exception:
                        tag = ""
                score = ""
                try:
                    score_el = card.xpath('.//span[@class="vod_score"]/text()')
                    score = score_el[0].strip() if score_el else ""
                except Exception:
                    pass
                if not title:
                    continue
                items.append({"vod_id": vod_id, "vod_name": title,
                              "vod_pic": pic, "vod_remarks": tag,
                              "vod_year": year, "vod_score": score})
            except Exception:
                continue
        return items

    def _fetch_json(self, url, referer=None):
        """取播放 JSON，不走 _is_real_content（JSON 里没有 module-item 等特征）"""
        headers = {
            "User-Agent": self.session.headers["User-Agent"],
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": referer or BASE_URL + "/",
            "X-Requested-With": "XMLHttpRequest",
        }
        # ① 壳端 self.fetch（大概率走 WebView，能过 CF）
        try:
            r = self.fetch(url, headers=headers, timeout=(10, 20))
            text = r.text if hasattr(r, "text") else str(r)
            if text and text.strip().startswith(("[", "{")):
                return text.strip()
            # 有些壳把 JSON 包了一层 html <pre>，也尝试提取
            if text and '"player"' in text and '"url"' in text:
                m = re.search(r'(\[.*?"player".*?\])', text, re.S)
                if m:
                    return m.group(1)
                return text.strip()
        except Exception:
            pass
        # ② requests 备用（CF 下大概率 403，仅尽力）
        try:
            r = self.session.get(url, headers=headers, timeout=(5, 15))
            if r.status_code == 200 and '"player"' in r.text:
                return r.text.strip()
        except Exception:
            pass
        return ""

    def detailContent(self, ids):
        out = []
        for vid in ids:
            vid = str(vid).strip()
            url = urljoin(BASE_URL, "/nb/" + vid + ".html")
            html = self._get_with_fallback(url)
            if not html:
                continue
            tree = etree.HTML(html)
            if tree is None:
                continue
            item = {"vod_id": vid}
            # ---- 标题 h1.page-title ----
            name = ""
            try:
                h1 = tree.xpath('string(//h1[contains(@class,"page-title")])').strip()
                if h1:
                    name = h1
                if not name:
                    name = tree.xpath('string(//h1)').strip()
                if not name:
                    t = tree.xpath('string(//title)').strip()
                    # 《兰香如故》电视剧全集在线观看_刘学义电视剧 - 驰骋影院 -> 兰香如故
                    m = re.search(r'《([^》]+)》', t)
                    name = m.group(1).strip() if m else t.split('_')[0].split('-')[0].strip()
            except Exception:
                pass
            item["vod_name"] = name
            # ---- 封面：限定在 video-cover / mobile-play / view-heading，避免取到推荐图 ----
            pic = ""
            try:
                for xp in [
                    '(//div[contains(@class,"video-cover")]//img | //div[contains(@class,"mobile-play")]//img | //div[contains(@class,"view-heading")]//img)[1]',
                ]:
                    imgs = tree.xpath(xp)
                    # lxml 对 [1] 位置谓词在联合里可能不稳，兜底取列表第一个
                    if imgs:
                        im = imgs[0] if isinstance(imgs, list) else imgs
                        pic = (im.get("data-src") or im.get("data-original") or im.get("src") or "").strip()
                        if pic and "1732942998" not in pic:
                            break
                        if pic:
                            break
                        pic = ""
                if not pic:
                    imgs = tree.xpath('//div[contains(@class,"video-cover") or contains(@class,"mobile-play")]//img')
                    if imgs:
                        pic = (imgs[0].get("data-src") or imgs[0].get("data-original") or imgs[0].get("src") or "").strip()
                if not pic or "1732942998" in pic:
                    # 按 alt=剧名 精确找
                    for im in tree.xpath('//div[contains(@class,"module-item-cover")]//img'):
                        ds = (im.get("data-src") or im.get("src") or "").strip()
                        alt = (im.get("alt") or "").strip()
                        if ds and ("1732942998" not in ds) and (not name or alt == name or "upload/movie" in ds):
                            pic = ds
                            break
                    if not pic or "1732942998" in pic:
                        allc = tree.xpath('//div[contains(@class,"module-item-cover")]//img')
                        if allc:
                            pic = (allc[0].get("data-src") or allc[0].get("src") or "").strip()
            except Exception:
                pass
            item["vod_pic"] = pic or ""
            # ---- 信息：video-info 体系 ----
            info_big = ""
            try:
                info_big = tree.xpath('string(//div[contains(@class,"video-info")])') or ""
            except Exception:
                info_big = ""
            if not info_big:
                try:
                    info_big = tree.xpath('string(//div[contains(@class,"vod-info")])') or ""
                except Exception:
                    pass
            def _txt_list(xp):
                try:
                    return [t.strip() for t in tree.xpath(xp) if t and t.strip()]
                except Exception:
                    return []
            # 导演 / 演员
            director = ""
            actor = ""
            try:
                d = _txt_list('//span[contains(text(),"导演")]/following-sibling::div//a/text()')
                if d:
                    director = "/".join(d)
                a = _txt_list('//span[contains(text(),"演员")]/following-sibling::div//a/text()')
                if a:
                    actor = "/".join(a)
            except Exception:
                pass
            # 年代 / 状态 / 集数 / 标签 等（p.vod-info-li 结构）
            def _li(label):
                try:
                    v = tree.xpath('string(//p[contains(.,"%s")]//span)' % label).strip()
                    if v:
                        return v
                    # 兼容无 span 的情况
                    t = tree.xpath('string(//p[contains(.,"%s")])' % label).strip()
                    if t and label in t:
                        return t.split(label, 1)[-1].replace("：", "").replace(":", "").strip()
                except Exception:
                    pass
                return ""
            year = _li("年代") or ""
            if not year:
                m = re.search(r'(19\d{2}|20\d{2})', info_big or "")
                # 优先 auxiliaries 里的年份链接
                try:
                    aux_y = tree.xpath('//div[contains(@class,"video-info-aux")]//a/text()')
                    for t in aux_y:
                        mm = re.search(r'(19\d{2}|20\d{2})', t or "")
                        if mm:
                            year = mm.group(1)
                            break
                except Exception:
                    pass
                if not year and m:
                    year = m.group(1)
            status = _li("状态") or ""
            total = ""
            try:
                js = _li("集数")
                m = re.search(r'共(\d+)集', js or "")
                if m:
                    total = m.group(1)
                else:
                    m2 = re.search(r'(\d+)集', (js or "") + (status or ""))
                    if m2 and not total:
                        pass
            except Exception:
                pass
            tag = _li("标签") or ""
            if not director:
                m = re.search(r'导演[：:]\s*([^\n\s<>]+(?:/[^\n\s<>]+)*)', info_big or "")
                if m:
                    director = m.group(1).strip()
            if not actor:
                m = re.search(r'演员[：:]\s*([^\n<>]+)', info_big or "")
                if m:
                    actor = re.sub(r'\s+', '', m.group(1).strip())
                    actor = actor.replace("年代", "").strip()
            # 地区 / 类型 从 aux 取
            area = ""
            vtype = ""
            try:
                aux_as = tree.xpath('//div[contains(@class,"video-info-aux")]//a/text() | //div[contains(@class,"video-info-aux")]//span/text()')
                aux_as = [t.strip() for t in aux_as if t and t.strip()]
                # 例: [电视剧, 逆袭, 2026, 中国大陆]
                for t in aux_as:
                    if t in ("电视剧", "电影", "动漫", "综艺"):
                        vtype = t
                    elif re.match(r'^(19\d{2}|20\d{2})$', t):
                        if not year:
                            year = t
                    elif len(t) <= 10 and ("大陆" in t or "美国" in t or "日本" in t or "韩国" in t or "香港" in t or "英国" in t or "中国" in t or "内地" in t or "台湾" in t):
                        area = t
                if not tag:
                    for t in aux_as:
                        if t not in (vtype, year, area) and t not in ("电视剧", "电影", "动漫", "综艺") and len(t) <= 10:
                            tag = t
                            break
            except Exception:
                pass
            item["vod_year"] = year or ""
            item["vod_actor"] = actor or ""
            item["vod_director"] = director or ""
            item["vod_tag"] = tag or ""
            item["vod_status"] = status or ""
            item["vod_total"] = total or ""
            item["vod_area"] = area or ""
            item["vod_type"] = vtype or ""
            # ---- 剧情：hide-article ----
            content = ""
            try:
                c = tree.xpath('string(//article[contains(@class,"hide-article")])').strip()
                if c:
                    content = c
                if not content:
                    c = tree.xpath('string(//div[contains(@class,"vod-info-content")])').strip()
                    if c:
                        content = re.sub(r'^剧情[：:]\s*', '', c).replace("展开", "").strip()
                if not content:
                    c = tree.xpath('string(//div[@id="hide-blurb"])').strip()
                    if c:
                        content = re.sub(r'^剧情[：:]\s*', '', c).replace("展开", "").strip()
            except Exception:
                pass
            item["vod_content"] = content or ""
            # ---- 播放列表：module-player-list / scroll-play（a>span 结构，必须用 . 而不是 text()）----
            from_name = "智能"
            eps = []  # (ep_name, pid)
            try:
                tabs = tree.xpath('//div[contains(@class,"module-tab-item")]//span/text() | //div[contains(@class,"module-tab-item")]/text()')
                tabs = [t.strip() for t in tabs if t and t.strip()]
                # 详情页一般是 [播放列表]，播放页是 [智能]；统一用 智能 做 from，保证播放器线路名稳定
                for t in tabs:
                    if "智能" in t:
                        from_name = "智能"
                        break
                else:
                    if tabs:
                        # 只有 播放列表 时也归一为 智能，避免壳切源混乱
                        from_name = "智能"
            except Exception:
                pass
            try:
                anchors = tree.xpath('//div[contains(@class,"module-player-list")]//a[@href] | //div[contains(@class,"scroll-play")]//a[@href]')
                if not anchors:
                    anchors = tree.xpath('//a[contains(@href,"/nb/") and contains(@href,"/")]')
                seen_pid = set()
                for a in anchors:
                    try:
                        h = (a.get("href") or "").strip()
                        if not h or "/nb/" not in h:
                            continue
                        m = re.search(r'/nb/(\d+)/([a-zA-Z0-9]+)\.html', h)
                        if not m:
                            continue
                        v, p = m.group(1), m.group(2)
                        if v != vid:
                            continue
                        if p in seen_pid:
                            continue
                        seen_pid.add(p)
                        title_attr = (a.get("title") or "").strip()
                        span_t = ""
                        try:
                            span_t = (a.xpath('string(.//span)') or "").strip() or (a.text_content() or "").strip()
                        except Exception:
                            span_t = (a.text or "").strip()
                        ep = span_t or title_attr
                        if not ep:
                            ep = p
                        # title 形如 兰香如故第01集 -> 提纯为 第01集
                        mep = re.search(r'(第\s*\d+\s*集|第\s*\d+话|第\s*\d+期|完整版|正片|预告|花絮|特辑)', ep)
                        if mep:
                            ep = mep.group(1).replace(" ", "")
                        else:
                            # 去掉剧名前缀
                            if name and ep.startswith(name):
                                ep = ep[len(name):].strip() or ep
                        eps.append((ep, p))
                    except Exception:
                        continue
            except Exception:
                pass
            item["vod_play_from"] = ""
            item["vod_play_url"] = ""
            if eps:
                # 按集数排序，避免播放页倒序导致列表倒挂（保留原序亦可，此处按集号正排更稳）
                def _ep_key(e):
                    mm = re.search(r'(\d+)', e[0] or "")
                    return int(mm.group(1)) if mm else 9999
                # 若原页是倒序（播放页），正排回正序；详情页本身正序，排序幂等
                try:
                    # 只有当首集号 > 末集号时才认为是倒序
                    first_n = _ep_key(eps[0])
                    last_n = _ep_key(eps[-1])
                    if first_n > last_n:
                        eps = sorted(eps, key=_ep_key)
                except Exception:
                    pass
                item["vod_play_from"] = from_name
                item["vod_play_url"] = "#".join(["%s$%s_%s" % (en, vid, pid) for en, pid in eps])
            remarks = []
            if item.get("vod_year"):
                remarks.append(item["vod_year"])
            if item.get("vod_status"):
                remarks.append(item["vod_status"])
            elif item.get("vod_total"):
                remarks.append("共%s集" % item["vod_total"])
            if item.get("vod_area"):
                remarks.append(item["vod_area"])
            item["vod_remarks"] = " ".join(remarks).strip()
            out.append(item)
        return {"list": out}

    def playerContent(self, flag, id, vipFlags):
        raw_id = (str(id) if id is not None else "").strip()
        vod_id = ""
        pid = ""
        try:
            # 详情页给的是 第01集$145229_6aa41b9a5bec8，id 段为 145229_6aa41b9a5bec8
            # 兼容旧数据 vid$pid、vid/pid、纯 pid
            m = re.search(r'(\d+)[_$/-]([a-zA-Z0-9]+)', raw_id)
            if m:
                vod_id, pid = m.group(1), m.group(2)
            elif "$" in raw_id:
                a, b = raw_id.split("$", 1)
                a, b = a.strip(), b.strip()
                if a.isdigit():
                    vod_id, pid = a, b
                elif b.isdigit():
                    vod_id, pid = b, a
                else:
                    pid = b or a
            elif "/" in raw_id:
                parts = [p for p in raw_id.split("/") if p]
                if len(parts) >= 2 and parts[0].isdigit():
                    vod_id, pid = parts[0], parts[1]
                elif len(parts) == 1 and parts[0].isdigit():
                    vod_id = parts[0]
                else:
                    pid = parts[-1]
            elif raw_id.isdigit():
                vod_id = raw_id
            else:
                # 纯 pid，尝试从 flag 反查？无 vid 则无法拼 data 接口，直接走嗅探
                pid = raw_id
        except Exception:
            pass
        # data 接口实测无 .html 后缀：/webPlayers/145229/6aa41b9a5bec8 -> [{"player":"极速云","url":"...m3u8"}]
        if vod_id and pid:
            data_url = "%s/webPlayers/%s/%s" % (BASE_URL, vod_id, pid)
            ep_page = "%s/nb/%s/%s.html" % (BASE_URL, vod_id, pid)
        elif vod_id:
            data_url = "%s/webPlayers/%s/" % (BASE_URL, vod_id)
            ep_page = "%s/nb/%s.html" % (BASE_URL, vod_id)
        elif pid:
            # 缺 vid 时无法调 data 接口，直接让 WebView 打开搜索/嗅探
            return {"parse": 1, "url": BASE_URL + "/nb/" + pid + ".html", "header": {}}
        else:
            return {"parse": 1, "url": BASE_URL + "/", "header": {}}
        raw = self._fetch_json(data_url, referer=ep_page)
        if raw:
            try:
                # 有些壳包了 <pre>，先提纯 JSON 数组
                txt = raw.strip()
                if not txt.startswith("["):
                    mm = re.search(r'\[.*?\"player\".*?\]', txt, re.S)
                    if mm:
                        txt = mm.group(0)
                arr = json.loads(txt)
                if isinstance(arr, dict):
                    arr = [arr]
                names = []
                urls = []
                seen_u = set()
                for i, o in enumerate(arr or []):
                    if not isinstance(o, dict):
                        continue
                    nm = str(o.get("player") or ("线路%d" % (i + 1))).strip()
                    u = str(o.get("url") or "").strip()
                    if not u or not u.startswith("http"):
                        continue
                    if u in seen_u:
                        continue
                    seen_u.add(u)
                    names.append(nm or ("线路%d" % (i + 1)))
                    urls.append(u)
                if urls:
                    # 同一集多条云线路，默认取第一条直连，保证壳拿到 url 字段就能播
                    # 线路名保留在 header 备注无用，直接返回首条 m3u8
                    return {"parse": 0, "url": urls[0], "header": {}}
            except Exception:
                pass
        # JSON 被 CF 拦或为空时，退回剧集页让壳 WebView 嗅探 iframe（页内 /webPlayers/strPlayer.html?v=05 + ArtPlayer 可播）
        return {"parse": 1, "url": ep_page, "header": {}}

    def searchContent(self, key, quick, pg="1"):
        kw = quote(key)
        pg = int(pg)
        url = urljoin(BASE_URL, "/so/?wd=" + kw)
        if pg > 1:
            url = urljoin(BASE_URL, "/so/" + kw + "/" + str(pg) + ".html")
        html = self._get_with_fallback(url)
        if not html:
            return {"page": pg, "pagecount": 0, "limit": 0, "total": 0, "list": []}
        items = self._parse_items(html)
        tree = etree.HTML(html)
        tt = tree.xpath("string(//h1 | //title)") if tree is not None else ""
        tm = re.search(r'(\d+)\s*部', tt or "")
        total = int(tm.group(1)) if tm else len(items)
        na = tree.xpath('//a[contains(text(), "下一页")]/@href') if tree is not None else []
        pc = 2 if na and pg == 1 else 1
        if pg > 1 and not items:
            pc = max(pg - 1, 1)
        if pg > 1 and na:
            pc = pg + 1
        return {"page": pg, "pagecount": pc,
                "limit": len(items), "total": total, "list": items}