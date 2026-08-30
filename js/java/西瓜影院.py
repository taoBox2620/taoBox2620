# coding=utf-8
"""
目标站: 黑夜影院 (darkvod.com)
框架: 苹果CMS (maccms) + MYUI 模板
实际结构(2026-08):
  详情页: /dianying/{id}/
  播放页: /dyplay/{id}-{sid}-{nid}/
  线路:   .tab-content .tab-pane (id=playlistN) + 对应 <a href="#playlistN">线路名</a>
  剧集:   .myui-content__list > li > a[href^="/dyplay/"]
  视频:   播放页 HTML 内可直接匹配到 m3u8/mp4/flv URL
"""

import re
import sys
import json
import ssl
import urllib.parse
from collections import OrderedDict
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass


# 过滤纯数字/角标等噪声线路名
_BAD_SOURCE_NAME = re.compile(r'^[\s\d\/\\\.\-—_、,，]+$|^\s*$')

# 播放页 URL 规则: 支持 dyplay/vodplay/play/player, 末尾可带 / 或 .html
_PLAY_HREF_RE = re.compile(
    r'/(dyplay|vodplay|play|player)/(\d+)[\-_](\d+)[\-_](\d+)(?:\.html?)?/?',
    re.I
)


class Spider(Spider):
    def init(self, extend=""):
        self.site_url = "https://darkvod.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': self.site_url + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        try:
            import requests
            import urllib3
            urllib3.disable_warnings()
            from requests.adapters import HTTPAdapter
            self._session = requests.Session()
            self._session.headers.update(self.headers)
            self._session.verify = False
            adapter = HTTPAdapter(pool_connections=8, pool_maxsize=16, max_retries=2)
            self._session.mount('http://', adapter)
            self._session.mount('https://', adapter)
        except Exception:
            self._session = None

        self.categories = self._build_categories()
        self.filters = self._build_filters()

    def _fetch(self, url, headers=None, timeout=12):
        if self._session is not None:
            try:
                h = dict(self.headers)
                if headers:
                    h.update(headers)
                return self._session.get(url, headers=h, timeout=timeout)
            except Exception:
                pass
        try:
            import requests
            import urllib3
            urllib3.disable_warnings()
            return requests.get(url, headers=headers or self.headers, timeout=timeout, verify=False)
        except Exception:
            return self.fetch(url, headers=headers)

    def _fix_url(self, url):
        if not url:
            return ""
        u = url.strip()
        if u.startswith('//'):
            return 'https:' + u
        if u.startswith(('http://', 'https://')):
            return u
        if u.startswith(('data:', 'blob:', 'javascript:')):
            return ''
        return urllib.parse.urljoin(self.site_url + '/', u.lstrip('/'))

    def _extract_pic(self, node):
        if node is None:
            return ''
        for attr in ('data-original', 'data-echo', 'data-src', 'data-url', 'data-bg', 'src'):
            v = (node.get(attr) or '').strip()
            if v and not v.startswith(('data:', 'blob:')):
                return v
        ss = (node.get('srcset') or '').strip()
        if ss:
            first = ss.split(',')[0].strip().split(' ')[0]
            if first:
                return first
        style = node.get('style', '')
        bg = re.search(r'url\(([^)]+)\)', style)
        if bg:
            return bg.group(1).strip('"').strip("'")
        for child in node.find_all(['source', 'img']):
            for attr in ('data-original', 'data-srcset', 'data-echo', 'data-src', 'data-url', 'srcset', 'src'):
                v = (child.get(attr) or '').strip()
                if v and not v.startswith(('data:', 'blob:')):
                    return v
        return ''

    def _build_categories(self):
        return [
            {"type_id": "dianying", "type_name": "电影"},
            {"type_id": "lianxuju", "type_name": "连续剧"},
            {"type_id": "zongyi", "type_name": "综艺"},
            {"type_id": "dongman", "type_name": "动漫"},
            {"type_id": "shuangwenduanju", "type_name": "爽文短剧"},
        ]

    def _build_filters(self):
        return {
            "dianying": [{
                "key": "class", "name": "类型",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "动作片", "v": "dongzuopian"},
                    {"n": "喜剧片", "v": "xijupian"},
                    {"n": "爱情片", "v": "aiqingpian"},
                    {"n": "科幻片", "v": "kehuanpian"},
                    {"n": "恐怖片", "v": "kongbupian"},
                    {"n": "剧情片", "v": "juqingpian"},
                    {"n": "战争片", "v": "zhanzhengpian"},
                    {"n": "悬疑片", "v": "xuanyipian"},
                    {"n": "犯罪片", "v": "fanzuipian"},
                    {"n": "网络电影", "v": "wangluodianying"},
                    {"n": "古装片", "v": "guzhuangpian"},
                    {"n": "记录片", "v": "jilupian"},
                    {"n": "历史片", "v": "lishipian"},
                    {"n": "影视解说", "v": "yingshijieshuo"},
                ]
            }],
            "lianxuju": [{
                "key": "class", "name": "地区",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "欧美剧", "v": "oumeiju"},
                    {"n": "港台剧", "v": "gangtaiju"},
                    {"n": "日韩剧", "v": "rihanju"},
                    {"n": "国产剧", "v": "guochanju"},
                ]
            }],
            "zongyi": [],
            "dongman": [],
            "shuangwenduanju": [],
        }

    def _get_cate_url(self, tid, pg=1, extend=None):
        extend = extend or {}
        sub = extend.get("class", "")
        path = sub if sub else tid
        if pg <= 1:
            return f"{self.site_url}/mov/{path}/"
        return f"{self.site_url}/mov/{path}/index_{pg}.html"

    def _parse_video_list(self, html):
        if not html:
            return []
        results, seen = [], set()
        soup = BeautifulSoup(html, 'html.parser')
        a_sel = soup.find_all('a', href=re.compile(r'/(?:dianying|detail)/\d+/?'))
        for a in a_sel:
            href = a.get('href', '')
            m = re.search(r'/(?:dianying|detail)/(\d+)/?', href)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue

            pic = self._extract_pic(a)
            if not pic:
                any_child = a.find(['img', 'source'])
                if any_child:
                    pic = self._extract_pic(any_child)
            if not pic:
                continue

            title = (a.get('title') or '').strip()
            if not title:
                img = a.find('img')
                if img:
                    title = (img.get('alt') or '').strip()
            if not title:
                title = a.get_text(strip=True)
            if not title:
                continue

            remark = ''
            for cls in ('pic-text', 'text-right', 'remark', 'pic-tag'):
                node = a.find(class_=re.compile(cls))
                if node:
                    remark = node.get_text(strip=True)
                    break

            seen.add(vid)
            results.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": self._fix_url(pic),
                "vod_remarks": remark,
            })
        return results

    def homeContent(self, filter):
        resp = self._fetch(self.site_url + "/", headers=self.headers)
        video_list = []
        if resp:
            video_list = self._parse_video_list(resp.text)[:30]
        return {"class": self.categories, "list": video_list, "filters": self.filters}

    def homeVideoContent(self):
        return self.homeContent(False)

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        url = self._get_cate_url(tid, page, extend)
        resp = self._fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": 24, "total": 0}

        video_list = self._parse_video_list(resp.text)
        html = resp.text

        nums = re.findall(r'/mov/[^/]+/index_(\d+)\.html', html)
        if not nums:
            nums = re.findall(r'href=["\']?/mov/[^/]+/(\d+)\.html["\']?', html)
        pagecount = max((int(x) for x in nums), default=page)
        if pagecount < page:
            pagecount = page

        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": 24,
            "total": len(video_list) * pagecount,
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/dianying/{vod_id}/"
        resp = self._fetch(url, headers=self.headers)
        if not resp:
            return {"list": []}
        html = resp.text

        # 标题
        vod_name = vod_id
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.I | re.DOTALL)
        if m:
            vod_name = re.sub(r'<[^>]+>', '', m.group(1)).strip() or vod_id
        if not vod_name or vod_name == vod_id:
            m = re.search(r'<title>(.*?)</title>', html, re.I)
            if m:
                vod_name = m.group(1).split('-')[0].strip() or vod_id

        # 封面
        vod_pic = ""
        m = re.search(r'<div[^>]*?myui-content__thumb[^>]*>.*?<img[^>]*?src=["\']?([^"\']+)["\']?', html, re.I | re.DOTALL)
        if not m:
            m = re.search(r'<img[^>]*?data-original=["\']?([^"\']+)["\']?', html, re.I)
        if not m:
            m = re.search(r'<img[^>]*?src=["\']?([^"\']+)["\']?', html, re.I)
        if m:
            vod_pic = self._fix_url(m.group(1))

        # 简介
        vod_content = ""
        m = re.search(r'<meta[^>]*?name=["\']?description["\']?[^>]*?content=["\']?([^"\']+)', html, re.I)
        if m:
            vod_content = m.group(1).strip()
        if not vod_content:
            m = re.search(r'class=["\']?desc["\']?[^>]*>(.*?)</div>', html, re.I | re.DOTALL)
            if m:
                vod_content = re.sub(r'<[^>]+>', '', m.group(1)).strip()

        # 字段
        def _field(label):
            patterns = [
                label + r'[：:]\s*([^<\n\r]+?)(?=\s*(?:<br|<p|</p|导演|地区|年份|类型|更新|简介|$))',
                r'>' + label + r'<[^>]*>\s*[:：]?\s*([^<\n\r]+?)(?=\s*<|$)',
                label + r'</[^>]+>\s*([^<\n\r]+?)(?=\s*<|$)',
            ]
            for pat in patterns:
                mm = re.search(pat, html, re.I)
                if mm:
                    val = re.sub(r'<[^>]+>', '', mm.group(1)).strip()
                    if val and val not in ('内详', '未知'):
                        return val
            return ''

        vod_actor = _field('主演') or _field('演员')
        vod_director = _field('导演')
        vod_year = _field('年份') or _field('年代')
        vod_area = _field('地区') or _field('国家/地区')

        # === 播放列表解析(针对黑夜影院真实结构) ===
        lines = OrderedDict()
        soup = BeautifulSoup(html, 'html.parser')

        # 先收集所有线路名: <a href="#playlistN">线路名</a>
        tab_name_map = {}
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if href.startswith('#playlist'):
                pid = href[1:]  # playlistN
                name = a.get_text(strip=True)
                if name and not _BAD_SOURCE_NAME.match(name):
                    tab_name_map[pid] = name

        # 遍历 .tab-content .tab-pane
        for pane in soup.select('.tab-content .tab-pane'):
            pid = pane.get('id', '')
            source_name = tab_name_map.get(pid)
            if not source_name:
                # 从 .playlist-tip-container .tips 取线路提示
                tip = pane.select_one('.playlist-tip-container .tips')
                if tip:
                    source_name = tip.get_text(strip=True)
                # 兜底生成线路名
                if not source_name or _BAD_SOURCE_NAME.match(source_name):
                    source_name = f"线路{len(lines) + 1}"

            eps = []
            # 黑夜影院真实剧集结构: .myui-content__list > li > a[href^="/dyplay/"]
            for a in pane.select('.myui-content__list li a'):
                href = a.get('href', '')
                mm = _PLAY_HREF_RE.search(href)
                if not mm:
                    continue
                _, vid, sid, nid = mm.groups()
                full = f"{self.site_url}/dyplay/{vid}-{sid}-{nid}/"
                ep_name = a.get_text(strip=True) or f"第{nid}集"
                if not any(full == u for _, u in eps):
                    eps.append((ep_name, full))

            # 面板内其他可能的 a[href*="/dyplay/"]
            if not eps:
                for a in pane.find_all('a', href=re.compile(r'/dyplay/\d+')):
                    href = a['href']
                    mm = _PLAY_HREF_RE.search(href)
                    if not mm:
                        continue
                    _, vid, sid, nid = mm.groups()
                    full = f"{self.site_url}/dyplay/{vid}-{sid}-{nid}/"
                    ep_name = a.get_text(strip=True) or f"第{nid}集"
                    if not any(full == u for _, u in eps):
                        eps.append((ep_name, full))

            if eps:
                # 线路名重复时加序号区分
                key = source_name
                idx = 2
                while key in lines:
                    key = f"{source_name}-{idx}"
                    idx += 1
                lines[key] = eps

        # 兜底: 全局正则搜 /dyplay/
        if not lines:
            sid_map = OrderedDict()
            for href in re.findall(r'href=["\']?(/dyplay/\d+-\d+-\d+(?:\.html?)?/?)["\']?', html, re.I):
                mm = _PLAY_HREF_RE.search(href)
                if not mm:
                    continue
                _, vid, sid, nid = mm.groups()
                full = f"{self.site_url}/dyplay/{vid}-{sid}-{nid}/"
                name = f"第{nid}集"
                tm = re.search(rf'<a[^>]*?href=["\']?{re.escape(href)}["\']?[^>]*>(.*?)</a>', html, re.I | re.DOTALL)
                if tm:
                    t = re.sub(r'<[^>]+>', '', tm.group(1)).strip()
                    if t:
                        name = t
                sid_map.setdefault(sid, [])
                if not any(full == u for _, u in sid_map[sid]):
                    sid_map[sid].append((name, full))
            for sid, eps in sid_map.items():
                lines[f"线路{sid}"] = eps

        # 按 URL 集数排序
        def _ep_sort_key(item):
            try:
                m = re.search(r'-\d+-\d+(?:\.html?)?/?$', item[1])
                if m:
                    parts = re.findall(r'\d+', m.group(0))
                    return int(parts[-1]) if parts else 0
            except Exception:
                pass
            return 0

        for key in lines:
            lines[key].sort(key=_ep_sort_key)

        play_from_list, play_url_list = [], []
        for frm, eps in lines.items():
            play_from_list.append(frm)
            play_url_list.append('#'.join(f"{n}${u}" for n, u in eps))

        if not play_from_list:
            play_from_list = ['默认源']
            play_url_list = [f"播放${url}"]

        return {"list": [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_area": vod_area,
            "vod_year": vod_year,
            "vod_play_from": '$$$'.join(play_from_list),
            "vod_play_url": '$$$'.join(play_url_list),
        }]}

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        encoded_key = urllib.parse.quote(key)
        url = f"{self.site_url}/tag/?wd={encoded_key}"
        if page > 1:
            url += f"&page={page}"

        resp = self._fetch(url, headers=self.headers)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1}

        video_list = self._parse_video_list(resp.text)
        html = resp.text
        pagecount = page
        nums = re.findall(r'[?&]page=(\d+)', html)
        if nums:
            pagecount = max(int(x) for x in nums)
        if re.search(r'(?:下\s*一\s*页|next|›|»)', html, re.I):
            pagecount = max(pagecount, page + 1)
        return {"list": video_list, "page": page, "pagecount": pagecount}

    def playerContent(self, flag, id, vipFlags):
        play_url = self._fix_url(id)

        if re.search(r'\.(m3u8|mp4|flv)(\?|$)', play_url, re.I):
            return {"parse": 0, "url": play_url, "header": self.headers}

        headers = dict(self.headers)
        headers['Referer'] = self.site_url + '/'
        max_depth = 8

        def _extract(url, depth, visited):
            if depth > max_depth or url in visited:
                return None
            visited.add(url)

            if re.search(r'\.(m3u8|mp4|flv)(\?|$)', url, re.I):
                return url

            resp = self._fetch(url, headers=headers)
            if not resp:
                return None
            html = resp.text

            # 苹果CMS player_aaaa 可能包含下一跳 link
            match = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*;?\s*</script>', html, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                    link = data.get('link', '') or data.get('url', '')
                    if link:
                        next_url = self._fix_url(link)
                        if next_url and next_url != url:
                            r = _extract(next_url, depth + 1, visited)
                            if r:
                                return r
                except Exception:
                    pass

            # 直接搜页面里的媒体 URL(黑夜影院 m3u8 直接出现在 HTML 中)
            m3u8 = re.search(r'(https?://[^\s"\']+\.(?:m3u8|mp4|flv)[^\s"\']*)', html, re.I)
            if m3u8:
                return m3u8.group(1)

            # iframe
            iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
            if iframe:
                iframe_url = self._fix_url(iframe.group(1))
                if iframe_url and iframe_url != url:
                    r = _extract(iframe_url, depth + 1, visited)
                    if r:
                        return r

            # video/source
            for pat in [
                r'<video[^>]+src=["\']([^"\']+)["\']',
                r'<source[^>]+src=["\']([^"\']+)["\']',
            ]:
                mm = re.search(pat, html)
                if mm:
                    return mm.group(1)

            # 常见 vars
            for pat in [
                r'var\s+playurl\s*=\s*["\']([^"\']+)["\']',
                r'var\s+url\s*=\s*["\']([^"\']+)["\']',
                r'var\s+video\s*=\s*["\']([^"\']+)["\']',
                r'var\s+src\s*=\s*["\']([^"\']+)["\']',
            ]:
                mm = re.search(pat, html, re.I)
                if mm:
                    val = mm.group(1)
                    if re.search(r'\.(m3u8|mp4|flv)', val, re.I):
                        return val
                    fixed = self._fix_url(val)
                    if fixed:
                        r = _extract(fixed, depth + 1, visited)
                        if r:
                            return r

            # 兜底: 页面内所有播放页链接
            for nl in re.findall(r'href=["\']([^"]*\/(?:dyplay|vodplay|play|player)\/\d+[^"\']*)["\']', html):
                next_url = self._fix_url(nl)
                if next_url and next_url != url:
                    r = _extract(next_url, depth + 1, visited)
                    if r:
                        return r

            return None

        visited = set()
        final_url = _extract(play_url, 0, visited)
        if final_url:
            final_url = self._fix_url(final_url)
            if re.search(r'\.(m3u8|mp4|flv)', final_url, re.I):
                return {"parse": 0, "url": final_url, "header": headers}
            return self.playerContent(flag, final_url, vipFlags)

        return {"parse": 1, "url": play_url, "header": headers}
