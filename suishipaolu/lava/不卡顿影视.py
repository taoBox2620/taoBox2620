# -*- coding: utf-8 -*-
import re
from urllib.parse import quote, urlparse

import requests as _rq
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.baseUrl = "https://www.yingshiso.top"
        self.ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
        self.headers = {"User-Agent": self.ua, "Referer": self.baseUrl + "/"}
        return self

    def getName(self):
        return "不卡顿影视"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def _fetch(self, path):
        url = path if path.startswith("http") else self.baseUrl + path
        try:
            rsp = self.fetch(url, headers=self.headers, timeout=10)
            return rsp.text or ""
        except Exception:
            return ""

    def _doc(self, html):
        try:
            from lxml import etree
            return etree.HTML(html or "")
        except Exception:
            return None

    def _parse_list(self, html):
        doc = self._doc(html)
        if doc is None:
            return []

        items, seen = [], set()

        boxes = doc.xpath('//div[contains(@class,"myui-vodlist__box")]')
        if not boxes:
            boxes = doc.xpath('//ul[contains(@class,"myui-vodlist__media")]/li')

        for box in boxes:
            a = box.xpath('.//a[contains(@class,"myui-vodlist__thumb")]')
            if not a:
                continue
            a = a[0]
            href = a.get("href", "") or ""
            m = re.search(r"/detail/\?(\d+)\.html", href)
            if not m:
                continue
            vid = m.group(1)
            if vid in seen:
                continue
            seen.add(vid)

            name = (a.get("title") or "").strip()
            if not name:
                name = "".join(box.xpath('.//h4[contains(@class,"title")]//text()')).strip()

            pic = (a.get("data-original") or a.get("data-src") or "").strip()
            note = "".join(box.xpath('.//span[contains(@class,"pic-text")]//text()')).strip()

            items.append({
                "vod_id": vid,
                "vod_name": name,
                "vod_pic": pic,
                "vod_remarks": note,
            })
        return items

    def _parse_pagecount(self, html, default=1):
        m = re.search(r'class="btn btn-warm">\s*(\d+)\s*/\s*(\d+)', html or "")
        return int(m.group(2)) if m else default

    CATE_LIST = [
        {"type_id": "1", "type_name": "电影"},
        {"type_id": "2", "type_name": "电视剧"},
        {"type_id": "3", "type_name": "综艺"},
        {"type_id": "4", "type_name": "动漫"},
    ]

    def homeContent(self, filter):
        return {
            "class": self.CATE_LIST,
            "list": self._parse_list(self._fetch("/")),
        }

    def homeVideoContent(self):
        return {"list": self._parse_list(self._fetch("/"))}

    def categoryContent(self, tid, pg, filter, extend):
        tid = str(tid)
        pg = str(pg) if pg else "1"

        url = "/list/?%s.html" % tid if pg == "1" else "/list/?%s-%s.html" % (tid, pg)
        html = self._fetch(url)

        seg = html
        m = re.search(r"<!--\s*筛选\s*-->(.*?)<!--\s*翻页", html, re.S)
        if m:
            seg = m.group(1)

        items = self._parse_list(seg)

        try:
            page_num = int(pg)
        except ValueError:
            page_num = 1

        total = self._parse_pagecount(html)

        return {
            "list": items,
            "page": page_num,
            "pagecount": total,
            "limit": len(items),
            "total": len(items) * total,
        }

    def detailContent(self, array):
        vid = array[0] if isinstance(array, list) else array
        html = self._fetch("/detail/?%s.html" % vid)

        seg = html
        m = re.search(r"<!--\s*详细信息\s*-->(.*?)<!--\s*播放列表", html, re.S)
        if m:
            seg = m.group(1)

        doc = self._doc(seg)

        name, pic = "", ""
        if doc is not None:
            h = doc.xpath('//h1//text()|//h2//text()|//meta[@property="og:title"]/@content')
            if h:
                name = "".join(h).strip()

            p = doc.xpath('//meta[@property="og:image"]/@content'
                          '|//img[@class="myui-vodlist__thumb"]/@data-original'
                          '|//img[@class="myui-vodlist__thumb"]/@src')
            if p:
                pic = p[0]

        def grab(label):
            mm = re.search(label + r"：</span>(.*?)(?:<span class=\"split-line|</p>)", seg, re.S)
            if not mm:
                return ""
            t = re.sub(r"<[^>]+>", " ", mm.group(1)).replace("&nbsp;", " ")
            return re.sub(r"\s+", " ", t).strip()

        def grab_lxml(label):
            if doc is None:
                return ""
            try:
                for sp in doc.xpath('//span[contains(@class,"text-muted")]'):
                    if (sp.text or "").strip().startswith(label):
                        a = sp.getnext()
                        while a is not None and a.tag != "a":
                            a = a.getnext()
                        if a is not None and a.text:
                            return a.text.strip()
                        parent = sp.getparent()
                        if parent is not None:
                            aa = parent.xpath('.//a')
                            if aa:
                                return (aa[0].text or "").strip()
            except Exception:
                pass
            return ""

        vod_class    = grab("分类") or grab_lxml("分类")
        vod_area     = grab("地区") or grab_lxml("地区")
        vod_year     = grab("年份") or grab_lxml("年份")
        vod_actor    = grab("主演")
        vod_director = grab("导演")
        vod_remarks  = grab("更新")

        vod_content = ""
        mc = re.search(r'<span class="(?:sketch )?content"[^>]*>(.*?)</span>', html, re.S)
        if mc:
            vod_content = re.sub(r"<[^>]+>", "", mc.group(1)).replace("&nbsp;", " ").strip()
        if not vod_content:
            mc = re.search(r"简介：</span>(.*?)(?:<a|</p>)", seg, re.S)
            if mc:
                vod_content = re.sub(r"<[^>]+>", "", mc.group(1)).replace("&nbsp;", " ").strip()
        vod_content = re.sub(r"\s+", " ", vod_content).strip()

        doc2 = self._doc(html)
        play_froms, play_urls = [], []
        if doc2 is not None:
            for tab in doc2.xpath('//ul[contains(@class,"nav-tabs")]/li/a[contains(@href,"#playlist")]'):
                pid = (tab.get("href") or "").replace("#", "")
                fname = (tab.text or "").strip()
                panels = doc2.xpath('//div[@id="%s"]' % pid)
                if not panels:
                    continue
                eps = []
                for a in panels[0].xpath('.//ul/li/a[@href]'):
                    eurl   = (a.get("href") or "").strip()
                    etitle = (a.get("title") or (a.text or "")).strip()
                    if eurl:
                        eps.append("%s$%s" % (etitle, eurl))
                if eps:
                    play_froms.append(fname)
                    play_urls.append("#".join(eps))

        vod = {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "vod_remarks": vod_remarks,
            "vod_class": vod_class,
            "vod_area": vod_area,
            "vod_year": vod_year,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_content": vod_content,
            "vod_play_from": "$$$".join(play_froms),
            "vod_play_url":  "$$$".join(play_urls),
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        try:
            sess = _rq.Session()
            sess.headers.update(self.headers)

            sess.get(self.baseUrl + "/search.php?searchword=" + quote(key), timeout=10)

            r = sess.get(self.baseUrl + "/include/vdimgck.php", timeout=10)
            try:
                ans = (vcode_ask(r.content) or "").strip()
            except Exception:
                return {"list": []}
            if not ans:
                return {"list": []}

            data = {
                "validate": ans, "searchword": key, "scheckAC": "check",
                "page": "", "searchtype": "", "order": "", "tid": "",
                "area": "", "year": "", "letter": "", "yuyan": "",
                "state": "", "money": "", "ver": "", "jq": "",
            }
            pr = sess.post(self.baseUrl + "/search.php", data=data, timeout=10)
            if "安全验证" in pr.text:
                return {"list": []}

            seg = pr.text
            m = re.search(r'<div class="myui-panel_bd col-pd clearfix">(.*?)<div class="col-lg-wide-3',
                          pr.text, re.S)
            if m:
                seg = m.group(1)

            items = self._parse_list(seg)

            page, total = 1, 1
            mt = re.search(r'class="btn btn-warm">\s*(\d+)\s*/\s*(\d+)', pr.text)
            if mt:
                page  = int(mt.group(1))
                total = int(mt.group(2))

            return {
                "list": items,
                "page": page,
                "pagecount": total,
                "limit": 30,
                "total": 30 * total,
            }
        except Exception:
            return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        header = ("User-Agent: " + self.ua + "\n"
                  + "Referer: " + self.baseUrl + "/")

        html = self._fetch(id)
        url = ""

        m = re.search(r'var\s+now\s*=\s*"([^"]+)"', html)
        if m:
            now = m.group(1)
            if ".m3u8" in now:
                url = now
            else:
                try:
                    share = _rq.get(now, headers={
                        "User-Agent": self.ua, "Referer": now,
                    }, timeout=10).text
                except Exception:
                    share = ""

                mu = re.search(r'const\s+url\s*=\s*["\']([^"\']+)["\']', share)
                if mu:
                    path = mu.group(1)
                    if path.startswith("http"):
                        url = path
                    else:
                        p = urlparse(now)
                        url = p.scheme + "://" + p.netloc + path
                else:
                    mu = re.search(r"const\s+vid\s*=\s*['\"]([^'\"]+\.m3u8[^'\"]*)['\"]", share)
                    if mu:
                        url = mu.group(1)

        if not url:
            m = re.search(r"const\s+vid\s*=\s*['\"]([^'\"]+\.m3u8[^'\"]*)['\"]", html)
            if m:
                url = m.group(1)
        if not url:
            m = re.search(r"(https?://[^\"'<>\s]+\.m3u8[^\"'<>\s]*)", html)
            if m:
                url = m.group(1)

        if not url:
            return {
                "parse": 1,
                "playUrl": "",
                "url": id,
                "header": header,
                "flag": flag,
            }

        return {
            "parse": 0,
            "playUrl": "",
            "url": url,
            "header": header,
            "flag": flag,
        }