# coding = utf-8
#!/usr/bin/python
import re
import sys
import json
import requests
import html
from base.spider import Spider

sys.path.append('..')

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except:
    pass

class Spider(Spider):
    def __init__(self):
        self.name = "顶级影院"
        self.host = "https://www.dj191.com"
        self.header = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
            "Referer": "https://www.dj191.com/"
        }
        
        self.xxx_keywords = [
            '成人', '三级', '福利', '伦理', '激情', '诱惑', '无删减', '未删减', 
            '18禁', '爆乳', '邪恶', '夜夜', '偷拍', '写真', '情色'
        ]

    def getName(self):
        return self.name

    def init(self, extend=''):
        pass

    def homeContent(self, filter):
        result = {}
        classes = [
            {"type_name": "电影", "type_id": "1"},
            {"type_name": "电视剧", "type_id": "2"},
            {"type_name": "综艺", "type_id": "3"},
            {"type_name": "动漫", "type_id": "4"},
            {"type_name": "短剧", "type_id": "29"},
            {"type_name": "动作片", "type_id": "6"},
            {"type_name": "喜剧片", "type_id": "7"},
            {"type_name": "爱情片", "type_id": "8"},
            {"type_name": "科幻片", "type_id": "9"},
            {"type_name": "恐怖片", "type_id": "10"},
            {"type_name": "剧情片", "type_id": "11"},
            {"type_name": "战争片", "type_id": "12"},
            {"type_name": "国产片", "type_id": "13"},
            {"type_name": "港台片", "type_id": "14"},
            {"type_name": "日韩剧", "type_id": "17"},
            {"type_name": "美剧", "type_id": "15"},
            {"type_name": "内地综艺", "type_id": "21"},
            {"type_name": "港台综艺", "type_id": "24"},
            {"type_name": "日韩综艺", "type_id": "22"},
            {"type_name": "欧美综艺", "type_id": "23"},
            {"type_name": "国产动漫", "type_id": "25"},
            {"type_name": "港台动漫", "type_id": "28"},
            {"type_name": "日韩动漫", "type_id": "26"},
            {"type_name": "欧美动漫", "type_id": "27"}
        ]
        result['class'] = classes
        result['filters'] = {} 
        return result

    def _parse_html_robust(self, html_text):
        videos = []
        links = re.findall(r'href=[\'\"]([^\'\"]+?\.html)[\'\"]', html_text)
        unique_links = list(dict.fromkeys(links))
        
        black_keywords = [
            '首页', '电影', '电视剧', '综艺', '动漫', '动作', '喜剧', '爱情', '科幻', 
            '恐怖', '剧情', '战争', '国产', '香港', '台湾', '欧美', '日本', '韩国', '海外', 
            '港台', '内地', '新片', '热播', '下一页', '上一页', '我的', '筛选', '排表', '留言'
        ]
        
        for vod_id in unique_links:
            if any(x in vod_id for x in ['vodtype', 'vodshow', 'vodsearch', 'index.html', 'map.html', 'javascript']):
                continue
                
            pos = html_text.find(vod_id)
            if pos == -1: continue
            block = html_text[max(0, pos-200): min(len(html_text), pos+400)]
            
            vod_name = ""
            title_match = re.search(r'title=[\'\"]([^\'\"]+?)[\'\"]', block)
            if title_match: vod_name = title_match.group(1).strip()
            
            if not vod_name:
                alt_match = re.search(r'alt=[\'\"]([^\'\"]+?)[\'\"]', block)
                if alt_match: vod_name = alt_match.group(1).strip()
            
            if not vod_name:
                text_match = re.search(r'>([^<>\u4e00-\u9fa5]*[\u4e00-\u9fa5]+[^<>]*)</', block)
                if text_match: vod_name = text_match.group(1).strip()
                
            if not vod_name:
                vod_name = vod_id.split('/')[-1].replace('.html', '')
            
            vod_name = html.unescape(vod_name)
            
            if any(k in vod_name for k in black_keywords):
                continue
                
            if any(xxx in vod_name for xxx in self.xxx_keywords):
                continue
                
            vod_pic = "https://img.ykimg.com/051600005E2E208413FC3E08A602BFF8"
            for attr in ['data-original', 'data-src', 'src', 'data-cover']:
                pic_match = re.search(rf'{attr}=[\'\"]([^\'\"]+?)[\'\"]', block)
                if pic_match:
                    pic = pic_match.group(1)
                    if '.gif' in pic.lower() and attr == 'src': continue
                    if pic.startswith('//'): vod_pic = "https:" + pic
                    elif pic.startswith('/'): vod_pic = self.host + pic
                    else: vod_pic = pic
                    break
            
            remarks = "热播"
            rem_match = re.search(r'class="pic-text[^">]*">([^<]+)</span>', block)
            if rem_match: 
                remarks = html.unescape(rem_match.group(1).strip())
            
            if not vod_id.startswith('/'):
                vod_id = '/' + vod_id

            videos.append({
                "vod_id": vod_id, "vod_name": vod_name, "vod_pic": vod_pic, "vod_remarks": remarks
            })
        return videos

    def homeVideoContent(self):
        return self.categoryContent("1", "1", {}, {})

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        videos = []
        urls_to_try = [
            f"{self.host}/vodshow/{tid}--------{pg}---.html",
            f"{self.host}/video/{tid}--------{pg}---.html",
            f"{self.host}/vodtype/{tid}-{pg}.html",
            f"{self.host}/vodtype/{tid}--------{pg}---.html"
        ]
        
        for url in urls_to_try:
            try:
                res = requests.get(url, headers=self.header, timeout=5, verify=False, allow_redirects=False)
                if res.status_code in [301, 302] and (res.headers.get('Location') == '/' or 'index.html' in res.headers.get('Location', '')):
                    continue
                res.encoding = 'utf-8'
                parsed_list = self._parse_html_robust(res.text)
                if len(parsed_list) > 0:
                    videos = parsed_list
                    break
            except Exception as e:
                continue
                
        if not videos:
            result['list'] = []
            return result
            
        # 强制限制加载数量为 20
        result['list'] = videos[:20]
        result['page'] = int(pg)
        result['pagecount'] = 99
        result['limit'] = 20
        result['total'] = len(videos[:20])
        return result

    def detailContent(self, ids):
        try:
            vodId = ids[0]
            backup_name = "未知影片"
            if "@@" in vodId:
                parts = vodId.split("@@")
                vodId = parts[0]
                backup_name = parts[1]

            if vodId.startswith('http'):
                url = vodId
            else:
                url = f"{self.host}{vodId}" if vodId.startswith('/') else f"{self.host}/{vodId}"
                
            res = requests.get(url, headers=self.header, timeout=8, verify=False, allow_redirects=True)
            res.encoding = 'utf-8'
            html_text = res.text

            name_match = re.search(r'<h1>([^<]+)</h1>', html_text)
            if not name_match: name_match = re.search(r'class="title">([^<]+)</h1>', html_text)
            if not name_match: name_match = re.search(r'title">([^<]+)<', html_text)
            name = name_match.group(1).strip() if name_match else backup_name
            name = html.unescape(name)
            
            vod_pic = "https://img.ykimg.com/051600005E2E208413FC3E08A602BFF8"
            pic_match = re.search(r'(?:data-original|src)=[\'\"]([^\'\"]+?)[\'\"]', html_text)
            if pic_match:
                vod_pic = pic_match.group(1)
                if vod_pic.startswith('//'): vod_pic = "https:" + vod_pic
                elif vod_pic.startswith('/'): vod_pic = self.host + vod_pic
            
            video_detail = {
                "vod_id": ids[0], "vod_name": name, "vod_pic": vod_pic,
                "type_name": "顶级片源", "vod_year": "", "vod_area": "", "vod_actor": "", "vod_director": "", "vod_content": ""
            }

            play_froms = []
            play_urls = []

            list_blocks = re.findall(r'(<(?:ul|div)[^>]*?playlist[^>]*?>.*?<\/(?:ul|div)>)', html_text, re.S)
            
            if not list_blocks:
                list_blocks = re.findall(r'(<ul[^>]*?active[^>]*?>.*?</ul>)', html_text, re.S)

            if list_blocks:
                source_names = re.findall(r'data-toggle="tab"[^>]*>([^<]+)</a>', html_text)
                if not source_names:
                    source_names = re.findall(r'alt=[\'\"]([^\'\"]+?)[\'\"]', html_text)
                
                for idx, block in enumerate(list_blocks):
                    links = re.findall(r'href=[\'\"]([^\'\"]*?(?:vodplay|/play/)[^\'\"]*?)[\'\"]>([^<]+)</a>', block)
                    if links:
                        seen = set()
                        urls = []
                        for link in links:
                            link_url = link[0].strip()
                            if link_url not in seen:
                                seen.add(link_url)
                                play_name = html.unescape(link[1].strip())
                                urls.append(f"{play_name}${link_url}")
                        
                        if urls:
                            if idx < len(source_names):
                                src_name = source_names[idx].strip()
                            else:
                                src_name = f"顶级专线 {idx + 1}"
                                
                            if not src_name or any(k in src_name for k in ['首页', '下载', 'APP']):
                                src_name = f"普通线路 {idx + 1}"
                                
                            play_froms.append(src_name)
                            play_urls.append("#".join(urls))
            
            if not play_urls:
                all_links = re.findall(r'href=[\'\"]([^\'\"]*?(?:vodplay|/play/)[^\'\"]*?)[\'\"]>([^<]+)</a>', html_text)
                if all_links:
                    seen = set()
                    urls = []
                    for link in all_links:
                        link_url = link[0].strip()
                        if link_url not in seen:
                            seen.add(link_url)
                            play_name = html.unescape(link[1].strip())
                            urls.append(f"{play_name}${link_url}")
                    play_froms.append("顶级专用线路")
                    play_urls.append("#".join(urls))

            if play_urls:
                video_detail['vod_play_from'] = "$$$".join(play_froms)
                video_detail['vod_play_url'] = "$$$".join(play_urls)
            else:
                video_detail['vod_play_from'] = "暂无可用线路"
                video_detail['vod_play_url'] = "未找到播放集数$#"

            return {'list': [video_detail]}
        except Exception as e:
            return {'list': []}

    def searchContent(self, key, quick, pg=1):
        result = {}
        videos = []
        
        if any(xxx in key for xxx in self.xxx_keywords):
            result['list'] = []
            return result
            
        url = f"{self.host}/vodsearch/{key}----------{pg}---.html"
        try:
            res = requests.get(url, headers=self.header, timeout=8, verify=False, allow_redirects=True)
            res.encoding = 'utf-8'
            raw_videos = self._parse_html_robust(res.text)
            
            match_key = key.strip()
            short_key = match_key[:3] if len(match_key) > 3 else match_key
            
            for item in raw_videos:
                if any(xxx in item["vod_name"] for xxx in self.xxx_keywords):
                    continue
                
                if (short_key not in item["vod_name"]) and (match_key not in item["vod_name"]):
                    continue
                    
                safe_id = f"{item['vod_id']}@@{item['vod_name']}"
                videos.append({
                    "vod_id": safe_id,
                    "vod_name": item["vod_name"],
                    "vod_pic": item["vod_pic"] if item["vod_pic"] else "https://img.ykimg.com/051600005E2E208413FC3E08A602BFF8",
                    "vod_remarks": item["vod_remarks"] if item["vod_remarks"] else "搜索结果"
                })
        except Exception as e:
            pass
            
        result['list'] = videos
        result['page'] = int(pg)
        result['pagecount'] = 1
        result['limit'] = len(videos)
        result['total'] = len(videos)
        return result

    def playerContent(self, flag, id, vipFlags):
        try:
            if "@@" in id: id = id.split("@@")[0]
            url = f"{self.host}{id}" if id.startswith('/') else f"{self.host}/{id}"
            res = requests.get(url, headers=self.header, timeout=8, verify=False, allow_redirects=True)
            res.encoding = 'utf-8'
            html_text = res.text
            player_json = re.search(r'var player_.*?=(.*?)</script>', html_text, re.S)
            if player_json:
                data = json.loads(player_json.group(1).strip())
                video_url = data.get('url', '')
                if 'm3u8' in video_url or 'mp4' in video_url:
                    return {"parse": 0, "playUrl": "", "url": video_url, "header": ""}
                else:
                    return {"parse": 1, "playUrl": "", "url": "https://jx.jsonplayer.com/player/?url=" + video_url, "header": ""}
            return {"parse": 0, "playUrl": "", "url": ""}
        except Exception as e:
            return {"parse": 0, "playUrl": "", "url": ""}

    def isVideoFormat(self, url): return url.lower().endswith(('.m3u8', '.mp4'))
    def manualVideoCheck(self): pass
    def localProxy(self, params): return None

if __name__ == '__main__':
    pass