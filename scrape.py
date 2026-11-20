"""高山質店 販売春日店(supplier=b03) 재고를 수집해 한국어로 변환, docs/data.json 에 저장."""
import html, json, os, re, statistics, sys, time, unicodedata, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent
BASE = "https://takayama78online.jp"
CATEGORIES = {  # tree 코드: 한국어 이름 (b03_zaiko.aspx 의 버튼 목록과 동일)
    "10": "남성 시계", "20": "여성 시계", "30": "가방", "40": "지갑",
    "50": "소품", "60": "브랜드 주얼리", "b0": "악기",
}
DICT = json.loads((ROOT / "dict_ja_ko.json").read_text(encoding="utf-8"))
DICT_KEYS = sorted(DICT, key=len, reverse=True)  # 긴 단어부터 치환


def fetch(tree, page):
    url = (f"{BASE}/shop/goods/search.aspx?tree={tree}&sort=rgd&stock_exists=0"
           f"&supplier=b03&ps=50&p={page}&search.x=1")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (inventory-ko)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("cp932", errors="replace")
        except OSError:
            if attempt == 2:
                raise
            time.sleep(5)


def text(pattern, block):
    m = re.search(pattern, block, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""


def parse(page_html):
    items = []
    for block in page_html.split('class="StyleT_Item_"')[1:]:
        code = text(r'href="/shop/g/g(\w+)/"', block)
        if not code:
            continue
        price = text(r'class="price_ prc_">([^<]*)', block)
        items.append({
            "code": code,
            "title": text(r'class="goods_name_"[^>]*title="([^"]*)"', block),
            "brand": text(r'class="name1_01_">(.*?)</span>', block),
            "model": text(r'class="name1_02_">(.*?)</span>', block),
            "ref": text(r'class="name1_03_">(.*?)</span>', block),
            "rank": unicodedata.normalize("NFKC", text(r"ランク：(.*?)</span>", block)).removesuffix("品").strip(),
            "price": int(re.sub(r"\D", "", price) or 0),
            "img": text(r'<img alt="[^"]*" src="([^"]+)"', block),
            "new": "/img/sys/new.gif" in block,
            "soldout": "在庫あり" not in block,
        })
    return items


# --- 가타카나 → 한글 음역 (사전에 없는 모델명 등에 사용) ---
CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
ROWS = {  # 자음: 아 이 우 에 오 단
    "ㅇ": "アイウエオ", "ㅋ": "カキクケコ", "ㄱ": "ガギグゲゴ", "ㅅ": "サシスセソ", "ㅈ": "ザジズゼゾ",
    "ㅌ": "タチツテト", "ㄷ": "ダヂヅデド", "ㄴ": "ナニヌネノ", "ㅎ": "ハヒフヘホ", "ㅂ": "バビブベボ",
    "ㅍ": "パピプペポ", "ㅁ": "マミムメモ", "ㄹ": "ラリルレロ",
}
KANA = {}
for c, row in ROWS.items():
    for k, v in zip(row, "ㅏㅣㅜㅔㅗ"):
        KANA[k] = [c, v]
KANA.update({"チ": ["ㅊ", "ㅣ"], "ツ": ["ㅊ", "ㅡ"], "ス": ["ㅅ", "ㅡ"], "ズ": ["ㅈ", "ㅡ"], "ヂ": ["ㅈ", "ㅣ"],
             "ヅ": ["ㅈ", "ㅡ"], "ヤ": ["ㅇ", "ㅑ"], "ユ": ["ㅇ", "ㅠ"], "ヨ": ["ㅇ", "ㅛ"], "ワ": ["ㅇ", "ㅘ"],
             "ヲ": ["ㅇ", "ㅗ"], "ヴ": ["ㅂ", "ㅜ"], "フ": ["ㅍ", "ㅜ"]})
VOWEL_ROW = "アイウエオヤユヨワヲ"
EPENTHETIC = "クグスズツヅブプフ"  # 외래어에서 모음 없이 읽히는 자음 (クロノ→크로노)
JONG = {"": 0, "ㄱ": 1, "ㄴ": 4, "ㄹ": 8, "ㅁ": 16, "ㅂ": 17, "ㅅ": 19}
SMALL_Y = {"ャ": "ㅑ", "ュ": "ㅠ", "ョ": "ㅛ"}
SMALL_V = {"ァ": "ㅏ", "ィ": "ㅣ", "ゥ": "ㅜ", "ェ": "ㅔ", "ォ": "ㅗ"}
W_VOWEL = {"ㅏ": "ㅘ", "ㅣ": "ㅟ", "ㅔ": "ㅞ", "ㅗ": "ㅝ"}
FLAT = {"ㅑ": "ㅏ", "ㅠ": "ㅜ", "ㅛ": "ㅗ"}  # チャ→차, ジャ→자


def kata_to_hangul(word):
    # 히라가나 → 가타카나
    word = "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in word)
    syl = []  # [초성, 중성, 종성] 또는 그대로 둘 문자
    for i, ch in enumerate(word):
        nx = word[i + 1] if i + 1 < len(word) else ""
        end = nx == "" or not ("ァ" <= nx <= "ヺ" or nx == "ー")
        cons = nx in KANA and nx not in VOWEL_ROW
        prev = syl[-1] if syl and isinstance(syl[-1], list) else None
        if prev and (ch in "クグ" and prev[2] == "ㄱ" or ch in "プブ" and prev[2] == "ㅂ") and (end or cons):
            continue  # ック → ㄱ받침 (ロレックス→로렉스), ップ → ㅂ받침 (トップ→톱)
        if ch in "ルム" and prev and not prev[2] and (end or cons):
            prev[2] = "ㄹ" if ch == "ル" else "ㅁ"  # シャネル→샤넬, プレミアム→프레미암
        elif ch in KANA:
            c, v = KANA[ch]
            if (ch in EPENTHETIC or ch in "トド" and end) and (end or cons):
                v = "ㅡ"  # ゴールド→골드
            syl.append([c, v, ""])
        elif ch in SMALL_Y and prev and not prev[2]:
            prev[1] = FLAT[SMALL_Y[ch]] if prev[0] in "ㅈㅊ" else SMALL_Y[ch]
        elif ch in SMALL_V and prev and not prev[2]:
            if prev[0] == "ㅇ" and prev[1] == "ㅜ":
                prev[1] = W_VOWEL.get(SMALL_V[ch], SMALL_V[ch])  # ウォ→워
            else:
                if prev[0] == "ㅎ" and prev[1] == "ㅜ":
                    prev[0] = "ㅍ"  # ファ→파
                prev[1] = SMALL_V[ch]
        elif ch in SMALL_Y or ch in SMALL_V:
            syl.append(["ㅇ", (SMALL_Y | SMALL_V)[ch], ""])
        elif ch == "ン" and prev and not prev[2]:
            prev[2] = "ㄴ"
        elif ch == "ッ" and prev and not prev[2]:
            prev[2] = "ㄱ" if nx in "カキクケコガギグゲゴ" else "ㅂ" if nx in "パピプペポバビブベボ" else "ㅅ"
        elif ch == "ー" and prev:
            continue  # 장음 생략
        else:
            syl.append(ch)
    out = []
    for s in syl:
        if isinstance(s, list):
            out.append(chr(0xAC00 + (CHO.index(s[0]) * 21 + JUNG.index(s[1])) * 28 + JONG[s[2]]))
        else:
            out.append(s)
    return "".join(out)


def to_korean(s):
    s = unicodedata.normalize("NFKC", s)
    for k in DICT_KEYS:
        s = s.replace(k, DICT[k])
    return re.sub(r"[ァ-ヺー]+|[ぁ-ゖ]+", lambda m: kata_to_hangul(m.group()), s)


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "inventory-ko", **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def jpy_krw(old):
    try:  # 유럽중앙은행 기준 환율 (키 불필요)
        return get_json("https://api.frankfurter.dev/v1/latest?from=JPY&to=KRW")["rates"]["KRW"]
    except (OSError, KeyError, ValueError):
        return old.get("jpykrw")  # 실패 시 직전 환율 유지


def norm(s):
    return re.sub(r"[^0-9a-z]", "", unicodedata.normalize("NFKC", s).lower())


def naver_new_price(query, ref):
    """네이버쇼핑 신품(productType 1~3) 중 제목에 품번이 들어간 결과의 중간값(원). 없으면 None."""
    url = "https://openapi.naver.com/v1/search/shop.json?display=40&query=" + urllib.parse.quote(query)
    res = get_json(url, {"X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"],
                         "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"]})
    prices = [int(r["lprice"]) for r in res.get("items", [])
              if r.get("productType") in ("1", "2", "3") and ref in norm(r["title"]) and r.get("lprice")]
    return int(statistics.median(prices)) if prices else None  # 최저가는 부품·액세서리일 수 있어 중간값


def add_new_prices(items):
    if not os.environ.get("NAVER_CLIENT_ID"):
        print("NAVER_CLIENT_ID 없음 — 신품가 비교 생략", file=sys.stderr)
        return
    path = ROOT / "price_cache.json"
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    today, calls = date.today(), 0
    for it in items:
        ref = norm(it["ref"])
        if len(ref) < 4:  # 품번이 없거나 너무 짧으면 오매칭 위험
            continue
        query = f'{it["brand"]} {it["ref"]}'
        hit = cache.get(query)
        if not hit or date.fromisoformat(hit["checked"]) < today - timedelta(days=7):
            if calls >= 3000:  # shortcut: 1회 실행당 상한, 남은 건 다음 실행에서 조회
                continue
            try:
                hit = {"krw": naver_new_price(query, ref), "checked": today.isoformat()}
            except (OSError, ValueError) as e:
                print(f"naver 실패 {query}: {e}", file=sys.stderr)
                continue
            cache[query], calls = hit, calls + 1
            time.sleep(0.12)  # API 초당 호출 제한 대비
        if hit["krw"]:
            it["new_krw"], it["new_q"] = hit["krw"], query
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"naver 조회 {calls}건", file=sys.stderr)


def main():
    old_path = ROOT / "docs" / "data.json"
    old = json.loads(old_path.read_text(encoding="utf-8")) if old_path.exists() else {}
    items = []
    for tree, cat in CATEGORIES.items():
        page = 1
        while True:
            got = parse(fetch(tree, page))
            for it in got:
                it["cat"] = cat
            items += got
            print(f"{cat} p{page}: {len(got)}", file=sys.stderr)
            if len(got) < 50:
                break
            page += 1
            time.sleep(1)  # 원 사이트 부하 방지
    if not items:
        sys.exit("상품 0건 — 사이트 구조 변경 가능성, data.json 을 덮어쓰지 않음")
    for it in items:
        # 제목 형식: 【영문브랜드】가타카나브랜드『모델』품번 사양 보증【中古】 → 브랜드는 영문만 사용
        it["spec_ko"] = to_korean(it["title"].rpartition("』")[2]).strip()
        it["model_ko"] = to_korean(it["model"])
        it["brand"] = to_korean(it["brand"])  # 대부분 영문, 'その他…' 같은 경우만 변환됨
    add_new_prices(items)
    now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
    out = {"updated": now, "jpykrw": jpy_krw(old), "count": len(items), "items": items}
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "data.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"saved {len(items)} items", file=sys.stderr)


def _selftest():
    assert kata_to_hangul("サントス") == "산토스", kata_to_hangul("サントス")
    assert kata_to_hangul("ファ") == "파" and kata_to_hangul("ウォ") == "워"
    assert kata_to_hangul("シャネル") == "샤넬" and kata_to_hangul("チャ") == "차"
    assert kata_to_hangul("ロレックス") == "로렉스" and kata_to_hangul("ゴールド") == "골드"
    assert kata_to_hangul("クロノ") == "크로노" and kata_to_hangul("プレミアム") == "프레미암"
    assert parse('class="StyleT_Item_" <a class="goods_name_" href="/shop/g/g123/" title="【A】b">'
                 '<span class="price_ prc_"> 1,000円</span>ランク：ＡＢ品</span>在庫あり')[0]["price"] == 1000
    assert norm("M46-127 ") == "m46127" and norm("ＩＷ３７１４４６") == "iw371446"


if __name__ == "__main__":
    _selftest()
    if "--test" not in sys.argv:
        main()
