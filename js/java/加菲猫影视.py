# -*- coding: utf-8 -*-
# 加菲猫影视 www.cixilyjt.com — OK影视 / TvBox Python 源
# 基于 PyramidStore (CatVod) Spider 接口
# 站点类型：苹果CMS (MacCMS) + 海螺模板 (Conch v3.5)
# v2.1: 修复线路/剧集对应、完整二级分类、搜索、播放解析、性能优化

import sys
sys.path.append('..')
from base.spider import Spider
import json
import re
from urllib.parse import quote, unquote


class Spider(Spider):

    HOST = "http://www.cixilyjt.com"

    # ── 一级分类 ──
    CATE = {
        "电影": "1",
        "连续剧": "2",
        "综艺": "3",
        "动漫": "4",
        "短剧": "36",
    }

    # ── 二级分类 filter ──
    SUB_CATE = {
        "1": [
            {"n": "全部", "v": ""},
            {"n": "动作片", "v": "6"},
            {"n": "喜剧片", "v": "7"},
            {"n": "爱情片", "v": "8"},
            {"n": "科幻片", "v": "9"},
            {"n": "恐怖片", "v": "10"},
            {"n": "战争片", "v": "12"},
        ],
        "2": [
            {"n": "全部", "v": ""},
            {"n": "国产剧", "v": "13"},
            {"n": "港台剧", "v": "14"},
            {"n": "韩剧", "v": "15"},
            {"n": "美剧", "v": "16"},
            {"n": "日剧", "v": "26"},
            {"n": "海外剧", "v": "27"},
        ],
        "3": [
            {"n": "全部", "v": ""},
            {"n": "大陆综艺", "v": "23"},
            {"n": "港台综艺", "v": "24"},
            {"n": "国外综艺", "v": "25"},
        ],
        "4": [
            {"n": "全部", "v": ""},
            {"n": "国产动漫", "v": "20"},
            {"n": "日本动漫", "v": "21"},
            {"n": "欧美动漫", "v": "22"},
        ],
        "36": [
            {"n": "全部", "v": ""},
        ],
    }

    YEAR_FILTERS = [
        {"n": "全部", "v": ""},
        {"n": "2026", "v": "2026"}, {"n": "2025", "v": "2025"},
        {"n": "2024", "v": "2024"}, {"n": "2023", "v": "2023"},
        {"n": "2022", "v": "2022"}, {"n": "2021", "v": "2021"},
        {"n": "2020", "v": "2020"}, {"n": "2019", "v": "2019"},
        {"n": "2018", "v": "2018"}, {"n": "2017", "v": "2017"},
        {"n": "2016", "v": "2016"}, {"n": "2015", "v": "2015"},
        {"n": "更早", "v": "more"},
    ]

    AREA_FILTERS = [
        {"n": "全部", "v": ""},
        {"n": "中国大陆", "v": "中国大陆"},
        {"n": "中国香港", "v": "中国香港"},
        {"n": "中国台湾", "v": "中国台湾"},
        {"n": "美国", "v": "美国"},
        {"n": "韩国", "v": "韩国"},
        {"n": "日本", "v": "日本"},
        {"n": "英国", "v": "英国"},
        {"n": "泰国", "v": "泰国"},
        {"n": "印度", "v": "印度"},
        {"n": "其他", "v": "其他"},
    ]

    UA = "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"

    # ── 预编译正则 ──
    RE_LIST_ITEM = re.compile(
        r'<li[^>]*class="hl-list-item"[^>]*>.*?'
        r'<a[^>]*class="hl-item-thumb[^"]*"[^>]*'
        r'href="/varticle/(\d+)\.html"[^>]*'
        r'title="([^"]*)"[^>]*'
        r'(?:data-original|src)="([^"]*)"[^>]*>.*?'
        r'<span[^>]*class="[^"]*remarks[^"]*"[^>]*>(.*?)</span>.*?'
        r'</li>',
        re.S
    )
    RE_LIST_ITEM_SIMPLE = re.compile(
        r'<a[^>]*class="hl-item-thumb[^"]*"[^>]*'
        r'href="/varticle/(\d+)\.html"[^>]*'
        r'title="([^"]*)"[^>]*'
        r'(?:data-original|src)="([^"]*)"[^>]*>',
        re.S
    )
    RE_PAGE_LINK = re.compile(r'href="/vodshow/\d+[-]+(\d+)\.html"')
    RE_PAGE_LINK2 = re.compile(r'page=(\d+)')
    RE_OG_IMAGE = re.compile(r'<meta[^>]*og:image[^>]*content="([^"]+)"', re.I)
    RE_OG_IMAGE2 = re.compile(r'<meta[^>]*content="([^"]+)"[^>]*og:image', re.I)
    RE_DETAIL_TITLE = re.compile(r'<h2[^>]*class="hl-dc-title[^"]*"[^>]*>(.*?)</h2>', re.S)
    RE_DETAIL_SUB = re.compile(r'<div[^>]*class="hl-dc-sub"[^>]*>(.*?)</div>', re.S)
    RE_DETAIL_PIC = re.compile(r'<span[^>]*class="hl-item-thumb[^"]*"[^>]*data-original="([^"]+)"', re.S)
    RE_SCORE = re.compile(r'<span[^>]*class="[^"]*score[^"]*"[^>]*>(\d+\.?\d*)</span>')
    RE_YEAR = re.compile(r'<em[^>]*>年份[：:]</em>\s*(\d{4})')
    RE_AREA = re.compile(r'<em[^>]*>地区[：:]</em>\s*([^<]+)')
    RE_REMARKS = re.compile(r'<em[^>]*>状态[：:]</em>\s*<span[^>]*>([^<]+)</span>')
    RE_UPDATE = re.compile(r'<em[^>]*>更新[：:]</em>\s*([^<]+)')
    RE_DETAIL_BLURB = re.compile(r'<em[^>]*class="hl-text-muted"[^>]*>简介[：:]</em>(.*?)</li>', re.S)
    RE_REM_TAG = re.compile(r'<[^>]+>')
    RE_PLAY_SOURCE = re.compile(r'<a[^>]*class="hl-tabs-btn[^"]*"[^>]*alt="([^"]*)"[^>]*>')
    RE_PLAY_BOX = re.compile(
        r'<div class="hl-tabs-box[^"]*"[^>]*>.*?'
        r'<ul class="hl-plays-list[^"]*"[^>]*>(.*?)</ul>.*?</div>',
        re.S
    )
    RE_PLAY_EP = re.compile(r'<a[^>]*href="/vplay/(\d+)-(\d+)-(\d+)\.html"[^>]*>(.*?)</a>', re.S)
    RE_PLAYER_AAAA = re.compile(r'player_aaaa\s*=\s*(\{.*?\})\s*[;<]', re.S)
    RE_PLAYER_DATA = re.compile(r'player_data\s*=\s*(\{.*?\})\s*[;<]', re.S)
    RE_MEDIA_M3U8 = re.compile(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', re.I)
    RE_MEDIA_MP4 = re.compile(r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)', re.I)

    def getName(self):
        return "加菲猫影视"

    def init(self, extend=""):
        pass

    # ════════════ 首页 ════════════

    def homeContent(self, filter):
        result = {}
        classes = [{'type_name': n, 'type_id': self.CATE[n]} for n in self.CATE]
        result['class'] = classes
        if filter:
            filters = {}
            for cid in self.CATE.values():
                flist = []
                if cid in self.SUB_CATE:
                    flist.append({"key": "type", "name": "类型", "value": self.SUB_CATE[cid]})
                flist.append({"key": "year", "name": "年份", "value": self.YEAR_FILTERS})
                flist.append({"key": "area", "name": "地区", "value": self.AREA_FILTERS})
                filters[cid] = flist
            result['filters'] = filters
        return result

    def homeVideoContent(self):
        result = {'list': []}
        try:
            html = self._fetch_html(self.HOST + "/vtype/1.html")
            videos = self._parse_list_html(html)
            result = {'list': videos[:30]}
        except:
            pass
        return result

    # ════════════ 分类列表 ════════════

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        result = {'list': [], 'page': page, 'pagecount': 1, 'limit': 30, 'total': 0}
        try:
            sub_type = ""
            year = ""
            area = ""
            if extend:
                sub_type = extend.get('type', '')
                year = extend.get('year', '')
                area = extend.get('area', '')

            has_filter = bool(sub_type or year or area)

            if not has_filter:
                if page <= 1:
                    url = "{0}/vtype/{1}.html".format(self.HOST, tid)
                else:
                    url = "{0}/vodshow/{1}-----------{2}.html".format(self.HOST, tid, page)
            else:
                area_enc = quote(area) if area else ""
                sub_enc = quote(sub_type) if sub_type else ""
                year_enc = year if year else ""
                if page <= 1:
                    url = "{0}/vodshow/{1}-{2}---{3}---{4}---.html".format(
                        self.HOST, tid, area_enc, sub_enc, year_enc)
                else:
                    url = "{0}/vodshow/{1}-{2}---{3}---{4}-{5}.html".format(
                        self.HOST, tid, area_enc, sub_enc, year_enc, page)

            html = self._fetch_html(url)
            result['list'] = self._parse_list_html(html)
            pagecount = self._parse_pagecount(html)
            result['pagecount'] = pagecount if pagecount else 9999
            result['total'] = 999999
        except:
            pass
        return result

    # ════════════ 详情 ════════════

    def detailContent(self, array):
        try:
            return self._detail_inner(array)
        except Exception as e:
            vod_id = str(array[0]) if array else ""
            return {
                'list': [{
                    "vod_id": vod_id, "vod_name": "解析异常", "vod_pic": "",
                    "type_name": "", "vod_year": "", "vod_area": "", "vod_remarks": "",
                    "vod_actor": "", "vod_director": "", "vod_content": str(e)[:200],
                    "vod_play_from": "默认线路",
                    "vod_play_url": "播放$" + vod_id + "___0___0"
                }]
            }

    def _detail_inner(self, array):
        vod_id = str(array[0])
        html = self._fetch_html("{0}/varticle/{1}.html".format(self.HOST, vod_id))
        if not html or len(html) < 200:
            raise Exception("详情页获取失败")

        title = self._m(self.RE_DETAIL_TITLE, html)
        title = self.RE_REM_TAG.sub('', title).strip() if title else ""

        pic = self._extract_detail_pic(html)
        score = self._m(self.RE_SCORE, html)
        year = self._m(self.RE_YEAR, html)
        area = self._m(self.RE_AREA, html).strip()
        remarks = self._m(self.RE_REMARKS, html).strip()
        if not remarks:
            remarks = self._m(self.RE_UPDATE, html).strip()

        director = self._extract_info_by_label(html, '导演')
        actor = self._extract_info_by_label(html, '主演')
        type_name = self._extract_info_by_label(html, '类型')

        content = ""
        m = self.RE_DETAIL_BLURB.search(html)
        if m:
            content = self.RE_REM_TAG.sub('', m.group(1)).replace('&nbsp;', ' ').strip()
            if len(content) > 500:
                content = content[:500] + '...'

        vod = {
            "vod_id": vod_id, "vod_name": title, "vod_pic": pic,
            "type_name": type_name, "vod_year": year, "vod_area": area,
            "vod_remarks": remarks, "vod_actor": actor, "vod_director": director,
            "vod_content": content, "vod_score": score,
        }
        vod["vod_play_from"], vod["vod_play_url"] = self._parse_play_list(html, vod_id)
        return {'list': [vod]}

    # ════════════ 搜索 ════════════

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        result = {'list': []}
        try:
            encoded_key = quote(key)
            if page <= 1:
                url = "{0}/vodsearch/{1}-------------.html".format(self.HOST, encoded_key)
            else:
                url = "{0}/vodsearch/{1}------------{2}.html".format(self.HOST, encoded_key, page)
            html = self._fetch_html(url)
            result = {'list': self._parse_list_html(html)}
        except:
            pass
        return result

    # ════════════ 播放解析 ════════════

    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 1, "url": "", "header": ""}
        try:
            parts = id.split("___")
            if len(parts) < 3:
                return {"parse": 0, "url": id, "header": ""}
            vod_id, sid, nid = parts[0], parts[1], parts[2]

            play_url = "{0}/vplay/{1}-{2}-{3}.html".format(self.HOST, vod_id, sid, nid)
            html = self._fetch_html(play_url)

            player_json = self._extract_player_data(html)
            if player_json and player_json.get('url', ''):
                real_url = player_json['url']
                encrypt = player_json.get('encrypt', 0)
                if encrypt == 1:
                    real_url = unquote(real_url)
                elif encrypt == 2:
                    real_url = self._aes_decrypt(real_url, html)
                result = {
                    "parse": 0, "playUrl": "", "url": real_url,
                    "header": json.dumps(self._play_header())
                }
            else:
                media_url = self._extract_media_url(html)
                if media_url:
                    result = {
                        "parse": 0, "url": media_url,
                        "header": json.dumps(self._play_header())
                    }
                else:
                    result = {"parse": 1, "url": play_url, "header": ""}
        except:
            pass
        return result

    # ════════════ 辅助：网络 ════════════

    def _headers(self):
        return {
            "User-Agent": self.UA,
            "Referer": self.HOST + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def _play_header(self):
        return {"User-Agent": self.UA, "Referer": self.HOST + "/"}

    def _fetch_html(self, url):
        rsp = self.fetch(url, headers=self._headers(), timeout=10)
        try:
            rsp.encoding = rsp.apparent_encoding or 'utf-8'
        except:
            pass
        return rsp.text

    # ════════════ 辅助：列表解析 ════════════

    def _parse_list_html(self, html):
        videos = []
        seen = set()

        for m in self.RE_LIST_ITEM.finditer(html):
            vid = m.group(1)
            if vid in seen:
                continue
            name = m.group(2).strip()
            pic = m.group(3).strip()
            remarks = self.RE_REM_TAG.sub('', m.group(4)).strip()
            if not name:
                continue
            seen.add(vid)
            videos.append({
                "vod_id": str(vid), "vod_name": name,
                "vod_pic": pic, "vod_remarks": remarks
            })

        if not videos:
            for m in self.RE_LIST_ITEM_SIMPLE.finditer(html):
                vid = m.group(1)
                if vid in seen:
                    continue
                name = m.group(2).strip()
                pic = m.group(3).strip()
                if not name:
                    continue
                seen.add(vid)
                videos.append({
                    "vod_id": str(vid), "vod_name": name,
                    "vod_pic": pic, "vod_remarks": ""
                })

        return videos

    def _parse_pagecount(self, html):
        pages = self.RE_PAGE_LINK.findall(html)
        if pages:
            nums = [int(p) for p in pages if p.isdigit() and int(p) > 0]
            if nums:
                return max(nums)
        pages2 = self.RE_PAGE_LINK2.findall(html)
        if pages2:
            nums = [int(p) for p in pages2 if p.isdigit() and int(p) > 0]
            if nums:
                return max(nums)
        return 0

    # ════════════ 辅助：详情页解析 ════════════

    def _extract_detail_pic(self, html):
        m = self.RE_OG_IMAGE.search(html) or self.RE_OG_IMAGE2.search(html)
        if m:
            return m.group(1)
        m = self.RE_DETAIL_PIC.search(html)
        if m:
            return m.group(1)
        return ""

    def _extract_info_by_label(self, html, keyword):
        idx = html.find('>' + keyword + '：')
        if idx == -1:
            idx = html.find('>' + keyword + ':')
        if idx == -1:
            return ""
        start = html.rfind('<li', max(0, idx - 200), idx)
        end = html.find('</li>', idx)
        if end == -1:
            end = idx + 500
        block = html[start:end]
        names = re.findall(r'>([^<]+)</a>', block)
        if not names:
            names = re.findall(r'>([^<]+)</span>', block)
        result = ' '.join(n.strip() for n in names if n.strip() and n.strip() not in ('/', '：', ':'))
        return result

    def _parse_play_list(self, html, vod_id):
        """
        海螺模板：线路名在 hl-tabs-btn 的 alt 属性中，
        剧集在对应的 hl-tabs-box 中，按索引一一对应。
        """
        sources = self.RE_PLAY_SOURCE.findall(html)
        boxes = self.RE_PLAY_BOX.findall(html)

        if not sources:
            ep_matches = self.RE_PLAY_EP.findall(html)
            if ep_matches:
                items = []
                for vid, sid, nid, ep_name in ep_matches:
                    ep_name = ep_name.strip()
                    if not ep_name:
                        ep_name = "第" + str(int(nid)).zfill(2) + "集"
                    items.append("{0}${1}___{2}___{3}".format(ep_name, vid, sid, nid))
                if items:
                    return "默认线路", "#".join(items)
            return "默认线路", "播放$" + vod_id + "___0___0"

        play_from_list = []
        play_url_list = []

        for i, box_html in enumerate(boxes):
            if i >= len(sources):
                break
            tab_name = sources[i].strip()
            if not tab_name:
                tab_name = "线路" + str(i + 1)

            ep_matches = self.RE_PLAY_EP.findall(box_html)
            if not ep_matches:
                continue

            items = []
            for vid, sid, nid, ep_name in ep_matches:
                ep_name = ep_name.strip()
                if not ep_name:
                    ep_name = "第" + str(int(nid)).zfill(2) + "集"
                items.append("{0}${1}___{2}___{3}".format(ep_name, vid, sid, nid))

            if items:
                play_from_list.append(tab_name)
                play_url_list.append("#".join(items))

        if play_from_list:
            return "$$$".join(play_from_list), "$$$".join(play_url_list)

        return "默认线路", "播放$" + vod_id + "___0___0"

    # ════════════ 辅助：播放器 ════════════

    def _extract_player_data(self, html):
        for pat in (self.RE_PLAYER_AAAA, self.RE_PLAYER_DATA):
            m = pat.search(html)
            if m:
                try:
                    return json.loads(m.group(1))
                except:
                    pass
        m = re.search(r'(player_\w+)\s*=\s*(\{[^}]+\})', html, re.S)
        if m:
            try:
                return json.loads(m.group(2))
            except:
                pass
        return {}

    def _extract_media_url(self, html):
        m = self.RE_MEDIA_M3U8.search(html) or self.RE_MEDIA_MP4.search(html)
        if not m:
            m = re.search(r'(https?://[^\s"\'<>]+\.flv[^\s"\'<>]*)', html, re.I)
        return m.group(1) if m else ""

    def _aes_decrypt(self, encrypted, html):
        try:
            key_match = re.search(r'key\s*[:=]\s*["\']([A-Za-z0-9]{16})["\']', html)
            key = key_match.group(1) if key_match else "28fd7d0f7dac4156"
            from Crypto.Cipher import AES
            import base64
            cipher = AES.new(key.encode(), AES.MODE_ECB)
            decrypted = cipher.decrypt(base64.b64decode(encrypted))
            pad = decrypted[-1]
            return decrypted[:-pad].decode('utf-8', errors='ignore')
        except:
            return encrypted

    # ════════════ 通用 ════════════

    def _m(self, regex, text):
        m = regex.search(text)
        return m.group(1) if m else ""

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def localProxy(self, param):
        return [200, "video/MP2T", "", ""]
