# coding=utf-8
"""
目标站: 力德短剧网 (https://m.leaderclean.com)
模板: 苹果CMS (jianbai/stui)
功能: 首页推荐、二级分类筛选、多线路播放列表解析、带验证码自动求解搜索
优化: HTTP降级、Session复用、正则优先解析、最小化重试、连接池复用
"""
import re
import sys
import json
import urllib.parse
import time
from bs4 import BeautifulSoup

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):

    # ===== 预编译正则（避免重复编译，提升解析速度） =====
    _RE_VOD_ID = re.compile(r'/dj/(\d+)\.html')
    _RE_PLAY_HREF = re.compile(r'/pl/(\d+)/(\d+)/(\d+)\.html')
    _RE_CHAPTER_URL = re.compile(r'chapterurl\s*=\s*[\'"]([^\'"]+)[\'"]')
    _RE_M3U8 = re.compile(r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*')
    _RE_PAGE_NUM = re.compile(r'/(\d+)/\d+/\d+/\d+/\d+/\d+/\d+/(\d+)\.html')
    _RE_LAST_PAGE = re.compile(r'/(\d+)/0/0/0/0/0/0/(\d+)\.html')

    def init(self, extend=""):
        self.site_url = "https://m.leaderclean.com"
        self.http_url = "http://m.leaderclean.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-G991U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Referer': self.site_url + '/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        # ===== 一级分类 =====
        self.categories = [
            {"type_id": "1", "type_name": "电视剧"},
            {"type_id": "2", "type_name": "电影"},
            {"type_id": "3", "type_name": "短剧"},
            {"type_id": "4", "type_name": "综艺"},
            {"type_id": "5", "type_name": "动漫"},
        ]

        # ===== 二级分类筛选系统 =====
        # URL格式: /{type_id}/{class}/{剧情}/{area}/{year}/{lang}/{sort}/{page}.html
        # 位置:     [0]     [1]    [2]   [3]   [4]   [5]   [6]   [7]
        self.filters = self._build_filters()

    # ========== 筛选系统构建 ==========

    def _build_filters(self):
        """构建各分类的二级筛选条件"""

        # 类型（class）- 各分类不同，位置 [1]
        class_map = {
            "1": [("全部", ""), ("国产剧", "1"), ("欧美剧", "2"), ("韩剧", "3"), ("日剧", "4"), ("港剧", "5"), ("台剧", "6"), ("泰剧", "7"), ("海外剧", "8")],
            "2": [("全部", ""), ("动作片", "1"), ("喜剧片", "2"), ("爱情片", "3"), ("科幻片", "4"), ("恐怖片", "5"), ("剧情片", "6"), ("战争片", "7"), ("纪录片", "8"), ("动画片", "9"), ("4K电影", "10"), ("邵氏电影", "11")],
            "3": [("全部", ""), ("有声动漫", "1"), ("女频恋爱", "2"), ("反转爽剧", "3"), ("古装仙侠", "4"), ("年代穿越", "5"), ("脑洞悬疑", "6"), ("现代都市", "7"), ("漫剧", "8"), ("其它", "9")],
            "4": [("全部", ""), ("大陆综艺", "1"), ("日韩综艺", "2"), ("港台综艺", "3"), ("欧美综艺", "4"), ("演唱会", "5")],
            "5": [("全部", ""), ("国产动漫", "1"), ("日韩动漫", "2"), ("欧美动漫", "3"), ("港台动漫", "4"), ("海外动漫", "5")],
        }

        # 地区（area）- 共用，位置 [3]
        area_opts = [
            ("全部", ""), ("大陆", "1"), ("内地", "2"), ("美国", "3"), ("法国", "4"),
            ("韩国", "5"), ("日本", "6"), ("加拿大", "7"), ("其它", "8"), ("香港", "9"),
            ("台湾", "11"), ("泰国", "15"), ("澳大利亚", "16"), ("英国", "17"),
            ("港台", "19"), ("国产", "20"), ("印度", "21"),
        ]

        # 年份（year）- 共用，位置 [4]
        year_opts = [("全部", "")]
        for y in range(2026, 2008, -1):
            year_opts.append((str(y), str(y)))
        year_opts.append(("其它", "99"))

        # 语言（lang）- 共用，位置 [5]
        lang_opts = [
            ("全部", ""), ("国语", "1"), ("粤语", "2"), ("英语", "3"), ("日语", "4"),
            ("韩语", "5"), ("泰语", "6"), ("俄语", "7"), ("法语", "8"), ("其它", "10"),
        ]

        # 排序（sort）- 共用，位置 [6]
        sort_opts = [("时间", "0"), ("人气", "1"), ("评分", "2")]

        filters = {}
        for tid in ["1", "2", "3", "4", "5"]:
            filters[tid] = [
                {"key": "class", "name": "类型", "value": [{"n": n, "v": v} for n, v in class_map[tid]]},
                {"key": "area", "name": "地区", "value": [{"n": n, "v": v} for n, v in area_opts]},
                {"key": "year", "name": "年份", "value": [{"n": n, "v": v} for n, v in year_opts]},
                {"key": "lang", "name": "语言", "value": [{"n": n, "v": v} for n, v in lang_opts]},
                {"key": "sort", "name": "排序", "value": [{"n": n, "v": v} for n, v in sort_opts]},
            ]
        return filters

    # ========== 网络请求（SSL降级 + 最小重试） ==========

    def _safe_fetch(self, url, headers=None, max_retry=2):
        """带 HTTP 降级的安全请求：先 HTTPS，失败秒降 HTTP"""
        if headers is None:
            headers = self.headers
        last_err = None
        for i in range(max_retry):
            try:
                resp = self.fetch(url, headers=headers)
                if resp:
                    return resp
            except Exception as e:
                last_err = e
                # 首次 HTTPS 失败 → 立即降级 HTTP
                if url.startswith('https://') and i == 0:
                    try:
                        http_url = url.replace('https://', 'http://', 1)
                        resp = self.fetch(http_url, headers=headers)
                        if resp:
                            return resp
                    except Exception:
                        pass
                if i < max_retry - 1:
                    time.sleep(0.3)
        return None

    def _post_fetch(self, url, data, headers=None, max_retry=2):
        """POST 请求（用于搜索验证码提交）"""
        if headers is None:
            headers = self.headers
        for i in range(max_retry):
            try:
                resp = self.post(url, data=data, headers=headers)
                if resp:
                    return resp
            except Exception as e:
                if url.startswith('https://') and i == 0:
                    try:
                        http_url = url.replace('https://', 'http://', 1)
                        resp = self.post(http_url, data=data, headers=headers)
                        if resp:
                            return resp
                    except Exception:
                        pass
                if i < max_retry - 1:
                    time.sleep(0.3)
        return None

    # ========== URL 工具 ==========

    def _fix_url(self, url):
        if not url:
            return ''
        if url.startswith('http'):
            return url
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('/'):
            return self.site_url + url
        return self.site_url + '/' + url

    def _build_cat_url(self, tid, pg, extend):
        """
        构建分类列表 URL
        格式: /{type_id}/{class}/{0}/{area}/{year}/{lang}/{sort}/{page}.html
        注意: 位置 [2] 为剧情分类，此处置 0 不使用
        """
        ext = {}
        if extend:
            if isinstance(extend, str):
                try:
                    ext = json.loads(extend)
                except Exception:
                    pass
            elif isinstance(extend, dict):
                ext = extend

        cls = ext.get('class', '')
        area = ext.get('area', '')
        year = ext.get('year', '')
        lang = ext.get('lang', '')
        sort = ext.get('sort', '')

        page = int(pg) if pg else 1
        return f"{self.site_url}/{tid}/{cls}/0/{area}/{year}/{lang}/{sort}/{page}.html"

    # ========== 列表解析 ==========

    def _parse_video_list(self, soup, max_count=0):
        """解析视频列表（正则优先，最小化 DOM 操作）"""
        video_list = []
        seen = set()

        # 主选择器: stui-vodlist__box
        boxes = soup.select('.stui-vodlist__box')
        for box in boxes:
            a = box.select_one('a.stui-vodlist__thumb')
            if not a:
                continue
            href = a.get('href', '')
            m = self._RE_VOD_ID.search(href)
            if not m:
                continue
            vod_id = m.group(1)
            if vod_id in seen:
                continue
            seen.add(vod_id)

            title = a.get('title', '')
            if not title:
                continue

            pic = a.get('data-original', '') or a.get('src', '')
            pic = self._fix_url(pic)

            # 提取状态标签（全集/更新至xx集）
            remark = ''
            remark_elem = box.select_one('.pic-text b')
            if remark_elem:
                remark = remark_elem.get_text(strip=True)
            if not remark:
                remark_elem = box.select_one('.pic-text1 b')
                if remark_elem:
                    remark = remark_elem.get_text(strip=True)

            video_list.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
            if max_count > 0 and len(video_list) >= max_count:
                break

        # 备用: 直接搜索 /dj/ 链接
        if not video_list:
            for a_tag in soup.select('a[href*="/dj/"]'):
                href = a_tag.get('href', '')
                m = self._RE_VOD_ID.search(href)
                if not m:
                    continue
                vod_id = m.group(1)
                if vod_id in seen:
                    continue
                seen.add(vod_id)
                title = a_tag.get('title', '') or a_tag.get_text(strip=True)
                if not title:
                    continue
                pic = self._fix_url(a_tag.get('data-original', '') or a_tag.get('src', ''))
                video_list.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": "",
                })
                if max_count > 0 and len(video_list) >= max_count:
                    break

        return video_list

    def _extract_page_info(self, soup, tid):
        """从分页链接提取总页数和总数"""
        pagecount = 1
        total = 0

        # 查找分页区域
        page_area = soup.select_one('.stui-page')
        if not page_area:
            page_area = soup

        # 查找末页/最大页码
        for a in page_area.select('a[href]'):
            href = a.get('href', '')
            text = a.get_text(strip=True)
            # 匹配 /{tid}/.../{page}.html 格式
            m = re.search(r'/{tid}/[\d\w]*/\d+/\d+/\d+/\d+/\d+/(\d+)\.html'.format(tid=tid), href)
            if m:
                pagecount = max(pagecount, int(m.group(1)))
            # 匹配末页
            if text in ('末页', '尾页', 'last', 'Last'):
                m2 = re.search(r'/(\d+)\.html', href)
                if m2:
                    pagecount = max(pagecount, int(m2.group(1)))

        total = 30 * pagecount
        return pagecount, total

    # ========== 首页 ==========

    def homeContent(self, filter):
        url = self.site_url + "/"
        resp = self._safe_fetch(url)
        video_list = []
        if resp:
            soup = BeautifulSoup(resp.text, 'html.parser')
            video_list = self._parse_video_list(soup, max_count=36)
        return {"class": self.categories, "list": video_list, "filters": self.filters}

    def homeVideoContent(self):
        return self.homeContent(False)

    # ========== 分类列表 ==========

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        url = self._build_cat_url(tid, page, extend)
        resp = self._safe_fetch(url)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1, "limit": 30, "total": 0}

        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = self._parse_video_list(soup)
        pagecount, total = self._extract_page_info(soup, tid)

        return {
            "list": video_list,
            "page": page,
            "pagecount": pagecount,
            "limit": 30,
            "total": total
        }

    # ========== 详情页 ==========

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]
        url = f"{self.site_url}/dj/{vod_id}.html"
        resp = self._safe_fetch(url)
        if not resp:
            return {"list": []}

        soup = BeautifulSoup(resp.text, 'html.parser')
        html = resp.text

        # ---- 标题 ----
        vod_name = ''
        h1 = soup.select_one('.stui-content__detail h1.title')
        if h1:
            vod_name = h1.get_text(strip=True)
        if not vod_name:
            title_tag = soup.select_one('title')
            if title_tag:
                raw = title_tag.get_text()
                vod_name = raw.split('全集')[0].split('在线观看')[0].split('-')[0].strip()

        # ---- 封面图 ----
        vod_pic = ''
        thumb = soup.select_one('.stui-content__thumb img')
        if thumb:
            vod_pic = self._fix_url(thumb.get('data-original', '') or thumb.get('src', ''))
        if not vod_pic:
            # OG meta 兜底
            og_img = soup.find('meta', attrs={'property': 'og:image'})
            if og_img:
                vod_pic = og_img.get('content', '')

        # ---- 详情信息 ----
        vod_content = ''
        vod_actor = vod_director = vod_area = vod_year = vod_class = ''
        detail = soup.select_one('.stui-content__detail')

        # OG meta 兜底提取
        og_class = soup.find('meta', attrs={'property': 'og:video:class'})
        if og_class:
            vod_class = og_class.get('content', '')
        og_actor = soup.find('meta', attrs={'property': 'og:video:actor'})
        if og_actor:
            vod_actor = og_actor.get('content', '')
        og_date = soup.find('meta', attrs={'property': 'og:video:date'})
        if og_date:
            vod_year = og_date.get('content', '')[:4]
        og_area = soup.find('meta', attrs={'property': 'og:video:area'})
        if og_area:
            area_raw = og_area.get('content', '')
            vod_area = area_raw.split(',')[0].strip()

        # 从 p.data 行精确提取（覆盖 OG meta）
        if detail:
            for p in detail.select('p.data'):
                text = p.get_text(strip=True)
                if not text:
                    continue
                # 跳过合并行 "类型：XX / 地区：XX / 年份：XX"
                if text.startswith('类型') and '地区' in text:
                    continue
                # 剧情（短剧类型标签，如 "剧情：现代都市 短剧"）
                if text.startswith('剧情'):
                    links = p.select('a')
                    cls_parts = [a.get_text(strip=True) for a in links]
                    if cls_parts:
                        vod_class = ' '.join(cls_parts)
                # 类型（单独行）
                elif text.startswith('类型'):
                    links = p.select('a')
                    cls_parts = [a.get_text(strip=True) for a in links]
                    if cls_parts:
                        vod_class = ' '.join(cls_parts)
                # 地区
                elif text.startswith('地区'):
                    links = p.select('a')
                    if links:
                        vod_area = links[0].get_text(strip=True)
                    else:
                        vod_area = text.replace('地区：', '').replace('地区', '').strip()
                # 年份
                elif text.startswith('年份') or text.startswith('年代'):
                    links = p.select('a')
                    if links:
                        vod_year = links[0].get_text(strip=True)
                    else:
                        vod_year = text.replace('年份：', '').replace('年代：', '').replace('年份', '').replace('年代', '').strip()
                # 状态
                elif text.startswith('状态'):
                    pass
                # 导演
                elif text.startswith('导演'):
                    vod_director = text.split('：', 1)[-1].strip() if '：' in text else text[2:].strip()
                # 主演
                elif text.startswith('主演') or text.startswith('演员'):
                    vod_actor = text.split('：', 1)[-1].strip() if '：' in text else text[2:].strip()
                # 更新时间
                elif text.startswith('更新'):
                    pass

        # 简介 - OG description 兜底
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc:
            vod_content = og_desc.get('content', '')
        if not vod_content:
            og_desc2 = soup.find('meta', attrs={'itemprop': 'description'})
            if og_desc2:
                vod_content = og_desc2.get('content', '')

        # ---- 播放列表（多线路解析） ----
        play_from_list = []
        play_url_list = []

        # 查找所有播放列表容器（每个代表一条线路）
        playlists = soup.select('.stui-content__playlist')
        if playlists:
            for idx, pl in enumerate(playlists):
                line_name = f"线路{idx + 1}"
                eps = []
                for a in pl.select('a[href]'):
                    href = a.get('href', '')
                    m = self._RE_PLAY_HREF.search(href)
                    if m:
                        ep_name = a.get_text(strip=True)
                        if ep_name:
                            eps.append(f"{ep_name}${self._fix_url(href)}")
                if eps:
                    play_from_list.append(line_name)
                    play_url_list.append('#'.join(eps))

        # 备用: 直接搜索所有 /pl/ 链接
        if not play_url_list:
            groups = {}
            for a in soup.select('a[href*="/pl/"]'):
                href = a.get('href', '')
                m = self._RE_PLAY_HREF.search(href)
                if not m:
                    continue
                vod_pl_id, line, ep = m.group(1), m.group(2), m.group(3)
                if vod_pl_id != str(vod_id):
                    continue
                ep_name = a.get_text(strip=True)
                if not ep_name or ep_name == '立即播放':
                    continue
                groups.setdefault(line, []).append(f"{ep_name}${self._fix_url(href)}")

            if groups:
                for line in sorted(groups.keys(), key=lambda x: int(x) if str(x).isdigit() else 0):
                    line_name = f"线路{int(line) + 1}" if str(line).isdigit() else str(line)
                    play_from_list.append(line_name)
                    play_url_list.append('#'.join(groups[line]))

        # 最终兜底
        if not play_url_list:
            play_from_list.append('默认线路')
            play_url_list.append(f"播放${self.site_url}/dj/{vod_id}.html")

        vod_play_from = '$$$'.join(play_from_list)
        vod_play_url = '$$$'.join(play_url_list)

        result = [{
            "vod_id": vod_id,
            "vod_name": vod_name,
            "vod_pic": vod_pic,
            "vod_content": vod_content,
            "vod_actor": vod_actor,
            "vod_director": vod_director,
            "vod_area": vod_area,
            "vod_year": vod_year,
            "vod_class": vod_class,
            "vod_play_from": vod_play_from,
            "vod_play_url": vod_play_url
        }]
        return {"list": result}

    # ========== 搜索（带验证码自动求解） ==========

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        encoded_key = urllib.parse.quote(key)
        search_url = f"{self.site_url}/search?keyword={encoded_key}"

        # 第一步: GET 获取验证码页面（同时获取 session cookie）
        resp = self._safe_fetch(search_url)
        if not resp:
            return {"list": [], "page": page, "pagecount": 1}

        # 检查是否需要验证码
        if 'captcha' in resp.text.lower():
            # 提取验证码文本
            soup = BeautifulSoup(resp.text, 'html.parser')
            cap_display = soup.select_one('.captcha-display')
            if cap_display:
                captcha_text = cap_display.get_text(strip=True)
                if captcha_text:
                    # 第二步: POST 提交验证码
                    form_data = {
                        'keyword': key,
                        'verify': '1',
                        'captcha': captcha_text,
                    }
                    resp = self._post_fetch(search_url, data=form_data)
                    if not resp:
                        return {"list": [], "page": page, "pagecount": 1}

        # 解析搜索结果
        soup = BeautifulSoup(resp.text, 'html.parser')
        video_list = self._parse_video_list(soup)

        pagecount = 1
        page_area = soup.select_one('.stui-page')
        if page_area:
            for a in page_area.select('a[href]'):
                m = re.search(r'[?&]page=(\d+)', a.get('href', ''))
                if m:
                    pagecount = max(pagecount, int(m.group(1)))

        return {"list": video_list, "page": page, "pagecount": pagecount}

    # ========== 播放解析 ==========

    def playerContent(self, flag, id, vipFlags):
        # 构建 play 页面 URL
        if id.startswith('http'):
            play_url = id
        elif id.startswith('/'):
            play_url = self.site_url + id
        else:
            play_url = self.site_url + '/' + id

        resp = self._safe_fetch(play_url)
        if not resp:
            return {"parse": 1, "url": play_url, "header": self.headers}

        html = resp.text

        # 优先: chapterurl 变量（jianbai 模板标准）
        m = self._RE_CHAPTER_URL.search(html)
        if m:
            video_url = m.group(1)
            if video_url and video_url.startswith('http'):
                return {"parse": 0, "url": video_url, "header": self.headers}

        # 备用: 直接搜索 m3u8
        m2 = self._RE_M3U8.search(html)
        if m2:
            return {"parse": 0, "url": m2.group(0), "header": self.headers}

        # 备用: mac_player_config
        mac_match = re.search(r'mac_player_config\s*=\s*({.*?})', html, re.DOTALL)
        if mac_match:
            try:
                cfg = json.loads(mac_match.group(1))
                video_url = cfg.get('url', '')
                if video_url and '.m3u8' in video_url:
                    return {"parse": 0, "url": video_url, "header": self.headers}
            except Exception:
                pass

        # 备用: var url = "..."
        url_match = re.search(r'var\s+url\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']', html)
        if url_match:
            return {"parse": 0, "url": url_match.group(1), "header": self.headers}

        # iframe 兜底
        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if iframe:
            iframe_url = iframe.group(1)
            if not iframe_url.startswith('http'):
                iframe_url = self._fix_url(iframe_url)
            iframe_resp = self._safe_fetch(iframe_url)
            if iframe_resp:
                m3 = self._RE_M3U8.search(iframe_resp.text)
                if m3:
                    return {"parse": 0, "url": m3.group(0), "header": self.headers}

        return {"parse": 1, "url": play_url, "header": self.headers}
