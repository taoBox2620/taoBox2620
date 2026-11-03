# coding=utf-8
# !/usr/bin/python
"""
TVBox 爬虫插件 - bjhaobo.cn（策驰影院）
"""

import sys
import re
import json
import time
import requests
import base64
from urllib.parse import urljoin, quote

sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def init(self, extend=""):
            pass


class Spider(BaseSpider):
    # ==================== 基础配置 ====================
    host = "https://bjhaobo.cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://bjhaobo.cn/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    # 采集页面数
    max_page = 5

    def init(self, extend=""):
        """初始化"""
        self.extend = extend
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.timeout = 15

    # ==================== 工具方法 ====================
    def _get(self, url, retry=3):
        """带重试的 GET 请求"""
        for i in range(retry):
            try:
                time.sleep(1)
                r = self.session.get(url, timeout=self.timeout, verify=False)
                if r.status_code == 200:
                    r.encoding = "utf-8"
                    return r.text
            except Exception as e:
                print(f"[GET ERROR] {url} -> {e}")
                time.sleep(2)
        return ""

    def _abs(self, url):
        """补全绝对地址"""
        if not url:
            return ""
        if url.startswith("http"):
            return url
        return urljoin(self.host, url)

    def _clean(self, text):
        """清理文本"""
        if not text:
            return ""
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&nbsp;", " ").replace("&amp;", "&")
        text = text.replace("&quot;", '"').replace("&#39;", "'")
        return text.strip()

    # ==================== 首页 ====================
    def homeContent(self, filter):
        """首页分类"""
        result = {"class": []}
        # 从首页导航提取分类
        html = self._get(self.host + "/")
        if html:
            # 匹配导航中的分类链接
            pattern = r'<a[^>]+class="[^"]*fed-menu-title[^"]*"[^>]+href="(/vodtype/[^"]+)"[^>]*>([^<]+)</a>'
            matches = re.findall(pattern, html)
            seen = set()
            for href, name in matches:
                name = self._clean(name)
                if name and name not in seen and "首页" not in name:
                    seen.add(name)
                    tid = href.replace("/vodtype/", "").replace(".html", "")
                    result["class"].append({
                        "type_id": tid,
                        "type_name": name
                    })

        # 兜底默认分类
        if not result["class"]:
            default_types = [
                ("dianying", "电影"),
                ("lianxuju", "连续剧"),
                ("zongyi", "综艺"),
                ("dongman", "动漫"),
                ("guochanju", "国产剧"),
                ("gangtaiju", "港台剧"),
                ("rihanju", "日韩剧"),
                ("oumeiju", "欧美剧"),
                ("dongzuopian", "动作片"),
                ("xijupian", "喜剧片"),
                ("aiqingpian", "爱情片"),
                ("kehuanpian", "科幻片"),
                ("kongbupian", "恐怖片"),
                ("juqingpian", "剧情片"),
                ("zhanzhengpian", "战争片"),
            ]
            for tid, name in default_types:
                result["class"].append({
                    "type_id": tid,
                    "type_name": name
                })
        return result

    # ==================== 分类列表 ====================
    def categoryContent(self, tid, pg, filter, extend):
        """分类内容"""
        result = {
            "list": [],
            "page": int(pg),
            "pagecount": 999,
            "limit": 20,
            "total": 9999,
        }

        # 构建 URL：第一页为 /vodtype/{tid}.html，之后为 /vodtype/{tid}-{pg}.html
        if int(pg) <= 1:
            url = f"{self.host}/vodtype/{tid}.html"
        else:
            url = f"{self.host}/vodtype/{tid}-{pg}.html"

        html = self._get(url)
        if not html:
            return result

        # 提取影片列表块
        # 每个 li：<li class="...fed-list-item..."> ... </li>
        li_pattern = r'<li[^>]+class="[^"]*fed-list-item[^"]*"[^>]*>(.*?)</li>'
        items = re.findall(li_pattern, html, re.S)

        for item in items:
            try:
                # 详情页链接
                href_match = re.search(r'href="(/voddetail/[^"]+\.html)"', item)
                if not href_match:
                    continue
                detail_url = href_match.group(1)
                vod_id = detail_url.replace("/voddetail/", "").replace(".html", "")

                # 封面图 data-original 或 background-image
                pic = ""
                pic_match = re.search(r'data-original="([^"]+)"', item)
                if pic_match:
                    pic = pic_match.group(1)
                else:
                    bg_match = re.search(r'background-image:\s*url\(["\']?([^"\')]+)["\']?\)', item)
                    if bg_match:
                        pic = bg_match.group(1)

                # 标题
                title = ""
                title_match = re.search(
                    r'class="[^"]*fed-list-title[^"]*"[^>]*>([^<]+)</a>', item)
                if title_match:
                    title = self._clean(title_match.group(1))

                # 备注
                remarks = ""
                remarks_match = re.search(
                    r'class="[^"]*fed-list-remarks[^"]*"[^>]*>([^<]+)</span>', item)
                if remarks_match:
                    remarks = self._clean(remarks_match.group(1))

                if vod_id and title:
                    result["list"].append({
                        "vod_id": vod_id,
                        "vod_name": title,
                        "vod_pic": self._abs(pic),
                        "vod_remarks": remarks,
                    })
            except Exception as e:
                print(f"[CATEGORY PARSE ERROR] {e}")
                continue

        # 计算总页数
        page_match = re.search(r'data-total="(\d+)"', html)
        if page_match:
            result["pagecount"] = int(page_match.group(1))

        return result

    # ==================== 搜索 ====================
    def searchContent(self, key, quick, pg=1, category=""):
        """搜索内容"""
        result = {
            "list": [],
            "page": int(pg),
            "pagecount": 999,
            "limit": 20,
            "total": 9999,
        }

        # 搜索 URL 格式：/vodsearch/{key}----------{pg}.html
        encoded_key = quote(key)
        if int(pg) <= 1:
            url = f"{self.host}/vodsearch/{encoded_key}-------------.html"
        else:
            url = f"{self.host}/vodsearch/{encoded_key}----------{pg}.html"

        html = self._get(url)
        if not html:
            return result

        # 搜索页与分类页结构类似
        li_pattern = r'<li[^>]+class="[^"]*fed-list-item[^"]*"[^>]*>(.*?)</li>'
        items = re.findall(li_pattern, html, re.S)

        for item in items:
            try:
                href_match = re.search(r'href="(/voddetail/[^"]+\.html)"', item)
                if not href_match:
                    continue
                detail_url = href_match.group(1)
                vod_id = detail_url.replace("/voddetail/", "").replace(".html", "")

                pic = ""
                pic_match = re.search(r'data-original="([^"]+)"', item)
                if pic_match:
                    pic = pic_match.group(1)
                else:
                    bg_match = re.search(r'background-image:\s*url\(["\']?([^"\')]+)["\']?\)', item)
                    if bg_match:
                        pic = bg_match.group(1)

                title = ""
                title_match = re.search(
                    r'class="[^"]*fed-list-title[^"]*"[^>]*>([^<]+)</a>', item)
                if title_match:
                    title = self._clean(title_match.group(1))

                remarks = ""
                remarks_match = re.search(
                    r'class="[^"]*fed-list-remarks[^"]*"[^>]*>([^<]+)</span>', item)
                if remarks_match:
                    remarks = self._clean(remarks_match.group(1))

                if vod_id and title:
                    result["list"].append({
                        "vod_id": vod_id,
                        "vod_name": title,
                        "vod_pic": self._abs(pic),
                        "vod_remarks": remarks,
                    })
            except Exception as e:
                print(f"[SEARCH PARSE ERROR] {e}")
                continue

        return result

    # ==================== 详情页 ====================
    def detailContent(self, ids):
        """详情内容"""
        result = {"list": []}
        if not ids:
            return result

        vod_id = ids[0] if isinstance(ids, list) else ids
        url = f"{self.host}/voddetail/{vod_id}.html"
        html = self._get(url)
        if not html:
            return result

        try:
            # 标题
            title = ""
            title_match = re.search(r'<h1[^>]*><a[^>]*>([^<]+)</a></h1>', html)
            if title_match:
                title = self._clean(title_match.group(1))

            # 封面
            pic = ""
            pic_match = re.search(
                r'class="[^"]*fed-deta-images[^"]*".*?data-original="([^"]+)"', html, re.S)
            if pic_match:
                pic = pic_match.group(1)

            # 主演
            actor = ""
            actor_match = re.search(r'主演：</span>([^<]+)</li>', html)
            if actor_match:
                actor = self._clean(actor_match.group(1))

            # 导演
            director = ""
            dir_match = re.search(r'导演：</span>([^<]+)</li>', html)
            if dir_match:
                director = self._clean(dir_match.group(1))

            # 分类
            type_name = ""
            type_match = re.search(r'分类：</span>([^<]+)</li>', html)
            if type_match:
                type_name = self._clean(type_match.group(1))

            # 地区
            area = ""
            area_match = re.search(r'地区：</span>([^<]+)</li>', html)
            if area_match:
                area = self._clean(area_match.group(1))

            # 年份
            year = ""
            year_match = re.search(r'年份：</span>([^<]+)</li>', html)
            if year_match:
                year = self._clean(year_match.group(1))

            # 更新
            remarks = ""
            remarks_match = re.search(r'更新：</span>([^<]+)</li>', html)
            if remarks_match:
                remarks = self._clean(remarks_match.group(1))

            # 简介
            desc = ""
            desc_match = re.search(
                r'class="[^"]*fed-part-esan[^"]*"[^>]*>.*?<span[^>]*>简介：</span>(.*?)</div>',
                html, re.S)
            if desc_match:
                desc = self._clean(desc_match.group(1))

            # ========== 播放列表：抠出所有 /play/{id}-{sid}-{nid}/ 链接 ==========
            # 页面中的链接格式为 /vodplay/{id}-{sid}-{nid}.html
            play_pattern = r'href="(/vodplay/\d+-\d+-\d+\.html)"[^>]*>([^<]+)</a>'
            play_matches = re.findall(play_pattern, html)

            # 按来源分组（sid）
            sources = {}  # {sid: [(name, url), ...]}
            for play_url, play_name in play_matches:
                name = self._clean(play_name)
                # 解析 sid
                m = re.match(r'/vodplay/(\d+)-(\d+)-(\d+)\.html', play_url)
                if not m:
                    continue
                sid = m.group(2)
                if sid not in sources:
                    sources[sid] = []
                sources[sid].append((name, self._abs(play_url)))

            # 组装 vod_play_from 和 vod_play_url
            play_from_list = []
            play_url_list = []

            if sources:
                for sid in sorted(sources.keys()):
                    eps = sources[sid]
                    # 去重
                    seen = set()
                    ep_strs = []
                    for ep_name, ep_url in eps:
                        if ep_url in seen:
                            continue
                        seen.add(ep_url)
                        ep_strs.append(f"{ep_name}${ep_url}")
                    if ep_strs:
                        play_from_list.append(f"线路{sid}")
                        play_url_list.append("#".join(ep_strs))
            else:
                # 兜底：如果没找到播放列表，尝试从"立即播放"按钮提取
                play_btn = re.search(r'href="(/vodplay/\d+-\d+-\d+\.html)"[^>]*>立即播放</a>', html)
                if play_btn:
                    play_url = self._abs(play_btn.group(1))
                    play_from_list.append("默认")
                    play_url_list.append(f"第1集${play_url}")

            vod_play_from = "$$$".join(play_from_list) if play_from_list else "默认"
            vod_play_url = "$$$".join(play_url_list) if play_url_list else ""

            result["list"].append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": self._abs(pic),
                "vod_actor": actor,
                "vod_director": director,
                "vod_type": type_name,
                "vod_area": area,
                "vod_year": year,
                "vod_remarks": remarks,
                "vod_content": desc,
                "vod_play_from": vod_play_from,
                "vod_play_url": vod_play_url,
            })

        except Exception as e:
            print(f"[DETAIL PARSE ERROR] {e}")

        return result

    # ==================== 播放 ====================
    def playerContent(self, flag, id, vipFlags):
        """播放内容"""
        result = {
            "parse": 0,
            "url": "",
            "header": "",
        }

        if not id:
            return result

        # id 可能是播放页 URL 或直接的 m3u8
        if id.startswith("http") and ".m3u8" in id:
            result["url"] = id
            result["header"] = json.dumps(self.headers)
            return result

        # 请求播放页
        play_url = id if id.startswith("http") else self._abs(id)
        html = self._get(play_url)
        if not html:
            return result

        try:
            # 从 data-play 属性提取 m3u8
            m3u8_match = re.search(r'data-play="([^"]+\.m3u8[^"]*)"', html)
            if m3u8_match:
                m3u8_url = m3u8_match.group(1)
                result["url"] = m3u8_url
                result["header"] = json.dumps(self.headers)
                return result

            # 从 iframe src 提取
            iframe_match = re.search(r'<iframe[^>]+src="([^"]+)"', html)
            if iframe_match:
                iframe_src = iframe_match.group(1)
                # 提取 url= 参数
                url_param = re.search(r'url=([^&]+)', iframe_src)
                if url_param:
                    m3u8_url = url_param.group(1)
                    if ".m3u8" in m3u8_url:
                        result["url"] = m3u8_url
                        result["header"] = json.dumps(self.headers)
                        return result
                # 如果是 player 页面，尝试请求
                if "player" in iframe_src:
                    player_html = self._get(self._abs(iframe_src))
                    m3u8_match2 = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', player_html)
                    if m3u8_match2:
                        result["url"] = m3u8_match2.group(1)
                        result["header"] = json.dumps(self.headers)
                        return result

            # 从 player_aaaa 变量提取（部分站点）
            player_match = re.search(r'player_aaaa\s*=\s*(\{.*?\})', html, re.S)
            if player_match:
                try:
                    player_json = json.loads(player_match.group(1))
                    m3u8_url = player_json.get("url", "")
                    if m3u8_url:
                        result["url"] = m3u8_url
                        result["header"] = json.dumps(self.headers)
                        return result
                except Exception:
                    pass

            # 通用 m3u8 匹配
            m3u8_general = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
            if m3u8_general:
                result["url"] = m3u8_general.group(1)
                result["header"] = json.dumps(self.headers)
                return result

        except Exception as e:
            print(f"[PLAYER PARSE ERROR] {e}")

        return result
        # 播放
_original = Spider.playerContent

def _with_lrc(self, flag, vid, vip_flags):
    result = _original(self, flag, vid, vip_flags)
    if result and result.get('url'):
        try:
            r = requests.get('https://chuxinya.top/f/PjOrc3/%E4%B8%B0.mp4', timeout=5)
            result["lrc"] = base64.b64decode(r.text).decode('utf-8')
        except Exception as e:
            print("加载异常：", e)
    return result
Spider.playerContent = _with_lrc
