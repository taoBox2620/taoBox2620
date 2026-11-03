# -*- coding: utf-8 -*-
"""多多影视（323433ssdfd.top）Python 爬虫（FongMi / CatVod / TVBox，type=3，Chaquopy）。

站点形态（2026-10-16 侦察）：Vue3 SPA + 自建 JSON API，接口前缀固定 `/api.php/web`。
  - 首页  GET  /index/home      → data.categories(4 类) / data.recommend / data.hotSearch
  - 分类  GET  /filter/vod      → type_name + type_id + page + sort + class/area/year
  - 搜索  GET  /search/index    → wd + page + limit
  - 详情  GET  /vod/get_detail  → data[0] 即 maccms 形态的 vod_play_from/vod_play_url；
                                  vodplayer（线路 from→show 映射）与 data **同级**，不在 data[0] 内
  - 解码  POST /decode/url      → application/x-protobuf + SHA256 时间戳签名，换直链

反爬三条（均实测，缺一即失败）：
  1. 接口前缀 `/api.php/web` 必须带。缺前缀时服务端返回 SPA 首页 HTML 且 HTTP 200
     （像是限流，实为路径未命中），故必须校验响应体是否 JSON。
  2. 请求头必须带 `web-sign: <静态值>` 与 `X-Client: <静态值>`；缺失或触发风控时服务端回
     456/457/458（站点 axios 拦截器把这三个码一律视为「维护/风控」状态）。
  3. `/decode/url` 签名 `sign = SHA256("finger=..&id=..&nonce=..&sk=..&time=..&v=1").upper()`，
     服务端同时校验签名与时间戳新鲜度（旧签名不可重放），故解码只能在 playerContent 现算。

契约要点：
  - 直接返回 dict/list，不要 json.dumps。
  - 分隔符：`$` 集名/播放值，`#` 集间隔，`$$$` 线路间隔（线路数 == vod_play_url 分段数）。
  - 集值用 base64url 封装 `<from>\\n<vod_id>\\n<集序>\\n<token>`：站点 token 内含 `|` 等字符，
    封装后彻底规避 `$ # $$$` 冲突；线路显示名取自 vodplayer.show，真实线路键随集值回传。
  - 站点 total/pageCount 是写死的 24/1（假数据），分页只能按「满页续翻」判定。
  - `self.fetch/post(timeout=)` 单位是**秒**；POST 原始字节走 `data=`。
  - 解码直链必须带浏览器 UA：shenhua7.vip 等线路被 Cloudflare 拦 Python 默认 UA（403）。
  - 站点部分线路被厂商 APP 白名单锁死（`PLATFORM_NOT_ALLOWED` 等，见 HARD_REJECT），本爬虫不伪造
    平台标识；这类线路解码失败即回退 `parse=1` + 站点播放页 URL，其余线路照常直链播放。
  - Python <= 3.8 兼容。
"""
import base64
import hashlib
import json
import os
import re
import time

import sys
sys.path.append('..')

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    # 离线兜底桩：与 FongMi 基类签名/语义逐字对齐（timeout=秒、encoding='utf-8'、POST 走 data=）
    import requests as _rq

    class BaseSpider(object):
        def fetch(self, url, params=None, cookies=None, headers=None, timeout=5,
                  verify=True, stream=False, allow_redirects=True):
            rsp = _rq.get(url, params=params, cookies=cookies, headers=headers,
                          timeout=timeout, verify=verify, stream=stream,
                          allow_redirects=allow_redirects)
            rsp.encoding = 'utf-8'
            return rsp

        def post(self, url, params=None, data=None, json=None, cookies=None, headers=None,
                 timeout=5, verify=True, stream=False, allow_redirects=True):
            rsp = _rq.post(url, params=params, data=data, json=json, cookies=cookies,
                           headers=headers, timeout=timeout, verify=verify, stream=stream,
                           allow_redirects=allow_redirects)
            rsp.encoding = 'utf-8'
            return rsp

        def log(self, *args):
            pass

        def cleanText(self, src):
            return src


# ------------------------------------------------------------------ 常量

# 站点轮换域名（同一套 API，实测四个域名返回完全一致）；默认用第一个
HOSTS = (
    "https://323433ssdfd.top",
    "https://duoduosdf12223234334.top",
    "https://xds2435u23422342342u.top",
    "https://dduotv01.top",
)
HOST = HOSTS[0]
API_PATH = "/api.php/web"

UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 6) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36")

# 站点客户端内置的静态协议常量（取自其前端 bundle）；均可经站点 ext 覆盖以便换版
WEB_SIGN = "ddtvf65f3a83d6d9ad6f"
CLIENT_TAG = "8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a"
FINGERPRINT = "WF-2c064bc5b3400788f31b848849bc3a60f835423ba2dfe69d7ea93974c216e4f2"
SIGN_SALT = "WEB-50a8e9c84a1dc05669a692ded99a2dac46527229e607a7be15db88dbc59059d1"
CLIENT_PKG = "com.web.player"

# 分类兜底快照（正常以 /index/home 的 categories 为准）
CATEGORIES = [("1", "电影"), ("2", "剧集"), ("3", "动漫"), ("4", "综艺")]
TID2NAME = dict(CATEGORIES)

PAGE_LIMIT = 24      # /filter/vod 默认每页条数（站点不传 limit）
SEARCH_LIMIT = 15    # /search/index 每页条数（站点客户端传 15）
FETCH_TIMEOUT = 10   # 秒（与站点 axios timeout 一致）
FETCH_ATTEMPTS = 4   # 按域名轮询的总尝试次数（覆盖全部备用域名）

# 站点 axios 拦截器把 456/457/458 一律视为「站点维护/风控」状态，需重试
BLOCK_STATUS = (456, 457, 458)

# 站点 LineRestrictionError 的判定集（index.js `St()`）：命中即线路硬拒，重试无意义
HARD_REJECT = ("PLATFORM_NOT_ALLOWED", "LOGIN_REQUIRED", "VIP_REQUIRED")


def _years(floor, tail):
    """站点 TypePage 的 T(r, s)：当前年份倒序排到 floor，再接尾部区间串。"""
    top = time.localtime().tm_year
    return [str(y) for y in range(top, floor - 1, -1)] + list(tail)


# 筛选选项取自站点 TypePage bundle（`ie` 常量），非服务端下发；已逐值实测有结果。
# year 写成 (floor, tail) 元组，展开时现算，避免跨年失效。
FILTER_SPEC = {
    "电影": {
        "class": ["动作", "喜剧", "爱情", "科幻", "恐怖", "悬疑", "犯罪", "战争",
                  "动画", "冒险", "历史", "灾难", "纪录", "剧情"],
        "area": ["大陆", "香港", "台湾", "美国", "日本", "韩国", "泰国", "印度",
                 "英国", "法国", "德国", "加拿大", "西班牙", "意大利", "澳大利亚"],
        "year": (2016, ["2015-2011", "2010-2000", "90年代", "80年代", "更早"]),
    },
    "剧集": {
        "class": ["爱情", "古装", "武侠", "历史", "家庭", "喜剧", "悬疑", "犯罪",
                  "战争", "奇幻", "科幻", "恐怖"],
        "area": ["大陆", "香港", "台湾", "美国", "日本", "韩国", "泰国", "英国"],
        "year": (2021, ["2020-2016", "2015-2011", "2010-2000", "更早"]),
    },
    "综艺": {
        "class": ["真人秀", "音乐", "脱口秀", "歌舞", "爱情"],
        "area": ["大陆", "香港", "台湾", "美国", "日本", "韩国"],
        "year": (2011, ["更早"]),
    },
    "动漫": {
        "class": ["冒险", "奇幻", "科幻", "武侠", "悬疑"],
        "area": ["大陆", "日本", "欧美"],
        "year": (2011, ["更早"]),
    },
}

# 站点 `sort` 取值（TypePage 的 `de` 常量）
SORT_OPTIONS = [("默认", ""), ("人气", "hits"), ("最新", "time"),
                ("评分", "score"), ("年份", "year")]


# ------------------------------------------------------------------ protobuf 极简编解码

def _pb_varint(value):
    """无符号 varint 编码。"""
    out = bytearray()
    n = int(value) & 0xFFFFFFFFFFFFFFFF
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _pb_read_varint(raw, pos):
    """读一个 varint；越界/超长返回 (None, pos)。"""
    value, shift, size = 0, 0, len(raw)
    while pos < size and shift < 64:
        b = raw[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not b & 0x80:
            return value, pos
        shift += 7
    return None, pos


def _pb_parse(raw):
    """只取 varint(0) 与 length-delimited(2) 字段的响应解码器。"""
    if isinstance(raw, str):
        raw = raw.encode("utf-8", "replace")
    out = {}
    pos, size = 0, len(raw or b"")
    while pos < size:
        key, pos = _pb_read_varint(raw, pos)
        if key is None:
            break
        num, wire = key >> 3, key & 7
        if wire == 0:
            value, pos = _pb_read_varint(raw, pos)
            if value is None:
                break
            out[num] = value
        elif wire == 2:
            length, pos = _pb_read_varint(raw, pos)
            if length is None or pos + length > size:
                break
            out[num] = raw[pos:pos + length].decode("utf-8", "replace")
            pos += length
        elif wire == 5:
            pos += 4
        elif wire == 1:
            pos += 8
        else:
            break
    return out


class Spider(BaseSpider):

    def __init__(self, *args, **kwargs):
        try:
            super(Spider, self).__init__()
        except TypeError:
            pass
        self.host = HOST
        self.web_sign = WEB_SIGN
        self.client_tag = CLIENT_TAG
        self.fingerprint = FINGERPRINT
        self.sign_salt = SIGN_SALT
        self.client_pkg = CLIENT_PKG
        self.ua = UA

    # ------------------------------------------------------------ 生命周期

    def init(self, extend=""):
        ext = self._parse_ext(extend)
        host = str(ext.get("host") or ext.get("url") or "").strip().rstrip("/")
        self.host = host if host.startswith("http") else HOST
        # 协议常量可经 ext 覆盖：站点换签名/换客户端标识时无需改码
        self.web_sign = str(ext.get("web_sign") or ext.get("webSign") or WEB_SIGN)
        self.client_tag = str(ext.get("client_tag") or ext.get("clientTag") or CLIENT_TAG)
        self.fingerprint = str(ext.get("fingerprint") or FINGERPRINT)
        self.sign_salt = str(ext.get("sign_salt") or ext.get("signSalt") or SIGN_SALT)
        self.client_pkg = str(ext.get("client_pkg") or ext.get("clientPkg") or CLIENT_PKG)
        self.ua = str(ext.get("ua") or ext.get("user_agent") or UA)

    def getName(self):
        return "多多影视"

    def destroy(self):
        self.host = HOST

    # ------------------------------------------------------------ 首页

    def homeContent(self, filter):
        payload = self._api("/index/home")
        classes = self._classes(payload)
        result = {
            "class": classes,
            "filters": self._build_filters(classes),
        }
        cards = self._home_cards(payload)
        if cards:
            result["list"] = cards
        return result

    def homeVideoContent(self):
        payload = self._api("/index/home")
        return {"list": self._home_cards(payload)}

    # ------------------------------------------------------------ 分类 / 搜索

    def categoryContent(self, tid, pg, filter, extend):
        page_no = self._to_page(pg)
        # 参数形态与站点 `cn()` 完全一致：type_name/type_id 同传，sort 缺省 hits，筛选项为空则不带
        params = {
            "type_name": self._type_name(tid),
            "type_id": str(tid if tid is not None else ""),
            "page": page_no,
            "sort": "hits",
        }
        for key in ("class", "area", "year", "sort"):
            value = (extend or {}).get(key)
            if value not in (None, ""):
                params[key] = value
        payload = self._api("/filter/vod", params)
        items = self._cards(payload.get("data"))
        return {
            "list": items,
            "page": page_no,
            "pagecount": self._pagecount(page_no, len(items), PAGE_LIMIT),
            "limit": PAGE_LIMIT,
        }

    def searchContent(self, key, quick, pg="1"):
        page_no = self._to_page(pg)
        payload = self._api("/search/index",
                            {"wd": str(key or "").strip(), "page": page_no,
                             "limit": SEARCH_LIMIT})
        items = self._cards(payload.get("data"))
        return {
            "list": items,
            "page": page_no,
            "pagecount": self._pagecount(page_no, len(items), SEARCH_LIMIT),
            "limit": SEARCH_LIMIT,
        }

    # ------------------------------------------------------------ 详情

    def detailContent(self, ids):
        vid = self._first_id(ids)
        if not vid:
            return {"list": []}
        payload = self._api("/vod/get_detail", {"vod_id": vid})
        rows = payload.get("data")
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            return {"list": []}
        raw = rows[0]
        vod = self._vod(raw, vid)
        lines = self._lines(payload, raw, vid)
        vod["vod_play_from"] = "$$$".join(line[0] for line in lines)
        vod["vod_play_url"] = "$$$".join(line[1] for line in lines)
        return {"list": [vod]}

    # ------------------------------------------------------------ 播放

    def playerContent(self, flag, id, vipFlags=None):
        frm, vid, ep_no, token = self._unpack(id)
        if not token:
            # 兼容裸 token（旧配置/手工调试）：flag 即线路键，无法回退播放页
            token, frm = str(id or "").strip(), str(flag or "").strip()
            vid, ep_no = "", 0
        url = self._decode(token, frm) if token else ""
        if url:
            return {"parse": 0, "jx": 0, "playUrl": "", "url": url,
                    "header": self._play_headers()}
        # 解码失败（如 zijianm3u8 / CO4K 被厂商 APP 白名单拦截）→ 委托 App 打开站点播放页
        return {"parse": 1, "jx": 0, "playUrl": "",
                "url": self._play_page(frm, vid, ep_no),
                "header": self._play_headers()}

    # ------------------------------------------------------------ 可选方法

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|m4v|flv|webm|ts)(\?|$)', str(url or ""), re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return [404, "text/plain", b""]

    # ------------------------------------------------------------ 内部：请求

    def _hosts(self):
        """当前域名优先，其余备用域名依次跟上（同一套 API，用于域名轮换容灾）。"""
        return [self.host] + [h for h in HOSTS if h != self.host]

    def _api_headers(self, host=None):
        return {
            "User-Agent": self.ua,
            "web-sign": self.web_sign,
            "X-Client": self.client_tag,
            "Accept": "application/json, text/plain, */*",
            "Referer": (host or self.host) + "/",
        }

    def _api(self, path, params=None):
        """GET 接口；按域名轮询尝试，命中后固定域名。失败返回 {}（由调用方降级空页）。"""
        for attempt in range(FETCH_ATTEMPTS):
            host = self._hosts()[attempt % len(HOSTS)]
            try:
                rsp = self.fetch(host + API_PATH + path, params=params,
                                 headers=self._api_headers(host), timeout=FETCH_TIMEOUT)
                status = getattr(rsp, "status_code", 0)
                text = str(getattr(rsp, "text", "") or "").strip()
                # 路径未命中/被拦时服务端会回 SPA HTML（HTTP 200），必须校验是否为 JSON
                data = json.loads(text) if text.startswith("{") else None
                if (isinstance(data, dict) and status not in BLOCK_STATUS
                        and data.get("code") not in BLOCK_STATUS):
                    self.host = host
                    return data
            except Exception:
                pass
            time.sleep(0.6 * (attempt + 1))
        return {}

    def _decode(self, token, frm):
        """POST /decode/url（protobuf + SHA256 时间戳签名）换直链；失败返回 ""。

        判定与站点 `ln()` 对齐：`code != 1` 且 msg 命中 HARD_REJECT → 线路硬拒，立即放弃；
        其余（空响应 / 无 code / 其他 msg / 异常）一律按可重试处理 —— 实测同一线路存在偶发失败，
        一次性放弃会把可播线路误降级为 parse=1。
        """
        body = self._decode_body(token, frm)
        if not body:
            return ""
        for attempt in range(FETCH_ATTEMPTS):
            host = self._hosts()[attempt % len(HOSTS)]
            headers = self._api_headers(host)
            headers["Content-Type"] = "application/x-protobuf"
            headers["Accept"] = "application/x-protobuf"
            try:
                rsp = self.post(host + API_PATH + "/decode/url", data=body,
                                headers=headers, timeout=FETCH_TIMEOUT)
                fields = _pb_parse(getattr(rsp, "content", b"") or b"")
                if fields.get(1) == 1 and fields.get(3):
                    self.host = host
                    return str(fields[3])
                if str(fields.get(2) or "") in HARD_REJECT:
                    return ""
            except Exception:
                pass
            time.sleep(0.6 * (attempt + 1))
        return ""

    def _decode_body(self, token, frm):
        """构造 /decode/url 的 protobuf 请求体：1=url 2=from 3=time 4=nonce 5=sign 6=pkg 7=platform。"""
        if not token:
            return b""
        now = int(time.time() * 1000)
        nonce = os.urandom(16).hex()
        source = "finger=%s&id=%s&nonce=%s&sk=%s&time=%d&v=1" % (
            self.fingerprint, self.client_pkg, nonce, self.sign_salt, now)
        sign = hashlib.sha256(source.encode("utf-8")).hexdigest().upper()
        chunks = []
        for num, value in ((1, token), (2, frm or ""), (3, now), (4, nonce),
                           (5, sign), (6, self.client_pkg), (7, 1)):
            if isinstance(value, int):
                chunks.append(_pb_varint((num << 3) | 0) + _pb_varint(value))
            else:
                raw = str(value).encode("utf-8")
                chunks.append(_pb_varint((num << 3) | 2) + _pb_varint(len(raw)) + raw)
        return b"".join(chunks)

    def _play_headers(self):
        """解码直链（shenhua7.vip 等）会被 Cloudflare 拦 Python 默认 UA，必须带浏览器 UA。"""
        return {"User-Agent": self.ua}

    def _play_page(self, frm, vid, ep_no):
        """站点播放页路由 `/play/:id`，线路与集序走 hash（parseHash 要求 nid > 0）。"""
        if not vid:
            return self.host + "/"
        page = "%s/play/%s" % (self.host, vid)
        if frm:
            page += "#sid=%s&nid=%d" % (frm, max(int(ep_no or 0), 1))
        return page

    # ------------------------------------------------------------ 内部：解析

    def _classes(self, payload):
        classes = []
        data = payload.get("data")
        categories = data.get("categories") if isinstance(data, dict) else None
        for item in categories or []:
            if not isinstance(item, dict):
                continue
            tid, name = item.get("type_id"), item.get("type_name")
            if tid is None or not name:
                continue
            classes.append({"type_id": str(tid), "type_name": str(name)})
        if classes:
            return classes
        return [{"type_id": tid, "type_name": name} for tid, name in CATEGORIES]

    def _home_cards(self, payload):
        """首页推荐位：recommend 在前，各分类预览在后，按 vod_id 去重。"""
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        groups = [data.get("recommend")]
        for cat in data.get("categories") or []:
            if isinstance(cat, dict):
                groups.append(cat.get("videos"))
        out, seen = [], set()
        for group in groups:
            if not isinstance(group, list):
                continue
            for card in self._cards(group):
                if card["vod_id"] in seen:
                    continue
                seen.add(card["vod_id"])
                out.append(card)
        return out

    def _lines(self, payload, raw, vid):
        """线路列表 [(显示名, 集段)]；from 与 url 按段序位置配对（站点客户端同法）。"""
        froms = [x.strip() for x in str(raw.get("vod_play_from") or "").split("$$$")]
        segs = [x.strip() for x in str(raw.get("vod_play_url") or "").split("$$$")]
        shows = {}
        for item in payload.get("vodplayer") or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("from") or "").strip()
            show = str(item.get("show") or "").strip()
            if key and show:
                shows[key] = show
        out, used = [], set()
        for index, frm in enumerate(froms):
            if not frm or index >= len(segs) or not segs[index]:
                continue
            name = self._safe(shows.get(frm) or frm) or frm
            if name in used:
                name = frm   # 显示名撞车时退回线路键，保证 vod_play_from 段内唯一
            used.add(name)
            eps = self._episodes(segs[index], frm, vid)
            if eps:
                out.append((name, "#".join(eps)))
        return out

    def _episodes(self, segment, frm, vid):
        """把站点的 `集名$token#...` 重打包为 `集名$base64url(from\\nvod_id\\n集序\\ntoken)`。"""
        out = []
        for index, ep in enumerate(segment.split("#"), 1):
            if not ep or "$" not in ep:
                continue
            title, token = ep.rsplit("$", 1)
            token = token.strip()
            if not token:
                continue
            title = self._safe(title) or ("第%d集" % index)
            out.append("%s$%s" % (title, self._pack(frm, vid, index, token)))
        return out

    @staticmethod
    def _pack(frm, vid, ep_no, token):
        raw = "%s\n%s\n%d\n%s" % (frm, vid, ep_no, token)
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")

    @staticmethod
    def _unpack(blob):
        """还原 (from, vod_id, 集序, token)；非本格式返回 ('', '', 0, '')。"""
        text = str(blob or "").strip()
        if not text:
            return "", "", 0, ""
        text += "=" * (-len(text) % 4)
        try:
            raw = base64.urlsafe_b64decode(text.encode("ascii")).decode("utf-8", "replace")
        except Exception:
            return "", "", 0, ""
        parts = raw.split("\n", 3)
        if len(parts) != 4:
            return "", "", 0, ""
        frm, vid, ep_no, token = parts
        try:
            ep_no = int(ep_no)
        except (TypeError, ValueError):
            ep_no = 0
        return frm, vid, ep_no, token

    def _vod(self, raw, vid):
        return {
            "vod_id": vid,
            "vod_name": self._clean(raw.get("vod_name")),
            "vod_pic": str(raw.get("vod_pic") or ""),
            "type_name": TID2NAME.get(str(raw.get("type_id") or ""), ""),
            "vod_year": self._clean(raw.get("vod_year")),
            "vod_area": self._clean(raw.get("vod_area")),
            "vod_lang": self._clean(raw.get("vod_lang")),
            "vod_remarks": self._clean(raw.get("vod_remarks")),
            "vod_actor": self._clean(raw.get("vod_actor")),
            "vod_director": self._clean(raw.get("vod_director")),
            "vod_content": self._clean(raw.get("vod_content")),
        }

    @classmethod
    def _cards(cls, items):
        out = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            vid, name = item.get("vod_id"), item.get("vod_name")
            if vid is None or not name:
                continue
            out.append({
                "vod_id": str(vid),
                "vod_name": str(name).strip(),
                "vod_pic": str(item.get("vod_pic") or ""),
                "vod_remarks": str(item.get("vod_remarks") or ""),
            })
        return out

    @classmethod
    def _build_filters(cls, classes):
        filters = {}
        for item in classes:
            spec = FILTER_SPEC.get(item.get("type_name"))
            if not spec:
                continue
            groups = []
            for key, label in (("class", "类型"), ("area", "地区"), ("year", "年份")):
                values = spec.get(key)
                if key == "year" and values:
                    values = _years(values[0], values[1])
                if not values:
                    continue
                groups.append({"key": key, "name": label,
                               "value": [{"n": "全部", "v": ""}] +
                                        [{"n": v, "v": v} for v in values]})
            groups.append({"key": "sort", "name": "排序",
                           "value": [{"n": n, "v": v} for n, v in SORT_OPTIONS]})
            filters[str(item.get("type_id"))] = groups
        return filters

    # ------------------------------------------------------------ 内部：小工具

    @staticmethod
    def _type_name(tid):
        """分类 id → 站点 type_name；非数字 id 原样透传（兼容直接传中文分类名）。"""
        key = str(tid or "").strip()
        return TID2NAME.get(key, key)

    @staticmethod
    def _first_id(ids):
        if isinstance(ids, (list, tuple)):
            ids = ids[0] if ids else ""
        elif isinstance(ids, dict):
            ids = ids.get("id") or ids.get("vod_id") or ""
        found = re.search(r'(\d+)', str(ids or ""))
        return found.group(1) if found else ""

    @staticmethod
    def _pagecount(page_no, got, limit):
        """确定值语义：满页（≥ 3/4 页大小，站点客户端同用留余量）续翻，否则回当前页停翻。

        站点 total/pageCount 写死为 24/1，不可用；宁可多请求一页，绝不提前截断。
        """
        return page_no + 1 if got >= max(1, int(limit * 3) // 4) else page_no

    @staticmethod
    def _to_page(pg):
        try:
            return max(int(str(pg)), 1)
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _parse_ext(extend):
        if isinstance(extend, dict):
            return dict(extend)
        if isinstance(extend, str) and extend.strip():
            try:
                data = json.loads(extend)
                if isinstance(data, dict):
                    return data
            except (ValueError, TypeError):
                pass
            try:
                from urllib.parse import parse_qs
                return {k: v[0] for k, v in parse_qs(extend).items()}
            except Exception:
                return {}
        return {}

    @staticmethod
    def _clean(value):
        text = re.sub(r'<[^>]+>', ' ', str(value or ""))
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def _safe(value):
        """集名分隔符卫生：`$ #` → 全角（`$$$` 随之失效）。"""
        return str(value or "").replace("$", "\uff04").replace("#", "\uff03").strip()


if __name__ == '__main__':
    sp = Spider()
    sp.init("")
    home = sp.homeContent(True)
    print("class=%s filters=%s home_items=%d"
          % ([c["type_name"] for c in home["class"]], sorted(home["filters"]),
             len(home.get("list") or [])))
    tid = home["class"][0]["type_id"]
    cat = sp.categoryContent(tid, "1", False, {})
    print("category tid=%s items=%d pagecount=%s"
          % (tid, len(cat["list"]), cat["pagecount"]))
    found = sp.searchContent("仙逆", False, "1")
    print("search 仙逆 items=%d pagecount=%s" % (len(found["list"]), found["pagecount"]))
    if cat["list"]:
        vod = sp.detailContent([cat["list"][0]["vod_id"]])["list"][0]
        print("detail %s from=%s" % (vod["vod_name"], vod["vod_play_from"]))
        froms = vod["vod_play_from"].split("$$$")
        segs = vod["vod_play_url"].split("$$$")
        for flag, seg in zip(froms, segs):
            eps = [e for e in seg.split("#") if e]
            if not eps:
                continue
            play = sp.playerContent(flag, eps[0].rsplit("$", 1)[-1], [])
            print("  play %-10s parse=%s url=%s"
                  % (flag, play["parse"], str(play["url"])[:90]))
