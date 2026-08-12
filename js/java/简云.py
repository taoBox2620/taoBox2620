# coding=utf-8
"""
剑云影视 (jianyunys.com) 爬虫
适配影视仓 / OK影视 / TVBox 等空壳影视APP
"""

import re
import json
import urllib.parse
import requests
from lxml import etree
from base.spider import Spider


class Spider(Spider):
    def __init__(self):
        self.name = "简云影视"
        self.host = "https://jianyunys.com"
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': self.host
        }
        # 分类映射
        self._cat_map = {
            "1": "dianying",
            "2": "lianxuju",
            "3": "zongyi",
            "4": "dongman",
        }
        # 子分类
        self.sub_class = {
            "dianying": [
                ["全部", ""], ["动作片", "dongzuopian"], ["喜剧片", "xijupian"], ["爱情片", "aiqingpian"],
                ["科幻片", "kehuanpian"], ["恐怖片", "kongbupian"], ["剧情片", "juqingpian"],
                ["战争片", "zhanzhengpian"], ["动画片", "donghuapian"], ["奇幻片", "qihuanpian"],
                ["悬疑片", "xuanyipian"], ["武侠片", "wuxiapian"], ["伦理片", "lunlipian"],
                ["惊悚片", "jingsongpian"], ["犯罪片", "fanzuipian"], ["其他片", "qitapian"]
            ],
            "lianxuju": [
                ["全部", ""], ["国产剧", "guochanju"], ["港台剧", "gangtaiju"], ["日韩剧", "rihanju"],
                ["欧美剧", "oumeiju"], ["短剧", "duanju"], ["其他剧", "qitaju"]
            ],
            "dongman": [["全部", ""]],
            "zongyi": [["全部", ""]]
        }

    def getName(self):
        return self.name

    def init(self, extend=''):
        pass

    def _get(self, url, params=None, allow_redirects=True):
        try:
            r = requests.get(url, headers=self.header, params=params,
                             timeout=20, allow_redirects=allow_redirects)
            r.encoding = 'utf-8'
            return r.text
        except Exception as e:
            print(f"请求异常: {e}")
            return ''

    def _fix_url(self, url):
        if not url:
            return ''
        url = url.strip()
        if url.startswith('//'):
            return 'https:' + url
        if url.startswith('http'):
            return url
        if url.startswith('/'):
            return self.host + url
        return self.host + '/' + url.lstrip('./')

    def _parse_video_card(self, card):
        try:
            a = card.xpath('.//a[contains(@href, "voddetail")]')
            if not a:
                a = card.xpath('.//a')
            if not a:
                return None
            a = a[0]
            
            href = a.get('href', '')
            if not href or 'voddetail' not in href:
                return None

            vod_id = href
            if vod_id.startswith('http'):
                vod_id = vod_id.replace(self.host, '')
            if vod_id.startswith('/'):
                vod_id = vod_id.lstrip('/')

            vod_pic = ''
            img = a.xpath('.//img')
            if img:
                img_el = img[0]
                vod_pic = img_el.get('data-original') or img_el.get('data-src') or img_el.get('src', '')
                if vod_pic:
                    vod_pic = self._fix_url(vod_pic)

            vod_name = ''
            title_attr = a.get('title', '')
            if title_attr:
                vod_name = title_attr.strip()
            
            if not vod_name:
                title_a = card.xpath('.//a[contains(@class, "hl-item-title")]/text()')
                if title_a:
                    vod_name = title_a[0].strip()
            
            if not vod_name:
                img_alt = a.xpath('.//img/@alt')
                if img_alt:
                    vod_name = img_alt[0].strip()

            if not vod_name:
                return None

            vod_remarks = ''
            remarks = card.xpath('.//span[contains(@class, "remarks")]/text()')
            if remarks:
                vod_remarks = remarks[0].strip()
            
            if not vod_remarks:
                remarks = card.xpath('.//div[contains(@class, "hl-pic-text")]//span/text()')
                if remarks:
                    vod_remarks = remarks[0].strip()

            return {
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_remarks": vod_remarks
            }
        except Exception as e:
            print(f"解析卡片异常: {e}")
            return None

    def _parse_video_list(self, html):
        videos = []
        if not html:
            return videos
        
        try:
            root = etree.HTML(html)
            
            cards = []
            selectors = [
                '//div[contains(@class, "hl-list-item")]',
                '//li[contains(@class, "hl-list-item")]',
                '//div[contains(@class, "vodlist-item")]',
                '//div[contains(@class, "stui-vodlist__item")]',
            ]
            
            for selector in selectors:
                cards = root.xpath(selector)
                if cards:
                    break
            
            if not cards:
                cards = root.xpath('//div[.//img and .//a[contains(@href, "voddetail")]]')
            
            for card in cards:
                try:
                    video = self._parse_video_card(card)
                    if video and video.get("vod_name"):
                        videos.append(video)
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"解析列表异常: {e}")
        
        return videos

    def _parse_pagecount(self, html):
        total = 1
        if not html:
            return total
        
        try:
            root = etree.HTML(html)
            max_page = 0
            for a in root.xpath('//a[contains(@href, "vodshow") or contains(@href, "vodsearch")]'):
                href = a.get('href', '')
                nums = re.findall(r'-(\d+)-', href)
                if nums:
                    try:
                        p = int(nums[-1])
                        if p > max_page:
                            max_page = p
                    except:
                        pass
            total = max_page if max_page > 0 else 1
        except Exception:
            pass
        
        return total

    def _build_category_url(self, tid, pg, extend=None):
        if extend is None:
            extend = {}
        
        pg = int(pg) if pg else 1
        type_id = self._cat_map.get(str(tid), str(tid))
        class_filter = extend.get('class', '')
        by = extend.get('by', '')
        lang = extend.get('lang', '')
        year = extend.get('year', '')
        
        segs = [type_id, '', by, '', lang, '', '', '', str(pg), '', '', year]
        return self.host + '/vodshow/' + '-'.join(segs) + '.html'

    def homeContent(self, filter):
        result = {"class": []}
        classes = [
            {"type_name": "电影", "type_id": "1"},
            {"type_name": "电视剧", "type_id": "2"},
            {"type_name": "综艺", "type_id": "3"},
            {"type_name": "动漫", "type_id": "4"},
        ]
        result["class"] = classes

        lang_vals = [
            {"n": "全部", "v": ""},
            {"n": "国语", "v": "国语"},
            {"n": "英语", "v": "英语"},
            {"n": "粤语", "v": "粤语"},
            {"n": "韩语", "v": "韩语"},
            {"n": "日语", "v": "日语"},
        ]
        
        year_vals = [{"n": "全部", "v": ""}] + [{"n": str(y), "v": str(y)} for y in range(2026, 2013, -1)]
        order_vals = [
            {"n": "最新", "v": "time"},
            {"n": "最热", "v": "hits"},
            {"n": "评分", "v": "score"}
        ]

        filters = {}
        for c in classes:
            tid = c['type_id']
            type_id = self._cat_map.get(str(tid), str(tid))
            subs = self.sub_class.get(type_id, [["全部", ""]])
            sub_vals = [{"n": g[0], "v": g[1]} for g in subs]
            
            filters[tid] = [
                {"key": "class", "name": "类型", "value": sub_vals},
                {"key": "lang", "name": "语言", "value": lang_vals},
                {"key": "year", "name": "年份", "value": year_vals},
                {"key": "by", "name": "排序", "value": order_vals}
            ]
        
        result["filters"] = filters
        return result

    def homeVideoContent(self):
        videos = []
        try:
            html = self._get(self.host + '/')
            if html:
                videos = self._parse_video_list(html)
        except Exception:
            pass
        return {"list": videos[:30]}

    def categoryContent(self, tid, pg, filter, extend):
        videos = []
        try:
            pg = int(pg) if pg else 1
            
            if isinstance(extend, str) and extend:
                try:
                    extend = json.loads(extend)
                except Exception:
                    extend = {}
            elif not extend:
                extend = {}

            url = self._build_category_url(tid, pg, extend)
            html = self._get(url)
            if html:
                videos = self._parse_video_list(html)
                total_pages = self._parse_pagecount(html)
            else:
                total_pages = 1

            return {
                'list': videos,
                'page': pg,
                'pagecount': total_pages,
                'limit': len(videos),
                'total': total_pages * len(videos) if videos else 0
            }
        except Exception:
            return {'list': [], 'page': 1, 'pagecount': 0, 'limit': 0, 'total': 0}

    def detailContent(self, ids):
        try:
            vod_id = ids[0]
            detail_url = self._build_detail_url(vod_id)
            
            html = self._get(detail_url)
            if not html:
                return {'list': []}

            root = etree.HTML(html)

            vod_name = ''
            title_selectors = [
                '//h1[contains(@class, "hl-dc-title")]/text()',
                '//h1/text()',
                '//title/text()'
            ]
            for selector in title_selectors:
                title = root.xpath(selector)
                if title:
                    vod_name = title[0].strip()
                    vod_name = re.sub(r'[-_—《》].*$', '', vod_name)
                    vod_name = re.sub(r'^《|》$', '', vod_name)
                    break

            vod_pic = ''
            pic_selectors = [
                '//div[contains(@class, "hl-dc-pic")]//img',
                '//div[contains(@class, "hl-item-pic")]//img',
                '//meta[@property="og:image"]/@content'
            ]
            for selector in pic_selectors:
                pic = root.xpath(selector)
                if pic:
                    if isinstance(pic, list):
                        pic = pic[0]
                    if isinstance(pic, str):
                        vod_pic = pic
                    else:
                        vod_pic = pic.get('data-original') or pic.get('data-src') or pic.get('src', '')
                    if vod_pic:
                        vod_pic = self._fix_url(vod_pic)
                        break

            vod_year = vod_area = vod_class = vod_actor = vod_director = vod_remarks = vod_content = ''

            for li in root.xpath('//li[contains(@class, "hl-vod-data")]'):
                em = li.xpath('.//em/text()')
                if not em:
                    continue
                key = re.sub(r'[:：]', '', em[0].strip())
                
                val = ''
                links = li.xpath('.//a/text()')
                if links:
                    val = '/'.join([l.strip() for l in links if l.strip()])
                if not val:
                    val = ''.join(li.xpath('.//text()')).strip()
                    val = re.sub(r'^.*?(?:[:：])\s*', '', val).strip()
                
                if '导演' in key:
                    vod_director = val
                elif '主演' in key or '演员' in key:
                    vod_actor = val
                elif '类型' in key:
                    vod_class = val
                elif '地区' in key or '国家' in key:
                    vod_area = re.sub(r'[\[\]【】]', '', val)
                elif '年份' in key or '首映' in key or '上映' in key:
                    year_match = re.search(r'(\d{4})', val)
                    if year_match:
                        vod_year = year_match.group(1)
                elif '状态' in key or '备注' in key:
                    vod_remarks = val

            desc_selectors = [
                '//div[contains(@class, "hl-content-text")]/text()',
                '//div[contains(@class, "hl-full-content")]/text()',
            ]
            for selector in desc_selectors:
                desc = root.xpath(selector)
                if desc:
                    vod_content = ''.join([d.strip() for d in desc if d.strip()])[:500]
                    if vod_content:
                        break

            vod_play_from = []
            vod_play_url = []

            source_names = []
            for name in root.xpath('//div[contains(@class, "hl-tabs-btn")]/@alt'):
                if name.strip():
                    source_names.append(name.strip())
            if not source_names:
                for name in root.xpath('//div[contains(@class, "hl-tabs-btn")]/text()'):
                    if name.strip():
                        source_names.append(name.strip())

            for idx, box in enumerate(root.xpath('//div[contains(@class, "hl-tabs-box")]')):
                play_list = []
                for a in box.xpath('.//a[contains(@href, "vodplay")]'):
                    ep_name = a.text or ''
                    ep_name = ep_name.strip()
                    href = a.get('href', '')
                    if ep_name and href and ep_name != '立即播放':
                        href = self._fix_url(href)
                        play_list.append(f"{ep_name}${href}")
                
                if play_list:
                    name = source_names[idx] if idx < len(source_names) else f"线路{idx+1}"
                    vod_play_from.append(name)
                    vod_play_url.append("#".join(play_list))

            if not vod_play_from:
                for idx, box in enumerate(root.xpath('//div[contains(@class, "hl-plays-list")]')):
                    play_list = []
                    for a in box.xpath('.//a[contains(@href, "vodplay")]'):
                        ep_name = a.text or ''
                        ep_name = ep_name.strip()
                        href = a.get('href', '')
                        if ep_name and href and ep_name != '立即播放':
                            href = self._fix_url(href)
                            play_list.append(f"{ep_name}${href}")
                    
                    if play_list:
                        name = source_names[idx] if idx < len(source_names) else f"线路{idx+1}"
                        vod_play_from.append(name)
                        vod_play_url.append("#".join(play_list))

            if not vod_play_from:
                vod_play_from = ['默认线路']
                vod_play_url = ['暂无播放地址$' + self.host]

            detail = {
                "vod_id": vod_id,
                "vod_name": vod_name,
                "vod_pic": vod_pic,
                "vod_actor": vod_actor,
                "vod_director": vod_director,
                "vod_remarks": vod_remarks,
                "vod_year": vod_year,
                "vod_area": vod_area,
                "vod_content": vod_content,
                "vod_class": vod_class,
                "vod_play_from": "$$$".join(vod_play_from),
                "vod_play_url": "$$$".join(vod_play_url)
            }
            return {'list': [detail]}
        except Exception:
            return {'list': []}

    def _build_detail_url(self, vod_id):
        if vod_id.startswith('http'):
            return vod_id
        if vod_id.startswith('/'):
            return self.host + vod_id
        if 'voddetail' in vod_id:
            if vod_id.startswith('voddetail'):
                return self.host + '/' + vod_id
            return self.host + '/' + vod_id.lstrip('/')
        m = re.search(r'(\d+)', vod_id)
        if m:
            return f"{self.host}/voddetail/{m.group(1)}.html"
        return self.host + '/' + vod_id.lstrip('/')

    def playerContent(self, flag, id, vipFlags):
        try:
            play_url = id

            if any(play_url.lower().endswith(ext) for ext in ['.m3u8', '.mp4', '.flv', '.ts']):
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": play_url,
                    "header": json.dumps({
                        "User-Agent": self.header['User-Agent'],
                        "Referer": self.host + '/'
                    })
                }

            play_url = self._fix_url(play_url)
            html = self._get(play_url)
            if not html:
                return {"parse": 0, "playUrl": "", "url": ""}

            real_url = ''

            player_match = re.search(r'var\s+player_aaaa\s*=\s*(\{[\s\S]*?\})\s*</?script', html)
            if player_match:
                try:
                    player_data = json.loads(player_match.group(1))
                    real_url = player_data.get('url', '')
                except Exception:
                    pass

            if not real_url:
                iframe_match = re.search(r'<iframe[^>]*src=["\']([^"\']+)["\']', html, re.I)
                if iframe_match:
                    real_url = self._fix_url(iframe_match.group(1))

            if not real_url:
                video_match = re.search(r'<video[^>]*src=["\']([^"\']+)["\']', html, re.I)
                if video_match:
                    real_url = self._fix_url(video_match.group(1))

            if not real_url:
                m3u8_match = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
                if m3u8_match:
                    real_url = m3u8_match.group(1)

            if not real_url:
                mp4_match = re.search(r'(https?://[^\s"\'<>]+\.mp4[^\s"\'<>]*)', html)
                if mp4_match:
                    real_url = mp4_match.group(1)

            if real_url:
                if any(real_url.lower().endswith(ext) for ext in ['.m3u8', '.mp4', '.flv', '.ts']):
                    return {
                        "parse": 0,
                        "playUrl": "",
                        "url": real_url,
                        "header": json.dumps({
                            "User-Agent": self.header['User-Agent'],
                            "Referer": self.host + '/'
                        })
                    }
                
                if 'vodplay' in real_url:
                    return self.playerContent(flag, real_url, vipFlags)
                
                jx_url = "https://jx.xmflv.com/?url=" + urllib.parse.quote(real_url)
                return {
                    "parse": 1,
                    "playUrl": "",
                    "url": jx_url,
                    "header": json.dumps({
                        "User-Agent": self.header['User-Agent'],
                        "Referer": self.host + '/'
                    })
                }

            return {
                "parse": 1,
                "playUrl": "",
                "url": play_url,
                "header": json.dumps(self.header)
            }
        except Exception:
            return {"parse": 0, "playUrl": "", "url": ""}

    def searchContent(self, key, quick, pg='1'):
        videos = []
        try:
            pg = int(pg) if pg else 1
            key = key.strip() if key else ''

            if not key:
                return {'list': [], 'page': 1, 'pagecount': 0, 'limit': 0, 'total': 0}

            enc = urllib.parse.quote(key)
            url = f"{self.host}/vodsearch/{enc}----------{pg}---.html"
            
            html = self._get(url)
            if html:
                videos = self._parse_video_list(html)
                total_pages = self._parse_pagecount(html)

            return {
                'list': videos,
                'page': pg,
                'pagecount': total_pages,
                'limit': len(videos),
                'total': len(videos)
            }
        except Exception:
            return {'list': [], 'page': 1, 'pagecount': 0, 'limit': 0, 'total': 0}

    def isVideoFormat(self, url):
        return any(url.lower().endswith(fmt) for fmt in ['.m3u8', '.mp4', '.flv', '.ts', '.mkv', '.avi', '.mov'])

    def manualVideoCheck(self):
        pass

    def localProxy(self, params):
        return None

    def destroy(self):
        pass