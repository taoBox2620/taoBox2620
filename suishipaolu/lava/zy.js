import { Crypto, _ } from 'assets://js/lib/cat.js';
 
let siteUrl = '';
let key = '';
let iv = '';
let siteKey = '';
let siteType = 3;
let apiPrefix = 'getappapi.index';
 
const prefixMap = {
    '1': 'getappapi.index',
    '2': 'qijiappapi.index',
    '3': 'appapi'
};
 
let enableVerifyTimeSign = false;
// 1. 核心修改：设置全局默认 UA
let headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; M2012K11AC Build/RKQ1.200826.002; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/90.0.4430.210 Mobile Safari/537.36',
    'app-user-device-id': '291b226282010337c9443590d6457be15',
    'app-version-code': '112'
};
 
let parseMap = {};
let homeVods = [];
let Searchstatus = false;
let searchApiSuffix = '';
let souParamName = '';
let souSalt = '';
let extraSearchHeaders = {};
let initSuffix = 'init';
let hasCustomInit = false;
let thirdDanmuBaseUrl = '';
let customPlayUa = ''; 
let customPlayqijireff = ''; // 新增：全局自定义播放qijireff变量
let request = async (reqUrl, data, header, method) => {
    let finalHeaders = { ...headers };
    if (enableVerifyTimeSign) {
        const timestamp = Math.floor(Date.now() / 1000).toString();
        const sign = aesEncode(timestamp, key, iv);
        finalHeaders['app-api-verify-time'] = timestamp;
        finalHeaders['app-api-verify-sign'] = sign;
    }
    if (header) {
        finalHeaders = { ...finalHeaders, ...header };
    }
    let res = await req(reqUrl, {
        method: method || 'get',
        data: data || '',
        headers: finalHeaders,
        postType: method === 'post' ? 'form' : '',
        timeout: 10000,
    });
    return res.content;
};
 
let request_text = async (reqUrl, data, header, method, tobase64) => {
    let finalHeaders = { ...headers };
    if (enableVerifyTimeSign) {
        const timestamp = Math.floor(Date.now() / 1000).toString();
        const sign = aesEncode(timestamp, key, iv);
        finalHeaders['app-api-verify-time'] = timestamp;
        finalHeaders['app-api-verify-sign'] = sign;
    }
    if (header) {
        finalHeaders = { ...finalHeaders, ...header };
    }
    let optObj = {
        headers: finalHeaders,
        method: method || 'get',
        data: method === 'post' ? data : undefined,
        postType: method === 'post' ? (data ? 'raw' : 'form') : undefined,
        timeout: 10000,
    };
    if (tobase64) {
        optObj.buffer = 2;
    }
    let res = await req(reqUrl, optObj);
    return res.content;
};
 
async function init(cfg) {
    siteKey = cfg.skey;
    siteType = cfg.stype;
    if (!cfg.ext) return;
    let extObj;
    if (typeof cfg.ext === 'string') {
        extObj = JSON.parse(cfg.ext);
    } else if (typeof cfg.ext === 'object' && cfg.ext !== null) {
        extObj = cfg.ext;
    } else {
        return;
    }
    if (extObj.init && typeof extObj.init === 'string' && extObj.init.startsWith('V')) {
        initSuffix = 'init' + extObj.init;
        hasCustomInit = true;
    }
    if (extObj.time !== undefined) {
        const timeVal = String(extObj.time);
        enableVerifyTimeSign = (timeVal === '1' || timeVal === 'true' || timeVal === '1');
    }
    if (extObj.code !== undefined) {
        forceVerifyCode = String(extObj.code).trim();
    }
    if (extObj.ua2 !== undefined) {
        customPlayUa = String(extObj.ua2).trim();
    }
    // 新增：解析ext中的自定义qijireff配置
    if (extObj.qijireff !== undefined) {
        customPlayqijireff = String(extObj.qijireff).trim();
    }
    if (extObj.head && typeof extObj.head === 'string') {
        const headStr = extObj.head.trim();
        if (headStr) {
            const items = headStr.split(',');
            for (let item of items) {
                const trimmed = item.trim();
                if (!trimmed) continue;
                const colonIndex = trimmed.indexOf(':');
                if (colonIndex > 0) {
                    const hKey = trimmed.substring(0, colonIndex).trim();
                    const hValue = trimmed.substring(colonIndex + 1).trim();
                    if (hKey && hValue) {
                        headers[hKey] = hValue;
                    }
                }
            }
        }
    }
    let host = extObj.host || '';
    if (host) {
        if (host.startsWith('http') && (host.endsWith('.txt') || host.endsWith('.json'))) {
            let response = await request(host, null, headers, 'get');
            let urls = response.split('\n').map(line => line.trim()).filter(line => line && line.startsWith('http'));
            if (urls.length > 0) {
                host = urls[0];
            }
        }
        siteUrl = host.replace(/\/+$/, '');
        if (!siteUrl.includes('php')) {
            siteUrl += '/api.php';
        }
    }
    key = extObj.key || '';
    iv = extObj.iv || key;
    if (extObj.api && prefixMap[extObj.api]) {
        apiPrefix = prefixMap[extObj.api];
    }
    if (extObj.version) {
        headers['app-version-code'] = String(extObj.version);
    }
    if (extObj.id) {
        headers['app-user-device-id'] = extObj.id;
    }
    if (extObj.token) {
        headers['app-user-token'] = extObj.token;
    }
    if (extObj.ua) {
        headers['User-Agent'] = extObj.ua;
    }
}
 
function processSignatureValue(sig) {
    if (sig.length < 8) {
        return sig.split('').reverse().join('');
    } else {
        let rear = sig.slice(-8).split('').reverse().join('');
        let front = sig.slice(0, -8).split('').reverse().join('');
        return front + rear;
    }
}
 
async function home(filter) {
    let initUrl = `${siteUrl}/${apiPrefix}/${initSuffix}`;
    let rets = JSON.parse(await request(initUrl)).data;
    let data = JSON.parse(aesDecode(rets, key, iv));
 
    let rawDanmuUrl = data.config?.third_danmu_url || '';
 
    if (Array.isArray(rawDanmuUrl)) {
        rawDanmuUrl = rawDanmuUrl.find(u => u && typeof u === 'string' && u.trim()) || '';
    } else if (typeof rawDanmuUrl !== 'string') {
        rawDanmuUrl = '';
    }
 
    if (rawDanmuUrl) {
        thirdDanmuBaseUrl = rawDanmuUrl.trim();
        let lower = thirdDanmuBaseUrl.toLowerCase();
        if (!lower.match(/[?&]url=$/)) {
            thirdDanmuBaseUrl += thirdDanmuBaseUrl.includes('?') ? '&url=' : '?url=';
        }
    } else {
        thirdDanmuBaseUrl = 'https://dmku.hls.one/?ac=dm&url='; 
    }
 
    if (data.box_config) {
        let originalKey = key;
        let swappedKey = originalKey.split('').reverse().join('');
        let md5Key = md5(swappedKey);
        let dynamicIv = md5Key.substring(0, 16);
        let decrypted = aesDecode(data.box_config, swappedKey, dynamicIv);
        let boxJson = JSON.parse(decrypted);
        if (boxJson.search_name) {
            searchApiSuffix = boxJson.search_name;
        }
        if (boxJson.signature_name && boxJson.signature_value) {
            souParamName = boxJson.signature_name;
            souSalt = processSignatureValue(boxJson.signature_value);
        }
        if (boxJson.api_header && boxJson.api_header.key && boxJson.api_header.value) {
            extraSearchHeaders[boxJson.api_header.key] = boxJson.api_header.value;
        }
    } else {
        searchApiSuffix = 'searchList';
        souParamName = '';
        souSalt = '';
    }
 
    Searchstatus = data.config?.system_search_verify_status || false;
 
    let filters = {};
    let classes = [];
    homeVods = [];
 
    _.forEach(data.type_list, item => {
        if (item.type_id > 0) {
            if (item.recommend_list && Array.isArray(item.recommend_list)) {
                homeVods = homeVods.concat(item.recommend_list);
            }
        }
 
        classes.push({
            type_id: item.type_id,
            type_name: item.type_name,
        });
 
        let filterList = [];
        _.forEach(item.filter_type_list, f => {
            let filter = {};
            if (f.name === 'class') {
                filter['name'] = '分类';
                filter['key'] = f.name;
                filter['value'] = _.map(f.list, i => ({ v: i, n: i }));
            }
            if (f.name === 'area') {
                filter['name'] = '区域';
                filter['key'] = f.name;
                filter['value'] = _.map(f.list, i => ({ v: i, n: i }));
            }
            if (f.name === 'lang') {
                filter['name'] = '语言';
                filter['key'] = f.name;
                filter['value'] = _.map(f.list, i => ({ v: i, n: i }));
            }
            if (f.name === 'year') {
                filter['name'] = '年份';
                filter['key'] = f.name;
                filter['value'] = _.map(f.list, i => ({ v: i, n: i }));
            }
            if (f.name === 'sort') {
                filter['name'] = '排序';
                filter['key'] = f.name;
                filter['value'] = _.map(f.list, i => ({ v: i, n: i }));
            }
            if (Object.keys(filter).length > 0) {
                filterList.push(filter);
            }
        });
        if (filterList.length > 0) {
            filters[item.type_id] = filterList;
        }
    });
 
    return JSON.stringify({
        'class': classes,
        'filters': filters,
    });
}
 
async function homeVod() {
    return JSON.stringify({
        list: homeVods,
    });
}
 
async function category(tid, pg, filter, extend) {
    if (pg <= 0) pg = 1;
    let url = `${siteUrl}/${apiPrefix}/typeFilterVodList`;
    let params = {
        "area": extend['area'] || "全部",
        "sort": extend['sort'] || "最新",
        "class": extend['class'] || "全部",
        "type_id": tid,
        "year": extend['year'] || "全部",
        "lang": extend['lang'] || '全部',
        "page": pg,
    };
    let encData = JSON.parse(await request(url, params, '', 'post')).data;
    let videos = JSON.parse(aesDecode(encData, key, iv)).recommend_list;
    return JSON.stringify({
        page: pg,
        pagecount: 9999,
        list: videos,
    });
}
 
async function detail(id) {
    let url = `${siteUrl}/${apiPrefix}/vodDetail`;
    let resp = await request(url, { vod_id: id }, '', 'post');
    let jsonResp = JSON.parse(resp);
    let encData = jsonResp.data;
    let decoded = aesDecode(encData, key, iv);
    let info = JSON.parse(decoded);
    let videos = {
        vod_id: info.vod.vod_id,
        vod_name: info.vod.vod_name,
        vod_area: info.vod.vod_area,
        vod_director: info.vod.vod_director,
        vod_actor: info.vod.vod_actor,
        vod_pic: info.vod.vod_pic,
        vod_content: info.vod.vod_content,
        type_name: info.vod.vod_class,
        vod_year: info.vod.vod_year 
    };
    let froms = [];
    let urls = [];
    let playSources = _.map(info.vod_play_list, item => {
        const playerInfo = item.player_info || {};
        const parse = playerInfo.parse || '';
        // 优先应用全局 UA
        const ua = playerInfo.user_agent || customPlayUa || headers['User-Agent']; 
        // 新增：qijireff优先级 - 播放器内置 > 自定义配置 > 空（不携带）
        const qijireff = playerInfo.qijireff || customPlayqijireff || '';
        const nameUrls = _.map(item.urls || [], item2 => {
            const { name = '', url = '', token = '', parse_api_url = '', nid = 1 } = item2;
            // 新增：把qijireff拼接到播放参数，位置在ua后、vodId前
            return `${name}$${url}@@${parse}@@${token}@@${parse_api_url}@@${ua}@@${qijireff}@@${info.vod.vod_id}@@${nid}`;
        }).join('#');
        return {
            show: playerInfo.show || 'Unknown',
            urls: nameUrls 
        };
    });
    let showCount = {};
    playSources = _.map(playSources, source => {
        let showName = source.show;
        if (showCount[showName]) {
            showCount[showName]++;
            showName = `${showName}${showCount[showName]}`;
        } else {
            showCount[showName] = 1;
        }
        return {
            show: showName,
            urls: source.urls 
        };
    });
    playSources.sort((a, b) => {
        const aShow = a.show.toLowerCase();
        const bShow = b.show.toLowerCase();
        const getPriority = (show) => {
            if (show.includes('4k')) return 1;
            if (show.includes('K')) return 2;
            if (show.includes('独家')) return 3;
            if (show.includes('秒播')) return 4;
            if (show.includes('自建')) return 5;
            if (show.includes('蓝光')) return 6;
            if (show.includes('专线')) return 7;
            return 8;
        };
        return getPriority(aShow) - getPriority(bShow);
    });
    froms = _.map(playSources, source => source.show);
    urls = _.map(playSources, source => source.urls);
    videos.vod_play_from = froms.join('$$$');
    videos.vod_play_url = urls.join('$$$');
    return JSON.stringify({
        list: [videos],
    });
}
 
// 2. 重点修改：play 函数解析qijireff并按需添加到请求头
async function play(flag, id, flags) {
    let parts = id.split('@@');
    let playUrl = parts[0];
    let parse = parts[1] || '';
    let token = parts[2] || '';
    let parse_api_url = parts[3] || '';
    let ua = parts[4] || headers['User-Agent']; 
    let qijireff = parts[5] || ''; // 新增：解析拼接的qijireff参数
    let vodId = parts[6] || '';  // 注意：参数索引后移一位
    let nidStr = parts[7] || '1';// 注意：参数索引后移一位
    
    // 构造请求头：保留原有UA+Referer，按需添加qijireff
    let playHeader = { 
        'User-Agent': ua,
        'Referer': siteUrl.split('/api.php')[0] + '/' 
    };
    // 新增：有qijireff配置则添加到请求头，无则不携带
    if (qijireff) {
        playHeader['qijireff'] = qijireff;
    }
    
    let danmakuUrl = '';
    if (thirdDanmuBaseUrl && vodId) {
        let nid = parseInt(nidStr, 10);
        if (isNaN(nid) || nid < 1) nid = 1;
        let urlPosition = nid - 1;
        let danmuParams = {
            url_position: urlPosition.toString(),
            vod_id: vodId 
        };
        let danmuRet = await request(`${siteUrl}/${apiPrefix}/danmuList`, danmuParams, '', 'post');
        let danmuResponse = JSON.parse(danmuRet);
        if (danmuResponse.data) {
            let decryptedDanmu = JSON.parse(aesDecode(danmuResponse.data, key, iv));
            if (decryptedDanmu && decryptedDanmu.official_url) {
                let realDanmuUrl = thirdDanmuBaseUrl + decryptedDanmu.official_url;
                let EncodedUrl = encodeURIComponent(realDanmuUrl);
                danmakuUrl = js2Proxy(false, siteType, siteKey || '', EncodedUrl, headers);
            }
        }
    }
 
    // 情况 A：直链播放
    if (
        (playUrl.includes('http://') || playUrl.includes('https://')) &&
        (playUrl.includes('m3u8') || playUrl.includes('mp4') || playUrl.includes('mkv')) &&
        !parse_api_url
    ) {
        return JSON.stringify({
            parse: 0,
            url: playUrl,
            danmaku: danmakuUrl,
            header: playHeader // 携带UA+Referer+按需qijireff
        });
    }
    // 情况 B：网页/解析接口播放
    if (parse.startsWith("http")) {
        let parseUrl = parse + playUrl;
        if (token) parseUrl += '&token=' + token;
        
        let rets = await request(parseUrl, null, playHeader, 'get');
        if (rets.indexOf('DOCTYPE html') > -1) {
            return JSON.stringify({
                parse: 1,
                url: parseUrl,
                danmaku: danmakuUrl,
                header: playHeader
            });
        }
        try {
            let parseJson = JSON.parse(rets);
            let finalUrl = parseJson['url'] || parseJson['data']?.['url'] || '';
            return JSON.stringify({
                parse: 0,
                url: finalUrl,
                danmaku: danmakuUrl,
                header: playHeader
            });
        } catch (e) {
            return JSON.stringify({ parse: 1, url: parseUrl, header: playHeader });
        }
    }
    // 情况 C：API 内部解密
    let params = {
        'parse_api': parse,
        'url': aesEncode(playUrl, key, iv),
        'token': token,
    };
    try {
        let rets = await request(`${siteUrl}/${apiPrefix}/vodParse`, params, playHeader, 'post');
        let urlDecoded = aesDecode(JSON.parse(rets).data, key, iv);
        let parsed = JSON.parse(urlDecoded);
        let finalPlayUrl = JSON.parse(parsed.json).url || '';
        
        return JSON.stringify({
            parse: 0,
            url: finalPlayUrl,
            danmaku: danmakuUrl,
            header: playHeader
        });
    } catch (e) {
        return JSON.stringify({ parse: 0, url: playUrl, header: playHeader });
    }
}
 
async function search(wd, quick, pg) {
    if (hasCustomInit) { await home({}); }
    let searchPath = searchApiSuffix || 'searchList';
    let url = `${siteUrl}/${apiPrefix}/${searchPath}`;
    let retryCount = 0;
    const maxRetries = 1;
    let videos = [];
    let attemptedCaptcha = false;
    let attemptedSlider = false;
    let sliderVerified = false;
    let sliderId = '';
    
    let params = { 'page': '1', 'type_id': '0', 'keywords': wd };
    
    if (souParamName && souSalt) {
        const currentTimestamp = Math.floor(Date.now() / 1000).toString();
        const souString = `/${souParamName}-${currentTimestamp}-sb-0-${souSalt}`;
        const md5Value = md5(souString);
        const finalValue = `${currentTimestamp}-sb-0-${md5Value}`;
        params[souParamName] = finalValue;
    }
    
    let searchHeaders = { ...headers, ...extraSearchHeaders };
    
    if (forceVerifyCode) {
        params['code'] = forceVerifyCode;
        params['key'] = generateUUID();
    }
    
    const maxWaitRetries = 2;
    let waitRetryCount = 0;
    
    while (true) {
        let encData = await request(url, params, searchHeaders, 'post');
        let response = JSON.parse(encData);
        
        if (response.code === 1001 && response.need_slider === true && !attemptedSlider) {
            attemptedSlider = true;
            let getSliderUrl = `${siteUrl}/${apiPrefix}/getSlider`;
            let sliderResponse = await request(getSliderUrl, {}, searchHeaders, 'post');
            let sliderJson = JSON.parse(sliderResponse);
            if (sliderJson.code === 1 && sliderJson.data) {
                let sliderDecrypted = aesDecode(sliderJson.data, key, iv);
                let sliderData = JSON.parse(sliderDecrypted);
                sliderId = sliderData.slider_id || '';
                let targetX = parseInt(sliderData.target_x) || 0;
                if (sliderId && targetX > 0) {
                    let posX = targetX + (Math.floor(Math.random() * 3) - 1);
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    let verifyParams = { pos_x: posX.toString(), slider_id: sliderId, timestamp: Date.now().toString() };
                    let verifySliderUrl = `${siteUrl}/${apiPrefix}/verifySlider`;
                    let verifyResponse = await request(verifySliderUrl, verifyParams, searchHeaders, 'post');
                    let verifyJson = JSON.parse(verifyResponse);
                    if (verifyJson.code === 1 && verifyJson.data) {
                        let verifyDecrypted = aesDecode(verifyJson.data, key, iv);
                        if (JSON.parse(verifyDecrypted).verified === true) {
                            sliderVerified = true;
                            continue;
                        }
                    }
                }
            }
        }
        
        if (response.code === 0 && (!response.data || response.data.length === 0) && response.msg && /等|稍/i.test(response.msg)) {
            if (waitRetryCount >= maxWaitRetries) break;
            let waitSeconds = extractWaitTime(response.msg);
            await new Promise(resolve => setTimeout(resolve, (waitSeconds + 1) * 1000));
            waitRetryCount++;
            continue;
        }
        
        if (response.data && response.data.length > 0) {
            let decodedData = JSON.parse(aesDecode(response.data, key, iv));
            videos = decodedData.search_list || [];
            break;
        } else if (!forceVerifyCode && (Searchstatus || (response.code === 0 && response.msg && response.msg.includes('验证码')))) {
            if (attemptedCaptcha) break;
            attemptedCaptcha = true;
            const random_uuid = generateUUID();
            let verifyUrl = `${siteUrl}/${apiPrefix.replace('.index', '')}.verify/create?key=${random_uuid}`;
            let base64Img = (await request_text(verifyUrl, null, headers, 'get', true)).replace(/\n/g, '');
            let ocrResult = await request_text('https://api.nn.ci/ocr/b64/text', base64Img, { 'User-Agent': headers['User-Agent'] }, 'post');
            params['code'] = ocrResult.trim();
            params['key'] = random_uuid;
            continue;
        } else {
            break;
        }
    }
    return JSON.stringify({ list: videos });
}
 
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = Math.random() * 16 | 0;
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
}
 
function aesDecode(str, keyStr, ivStr, type) {
    const key = Crypto.enc.Utf8.parse(keyStr);
    const iv = Crypto.enc.Utf8.parse(ivStr);
    if (type === 'hex') {
        return Crypto.AES.decrypt({ ciphertext: Crypto.enc.Hex.parse(str) }, key, { iv: iv, mode: Crypto.mode.CBC, padding: Crypto.pad.Pkcs7 }).toString(Crypto.enc.Utf8);
    }
    return Crypto.AES.decrypt(str, key, { iv: iv, mode: Crypto.mode.CBC, padding: Crypto.pad.Pkcs7 }).toString(Crypto.enc.Utf8);
}
 
function aesEncode(str, keyStr, ivStr, type) {
    const key = Crypto.enc.Utf8.parse(keyStr);
    const iv = Crypto.enc.Utf8.parse(ivStr);
    let encData = Crypto.AES.encrypt(str, key, { iv: iv, mode: Crypto.mode.CBC, padding: Crypto.pad.Pkcs7 });
    return type === 'hex' ? encData.ciphertext.toString(Crypto.enc.Hex) : encData.toString();
}
 
function md5(text) { return Crypto.MD5(text).toString(); }
function chineseToNumber(chineseStr) {
    const map = { '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10 };
    if (chineseStr.length === 1) return map[chineseStr] || 2;
    if (chineseStr.startsWith('十')) return 10 + (map[chineseStr[1]] || 0);
    return (map[chineseStr[0]] * 10) + (map[chineseStr[2]] || 0);
}
 
function extractWaitTime(message) {
    const d = message.match(/(\d+)\s*秒/);
    if (d) return parseInt(d[1], 10);
    const c = message.match(/([零一二三四五六七八九十两]+)\s*秒/);
    if (c) return chineseToNumber(c[1]);
    return 2;
}
 
function hexToDec(hex) {
    hex = (hex || '#FFFFFF').replace(/^#/, '').toUpperCase();
    return parseInt(hex.padEnd(6, '0').slice(0, 6), 16);
}
 
function escapeXml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
}
 
function jsonDanmakuToXml(json) {
    if (!json?.danmuku) return '<?xml version="1.0" encoding="utf-8"?><i><code>0</code></i>';
    let lines = ['<?xml version="1.0" encoding="utf-8"?>', '<i>', ` <code>${json.code || 0}</code>`, ` <id>${escapeXml(json.name || '12345')}</id>`];
    json.danmuku.forEach(d => {
        if (!Array.isArray(d) || d.length < 5) return;
        let p = `${Number(d[0]).toFixed(3)},1,24,${hexToDec(d[2])},,,,,`;
        lines.push(` <d p="${p}">${escapeXml(d[4])}</d>`);
    });
    lines.push('</i>');
    return lines.join('\n');
}
 
async function proxy(params) {
    let url = decodeURIComponent(params.url || params[0] || '');
    if (!url.startsWith('http')) return JSON.stringify({ code: 400, content: "URL Error" });
    let xml = jsonDanmakuToXml(JSON.parse(await request_text(url, null, headers, 'get')));
    return JSON.stringify({ code: 200, content: xml, headers: { "Content-Type": "text/xml; charset=utf-8" } });
}
 
let forceVerifyCode = null;
 
export function __jsEvalReturn() {
    return { init, home, homeVod, category, detail, play, search, proxy };
}