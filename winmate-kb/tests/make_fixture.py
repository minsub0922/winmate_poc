"""스모크 테스트용 소형 픽스처(실제 사이트 구조를 본뜬 합성 데이터). 실제 빌드에는 쓰지 않는다."""
import json, sys
from pathlib import Path
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
H = lambda l, x: {"t": "h", "l": l, "x": x}
P = lambda x: {"t": "p", "x": x}
A = lambda x, h: {"t": "a", "x": x, "href": h}
I = lambda s, alt="": {"t": "img", "src": s, "alt": alt}
S = "https://www.samsung.com"
hosp = [P("고객 유치 경쟁력을 갖춘"), H(3, "미래형 호텔을 완성하다"), P("특장점"), P("추천 솔루션 / 서비스"), P("고객 도입사례"),
  H(2, "투숙객 맞춤 콘텐츠 제공"), P("LYNK Cloud 솔루션을 통해 투숙객 정보에 따라 맞춤형 콘텐츠가 자동 제공됩니다."), P("객실"), P("호텔 운영에 최적화된"),
  H(3, "링크 클라우드 솔루션"), A("자세히 보기", S + "/sec/business/tv-vd-solution/tv-solition-bw-hdlt11a/BW-HDLT11A/"), P("자세히 보기"),
  I("//images.samsung.com/kdp/hosp/ci_slide1_2_obj.png?$ORIGIN_PNG$", "링크 클라우드 안내 이미지"), I("//images.samsung.com/kdp/hosp/ci_slide1_2_obj_mo.png?$ORIGIN_PNG$", "링크 클라우드 안내 이미지"),
  H(2, "편안하고 안락한 SMART 객실 공간"), P("객실 내 다양한 스마트 기기로 투숙객의 편의를 높입니다."), P("객실 내부"), H(4, "무풍 시스템에어컨"), H(4, "호텔 TV"), H(4, "에어드레서"),
  H(2, "투숙 만족도를 높이는 로비 공간"), P("로비 공간을 감각적으로 연출하는 디스플레이와 쾌적한 공조"), P("호텔 리셉션"), P("호텔 라운지"),
  H(3, "LED 사이니지"), A("자세히 보기", S + "/sec/business/led-signage/all-led-signage/?indoor"), I("//images.samsung.com/kdp/hosp/ci_slide3_obj.png", "LED 사이니지 안내 이미지"),
  H(3, "호텔 맞춤형 TV"), A("자세히 보기", S + "/sec/business/hotel-tvs/all-hotel-tvs/"), I("//images.samsung.com/kdp/hosp/ci_slide3_2_obj.png", "호텔 TV 안내 이미지"),
  H(2, "투숙 만족도를 높이는 로비 공간"), P("로비 공간을 감각적으로 연출하는 디스플레이와 쾌적한 공조"), P("호텔 라운지"),
  H(3, "호텔 맞춤형 TV"), A("자세히 보기", S + "/sec/business/hotel-tvs/all-hotel-tvs/"), I("//images.samsung.com/kdp/hosp/ci_slide3_2_obj_mo.png", "호텔 TV 안내 이미지"),
  H(2, "추천 솔루션 / 서비스"), I("//images.samsung.com/kdp/hosp/standard2_feature_1.png", "링크 클라우드 솔루션"), H(3, "링크 클라우드 솔루션"),
  A("자세히 보기", S + "/sec/business/tv-vd-solution/tv-solition-bw-hdlt11a/BW-HDLT11A/"),
  H(2, "고객 도입사례"), I("//images.samsung.com/kdp/hosp/hospitality_customer06.jpg"), H(3, "인스파이어 리조트 - 사이니지 + 호텔 TV"),
  A("자세히 보기", S + "/sec/business/insights/case-study/inspire/")]
case = [H(1, "고객 도입사례"), H(2, "인스파이어 리조트 - 사이니지 + 호텔 TV"), P("2024-05-31"), I("//images.samsung.com/kdp/case/mo_case_01.jpg"),
  I("//images.samsung.com/kdp/case/pc_case_01.jpg"), P("리조트 로비에 설치된 대형 LED 사이니지"), P("업종 : 호텔/리조트"), P("규모 : 객실 1,275실"),
  P("관련 제품"), A("", S + "/sec/business/led-signage/all-led-signage/"), I("//images.samsung.com/kdp/case/img_01.png", "LED 사이니지"),
  A("", S + "/sec/business/hotel-tvs/all-hotel-tvs/"), I("//images.samsung.com/kdp/case/img_02.png", "호텔TV"), P("비즈니스 정보 열람/구독 신청")]
sol = [H(2, "호텔 객실 TV를 한 곳에서 관리하는 클라우드"), P("링크 클라우드는 호텔 객실 TV의 콘텐츠와 상태를 원격으로 관리합니다."), I("//images.samsung.com/kdp/lynk/diagram_01.png", "구성도")]
us = [H(2, "The connected room"), H(3, "Personalize each stay"), P("Transform every guest room into a customizable experience with Samsung displays."),
  A("Explore LYNK Cloud", "/us/business/solutions/industries/hospitality/lynk-cloud/"), H(2, "Contact a sales expert"), P("Get in touch with our sales team")]
pages = {"items": {
  "/sec/business/hospitality/": {"kind": "industry_kr", "url": S + "/sec/business/hospitality/", "title": "호텔 | 업종별 제안", "blocks": hosp},
  "/sec/business/insights/case-study/inspire/": {"kind": "case_kr", "url": S + "/sec/business/insights/case-study/inspire/", "title": "도입사례", "blocks": case},
  "/sec/business/tv-vd-solution/tv-solition-bw-hdlt11a/BW-HDLT11A/": {"kind": "solution_service_kr", "url": S + "/sec/business/tv-vd-solution/tv-solition-bw-hdlt11a/BW-HDLT11A/", "title": "링크 클라우드", "blocks": sol},
  "/us/business/solutions/industries/hospitality/": {"kind": "us_page", "url": S + "/us/business/solutions/industries/hospitality/", "title": "Hospitality", "blocks": us}}}
cats = [{"p": "hotel-tvs/all-hotel-tvs", "no": "10001300", "title": "호텔TV", "allFilters": ["8000", "smart-tv"]},
        {"p": "led-signage/all-led-signage", "no": "10001200", "title": "스마트 LED 사이니지", "allFilters": ["indoor", "the-wall"]},
        {"p": "tv-vd-solution/all-tv-vd-solution", "no": "100002764", "title": "TV/음향 솔루션", "allFilters": ["lynk-cloud"]}]
def prod(cat, no, gid, nm, code, sub, usp, comp=None):
    return {"catPath": cat, "catNo": no, "goodsId": gid, "goodsNm": nm, "mdlCode": code, "mdlNm": code, "grpPath": code.lower(),
            "goodsDetailUrl": f"{cat.split('/')[0]}/{code.lower()}/{code}/", "dlgtDispClsfEnNm": sub, "compDispClsfEnNm": comp or cat.split('/')[0],
            "uspDescList": usp, "saleStatCd": "17", "sysRegDtm": 1700000000000, "goodsTpCd": "10",
            "images": [{"src": f"//images.samsung.com/kdp/goods/{gid}_1.jpg", "alt": nm}]}
products = {"G1": prod("hotel-tvs/all-hotel-tvs", "10001300", "G1", "호텔TV 8000 시리즈", "HG55BU800", "8000-series", ["LYNK Cloud 지원", "4K UHD"]),
            "G2": prod("led-signage/all-led-signage", "10001200", "G2", "실내용 LED 사이니지 IF 시리즈", "LH015IFH", "indoor", ["1.5mm 픽셀 피치"]),
            "G3": prod("tv-vd-solution/all-tv-vd-solution", "100002764", "G3", "링크 클라우드", "BW-HDLT11A", "lynk-cloud", None)}
variants = {"G1b": {"goodsId": "G1b", "mdlCode": "HG65BU800", "parentGoodsId": "G1", "optName": "사이즈", "optValue": "65"}}
P_ = {"cats": cats, "products": products, "cardOrder": ["G1", "G2", "G3"], "variants": variants,
      "filters": {"10001300": {"8000": ["G1"], "smart-tv": ["G1"]}, "10001200": {"indoor": ["G2"]}, "100002764": {"lynk-cloud": ["G3"]}}, "fetchedAt": "2026-10-04"}
specs = {"G1": [["기능", "삼성 LYNK™ Cloud", "있음"], ["디스플레이", "화면 크기", "138 cm"], ["디스플레이", "제품 사용 시간", "16/7"]],
         "G1b": [["디스플레이", "화면 크기", "163 cm"]],
         "G2": [["시각적 지표", "밝기", "500 nit"], ["동작조건", "IP 등급", "IP20"], ["동작조건", "동작온도", "0℃~+40℃"]]}
feats = {"G1": {"title": "호텔TV", "desc": "호텔 TV", "feats": [{"h": "호텔 객실 TV 통합 관리", "text": "호텔 객실 TV 통합 관리 LYNK Cloud로 원격 관리", "imgs": [{"src": "//images.samsung.com/kdp/goods/G1_feat.jpg", "alt": "객실에 설치된 TV"}]}]}}
fm = {"meta": {"10001300": {"8000": {"group": "시리즈", "label": "8000"}}, "10001200": {"indoor": {"group": "유형", "label": "실내용"}}},
      "members": {"10001300": ["G1"], "10001200": ["G2"], "100002764": ["G3"]}}
for n, d in [("wkb_products.json", P_), ("wkb_specs.json", specs), ("wkb_features.json", feats), ("wkb_filter_meta.json", fm), ("wkb_pages_v2.json", pages)]:
    (out / n).write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
(out / "prior_case_studies.json").write_text(json.dumps({"cases": [{"id": 1, "title": "인스파이어 리조트", "url": S + "/sec/business/insights/case-study/inspire/",
   "industry": ["호텔/서비스"], "space": ["로비", "객실"], "offer": ["LED 사이니지", "호텔 TV"], "proof": ["객실 1,275실 TV 통합 관리"], "customer_type": "리조트", "quote": "다채로운 경험을 제공"}]}, ensure_ascii=False), encoding="utf-8")
print("fixture ok")
