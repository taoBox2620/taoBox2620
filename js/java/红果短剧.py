# -*- coding: utf-8 -*-
import re
import sys
import json
from pyquery import PyQuery as pq

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def init(self, extend=""): pass
        def getName(self): pass
        def fetch(self, url, headers=None, timeout=None): pass

class Spider(Spider):

    def init(self, extend=""):
        pass

    def getName(self):
        return "红果果"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    host = 'https://www.hongguoguo.tv'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': host + '/',
        'Origin': host
    }

    def homeContent(self, filter):
        result = {}
        classes = []
        try:
            res = self.fetch(self.host, headers=self.headers)
            text = res.text
            vlist = self.get_vod_list(text)
            
            d = pq(text)
            seen_ids = set()
            for a in d('a').items():
                href = a.attr('href')
                if not href or '/vod/type/id/' not in href: continue
                name = a.text().strip()
                if not name: name = a.find('span').text().strip()
                if not name or len(name) > 6 or '更多' in name: continue

                match = re.search(r'id/(.*?)\.html', href)
                if match:
                    tid = match.group(1)
                    if tid not in seen_ids:
                        classes.append({'type_name': name, 'type_id': tid})
                        seen_ids.add(tid)
            
        except Exception:
            vlist = []
        
        if not classes:
            classes = [
                {'type_name': '精选短剧', 'type_id': 'jingxuanduanju'},
                {'type_name': '穿越短剧', 'type_id': 'chuanyueduanju'},
                {'type_name': '古装短剧', 'type_id': 'guzhuangduanju'},
                {'type_name': '逆袭短剧', 'type_id': 'nixiduanju'},
                {'type_name': '都市短剧', 'type_id': 'dushiduanju'},
            ]

        result['class'] = classes
        result['list'] = vlist
        return result

    def homeVideoContent(self):
        pass

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        if pg == '1':
            url = '{}/vod/type/id/{}.html'.format(self.host, tid)
        else:
            url = '{}/vod/type/id/{}/page/{}.html'.format(self.host, tid, pg)
            
        try:
            res = self.fetch(url, headers=self.headers)
            vlist = self.get_vod_list(res.text)
            result['list'] = vlist
            result['page'] = pg
            result['pagecount'] = 9999
            result['limit'] = 40
            result['total'] = 999999
        except Exception:
            result['list'] = []
            
        return result

    def detailContent(self, ids):
        did = ids[0]
        url = did if did.startswith('http') else '{}{}'.format(self.host, did)
        if '/vod/' not in url:
             url = '{}/vod/detail/id/{}.html'.format(self.host, did)

        res = self.fetch(url, headers=self.headers)
        html = res.text
        data = pq(html)
        
        title = ''
        try:
            js_name_match = re.search(r'vod_name[\'"]?\s*:\s*[\'"](.*?)[\'"]', html)
            if js_name_match:
                raw_title = js_name_match.group(1)
                if '\\u' in raw_title:
                    title = raw_title.encode('utf-8').decode('unicode_escape')
                else:
                    title = raw_title
        except:
            pass

        if not title:
            og_title = data('meta[property="og:title"]').attr('content')
            if og_title:
                title = re.sub(r'(《|》|全集|免费|观看|在线|高清|完整版|_)','', og_title).strip()

        if not title:
            t = data('.tim-title-h1').text() or data('h1').text()
            if t:
                t = re.sub(r'^\d{4}-', '', t)
                t = t.split('_')[0].split('-')[0]
                title = t.strip()

        if not title: title = '未知片名'
        
        pic = ''
        pic_container = data('.lazy').eq(0) or data('.detail-pic').eq(0) or data('.poster').eq(0)
        
        if pic_container:
            pic = pic_container.attr('data-original')
            if not pic:
                style = pic_container.attr('style') or ''
                m = re.search(r'url\([\'"]?(.*?)[\'"]?\)', style)
                if m: pic = m.group(1)
            if not pic:
                pic = pic_container.find('img').attr('src')

        if pic and not pic.startswith('http'):
            pic = self.host + pic

        vod = {
            'vod_name': title,
            'vod_pic': pic or '',
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': '',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': '',
        }

        for p in data('.play-detail p').items():
            txt = p.text().strip()
            if '导演' in txt:
                vod['vod_director'] = txt.replace('导演：', '').replace('导演:', '').strip()
            elif '主演' in txt:
                vod['vod_actor'] = txt.replace('主演：', '').replace('主演:', '').strip()
            elif '年份' in txt:
                m_year = re.search(r'年份[：:]\s*(\d{4})', txt)
                if m_year: vod['vod_year'] = m_year.group(1)
                m_area = re.search(r'地区[：:]\s*([\w\u4e00-\u9fa5]+)', txt)
                if m_area: vod['vod_area'] = m_area.group(1)
            elif '简介' in txt:
                vod['vod_content'] = txt.replace('简介：', '').replace('简介:', '').strip()
        
        if not vod['vod_content']:
            blurb = data('.Blurb').text()
            if blurb and len(blurb) > 10:
                vod['vod_content'] = blurb.strip()

        if not vod['vod_content']:
            meta_desc = data('meta[property="og:description"]').attr('content') or data('meta[name="description"]').attr('content')
            if meta_desc:
                clean_desc = meta_desc
                if '2025' in clean_desc: clean_desc = clean_desc.split('2025')[0]
                if '红果果' in clean_desc: clean_desc = clean_desc.split('红果果')[0]
                if len(clean_desc) > 10: vod['vod_content'] = clean_desc.strip()

        if not vod['vod_content']: vod['vod_content'] = '暂无简介'

        play_from = []
        play_url = []
        
        tabs = []
        swiper_wrapper = data('.anthology .swiper-wrapper')
        if swiper_wrapper:
            for slide in swiper_wrapper.find('.swiper-slide').items():
                t = slide.attr('aria-label') or slide.text()
                if '/' in t: t = t.split('/')[-1]
                tabs.append(t.strip())
        
        if not tabs:
            tabs_container = data('.module-tab-content, .play_source_tab, .nav-tabs')
            if tabs_container:
                tabs = [i.text().strip() for i in tabs_container('a, span, div').items() if i.text().strip()]
        
        if not tabs: tabs = ['默认线路']

        lists = []
        anthology_list = data('.anthology-list')
        if anthology_list:
            for ul in anthology_list.children('ul').items():
                lists.append(ul)
        
        if not lists:
            lists = [i for i in data('.module-play-list, .play_list_box, #playlist').items()]

        if len(lists) > len(tabs):
             tabs = ['线路{}'.format(i+1) for i in range(len(lists))]

        for idx, plist_container in enumerate(lists):
            from_name = tabs[idx] if idx < len(tabs) else '线路{}'.format(idx+1)
            play_from.append(from_name)
            
            urls = []
            for a in plist_container('a').items():
                name = a.text().strip()
                link = a.attr('href')
                if not link or '/vod/' not in link: continue
                
                if not name: name = a.attr('title') 
                if not name: name = '第{}集'.format(len(urls)+1)
                
                name = name.replace('', '')
                
                urls.append('{}${}'.format(name, link))
            
            if urls:
                play_url.append('#'.join(urls))

        vod['vod_play_from'] = '$$$'.join(play_from)
        vod['vod_play_url'] = '$$$'.join(play_url)
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        url = '{}/vod/search/page/{}/wd/{}.html'.format(self.host, pg, key)
        res = self.fetch(url, headers=self.headers)
        return {'list': self.get_vod_list(res.text), 'page': pg}

    def playerContent(self, flag, id, vipFlags):
        url = id
        if not url.startswith('http'):
            url = self.host + url
            
        res = self.fetch(url, headers=self.headers)
        html = res.text
        
        try:
            match = re.search(r'player_aaaa\s*=\s*({.*?});', html)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                play_url = data.get('url')
                if play_url and 'hongguoguo.tv' not in play_url:
                    return {'parse': 0, 'playUrl': '', 'url': play_url, 'header': self.headers}
        except Exception:
            pass
            
        try:
            match = re.search(r'"url"\s*:\s*"([^"]+)"', html)
            if match:
                raw_url = match.group(1)
                play_url = raw_url.replace('\\/', '/')
                if play_url.startswith('http') and 'hongguoguo.tv' not in play_url:
                     return {'parse': 0, 'playUrl': '', 'url': play_url, 'header': self.headers}
        except Exception:
            pass
        
        d = pq(html)
        iframe_src = d('iframe').attr('src')
        if iframe_src:
            return {'parse': 1, 'url': iframe_src, 'header': self.headers}

        return  {'parse': 1, 'url': url, 'header': self.headers}

    def localProxy(self, param):
        pass

    def get_vod_list(self, html):
        vlist = []
        seen = set()
        d = pq(html)
        
        items = d('.l-list-box, .module-item, .public-list-box')
        
        for item in items.items():
            link_tag = item.find('a').eq(0)
            href = link_tag.attr('href')
            
            if not href or '/vod/' not in href: continue
            
            name = link_tag.attr('title') 
            if not name: 
                name = item.find('h2').text() or item.find('.tim-title').text()
            if not name: name = link_tag.text().strip()
            
            if not name or len(name) > 50 or '立即观看' in name: continue
            
            pic = ''
            lazy = item.find('.lazy')
            if lazy:
                pic = lazy.attr('data-original')
                if not pic:
                    style = lazy.attr('style') or ''
                    m = re.search(r'url\([\'"]?(.*?)[\'"]?\)', style)
                    if m: pic = m.group(1)
            
            if not pic:
                pic = item.find('img').attr('data-src') or item.find('img').attr('src')

            if pic and not pic.startswith('http'):
                pic = self.host + pic
            
            if not pic:
                pic = "https://github.com/tv-player/logo/raw/main/default.png"
            
            if href not in seen:
                vlist.append({
                    'vod_id': href,
                    'vod_name': name,
                    'vod_pic': pic,
                    'vod_remarks': item.find('.tim-tag').text() or ''
                })
                seen.add(href)

        return vlist