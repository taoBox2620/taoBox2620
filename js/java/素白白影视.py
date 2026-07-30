# -*- coding: utf-8 -*-
import json
import re
from urllib.parse import quote, urljoin

import requests
from lxml import etree
from base.spider import Spider


class Spider(Spider):
    def getName(self): return "素白白影视"

    def init(self, extend=""):
        self.host = "https://www.wczzs.cc"
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": self.host + "/"}
        self.classes = [{"type_id": "1", "type_name": "电影"}, {"type_id": "2", "type_name": "电视剧"}, {"type_id": "4", "type_name": "动漫"}, {"type_id": "3", "type_name": "综艺"}, {"type_id": "9", "type_name": "短视频"}, {"type_id": "51", "type_name": "即将上映"}]
        self.subtypes = {
            "1": [("全部", "1"), ("喜剧片", "35"), ("动作片", "36"), ("爱情片", "37"), ("科幻片", "38"), ("恐怖片", "39"), ("剧情片", "40"), ("战争片", "41")],
            "2": [("全部", "2"), ("国产剧", "42"), ("港台剧", "43"), ("日韩剧", "44"), ("欧美剧", "45")],
            "3": [("全部", "3"), ("国内综艺", "46"), ("海外综艺", "47")],
            "4": [("全部", "4"), ("国内动漫", "48"), ("海外动漫", "49")],
            "9": [("全部", "9"), ("动画短片", "57"), ("短剧", "58")]
        }
        letters = [{"n": "全部", "v": ""}] + [{"n": x, "v": x} for x in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
        years = [{"n": "全部", "v": ""}] + [{"n": str(x), "v": str(x)} for x in range(2026, 2015, -1)]
        self.filters = {tid: [{"key": "type", "name": "类型", "value": [{"n": n, "v": v} for n, v in values]}, {"key": "letter", "name": "字母", "value": letters}, {"key": "year", "name": "年份", "value": years}] for tid, values in self.subtypes.items()}

    def _get(self, url):
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            return response.text
        except Exception:
            return ""

    def _fix_url(self, url): return urljoin(self.host + "/", url or "")

    def _parse_list(self, html):
        if not html: return []
        tree, result, seen = etree.HTML(html), [], set()
        nodes = tree.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," ysList6 ")]/a[starts-with(@href,"/wczzch/") and .//img]') or tree.xpath('//a[starts-with(@href,"/wczzch/") and .//img[@data-src or @data-original]]')
        for node in nodes:
            match = re.search(r"/wczzch/(\d+)\.html", node.get("href", ""))
            if not match or match.group(1) in seen: continue
            seen.add(match.group(1))
            img = node.xpath(".//img")[0]
            name = img.get("alt") or "".join(node.xpath('.//div[contains(@class,"ys-name")]//text()')).strip()
            pic = img.get("data-original") or img.get("data-src") or img.get("data-lazyload") or img.get("src", "")
            result.append({"vod_id": match.group(1), "vod_name": name.strip(), "vod_pic": self._fix_url(pic)})
        return result

    def _pagecount(self, tree):
        value = "".join(tree.xpath('//span[contains(@class,"total")]/text()')).strip()
        return int(value) if value.isdigit() else 1

    def homeContent(self, filter):
        return {"class": self.classes, "list": self._parse_list(self._get(self.host + "/")), "filters": self.filters}

    def categoryContent(self, tid, pg, filter, extend):
        page, ext = max(1, int(pg or 1)), extend if isinstance(extend, dict) else {}
        selected = str(ext.get("type") or tid)
        letter, year = str(ext.get("letter") or ""), str(ext.get("year") or "")
        filtered = bool(letter or year)
        if filtered:
            fields = [""] * 12
            fields[0], fields[4], fields[5] = selected, year, letter
            url = f'{self.host}/wczzchshow/{"-".join(fields)}.html'
        else:
            url = f"{self.host}/wczzchtype/{selected}-{page}.html"
        html = self._get(url)
        tree = etree.HTML(html) if html else etree.HTML("<html/>")
        pagecount = 1 if filtered else self._pagecount(tree)
        videos = self._parse_list(html)
        return {"page": 1 if filtered else page, "pagecount": pagecount, "limit": len(videos), "total": pagecount * max(len(videos), 1), "list": videos}

    def detailContent(self, ids):
        result = []
        for vid in ids:
            html = self._get(f"{self.host}/wczzch/{vid}.html")
            if not html: continue
            tree = etree.HTML(html)
            name = "".join(tree.xpath('//div[contains(@class,"ys-name18")]/text()')).strip()
            pic = "".join(tree.xpath('//a[contains(@class,"poster5")]//img/@data-src'))
            content = " ".join(x.strip() for x in tree.xpath('//div[contains(@class,"Synopsis-word")]//p[1]//text()') if x.strip())
            director = " ".join(x.strip() for x in tree.xpath('//div[contains(@class,"main-actors2")][1]//a//text()') if x.strip())
            actor = " ".join(x.strip() for x in tree.xpath('//div[contains(@class,"main-actors2")][2]//a//text()') if x.strip())
            sources, playlists = [], []
            for title in tree.xpath('//div[contains(@class,"list-name23")]'):
                panel = title.xpath('following-sibling::*[1][self::div[contains(@class,"list-number1")]]')
                if not panel: continue
                episodes = panel[0].xpath('.//a[contains(@href,"/wczzchplay/")]')
                if not episodes: continue
                source = "".join(title.xpath('.//div[contains(@class,"name17")]//text()')).strip() or f"线路{len(sources) + 1}"
                plays = []
                for episode in episodes:
                    label = "".join(episode.xpath(".//text()")).strip() or str(len(plays) + 1)
                    plays.append(f'{label}${self._fix_url(episode.get("href", ""))}')
                sources.append(source)
                playlists.append("#".join(plays))
            result.append({"vod_id": str(vid), "vod_name": name, "vod_pic": self._fix_url(pic), "vod_actor": actor, "vod_director": director, "vod_content": content, "vod_play_from": "$$$".join(sources), "vod_play_url": "$$$".join(playlists)})
        return {"list": result}

    def searchContent(self, key, quick, pg="1"):
        page = max(1, int(pg or 1))
        url = f"{self.host}/search/{quote(key)}--{page}-----------.html"
        html = self._get(url)
        tree = etree.HTML(html) if html else etree.HTML("<html/>")
        return {"page": page, "pagecount": self._pagecount(tree), "list": self._parse_list(html)}

    def playerContent(self, flag, id, vipFlags):
        url = self._fix_url(id)
        html = self._get(url)
        match = re.search(r"player_aaaa\s*=\s*(\{.*?\})\s*</script>", html)
        if match:
            try:
                play_url = json.loads(match.group(1)).get("url", "")
                if play_url and any(x in play_url.lower() for x in (".m3u8", ".mp4", ".flv")): return {"parse": 0, "url": play_url, "header": {"User-Agent": self.headers["User-Agent"], "Referer": url}}
            except Exception:
                pass
        return {"parse": 1, "url": url, "header": self.headers}
