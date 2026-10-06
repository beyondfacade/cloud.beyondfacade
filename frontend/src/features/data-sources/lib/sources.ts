export interface DataSource {
  agency: string;
  dataset: string;
  terms: string;
  koglType1?: boolean;
  attribution?: string;
  links: { label: string; url: string }[];
}

const seoulDatasetUrl = (id: string) => `https://data.seoul.go.kr/dataList/${id}/S/1/datasetView.do`;

export const SOURCES: DataSource[] = [
  {
    agency: "서울특별시",
    dataset: "서울시 상권분석서비스(행정동)",
    terms: "공공누리 제1유형",
    koglType1: true,
    attribution: "본 서비스는 서울특별시가 공공누리 제1유형으로 개방한 '서울시 상권분석서비스(추정매출-행정동)' 등을 이용했으며, 해당 저작물은 서울 열린데이터광장(data.seoul.go.kr)에서 무료로 내려받을 수 있습니다.",
    links: [
      ["추정매출", "OA-22175"], ["점포", "OA-22172"], ["길단위인구", "OA-22178"],
      ["직장인구", "OA-22184"], ["상주인구", "OA-22183"], ["아파트", "OA-22163"],
      ["집객시설", "OA-22169"], ["소비", "OA-22166"], ["상권변화지표", "OA-15575"],
    ].map(([label, id]) => ({ label: `${label} ${id}`, url: seoulDatasetUrl(id) })),
  },
  {
    agency: "서울특별시교육청", dataset: "서울시 학원 교습소정보 OA-20528", terms: "공공누리 제1유형", koglType1: true,
    attribution: "본 서비스는 서울특별시교육청이 공공누리 제1유형으로 개방한 '서울시 학원 교습소정보'를 이용했으며, 해당 저작물은 서울 열린데이터광장(data.seoul.go.kr)에서 무료로 내려받을 수 있습니다.",
    links: [{ label: "서울시 학원 교습소정보 OA-20528", url: seoulDatasetUrl("OA-20528") }],
  },
  {
    agency: "서울특별시", dataset: "서울시 대규모점포 인허가 정보 OA-16096", terms: "공공누리 제1유형", koglType1: true,
    attribution: "본 서비스는 서울특별시가 공공누리 제1유형으로 개방한 '서울시 대규모점포 인허가 정보'를 이용했으며, 해당 저작물은 서울 열린데이터광장(data.seoul.go.kr)에서 무료로 내려받을 수 있습니다.",
    links: [{ label: "서울시 대규모점포 인허가 정보 OA-16096", url: seoulDatasetUrl("OA-16096") }],
  },
  {
    agency: "서울특별시", dataset: "서울시 공동주택 아파트 정보 OA-15818", terms: "공공누리 제1유형", koglType1: true,
    attribution: "본 서비스는 서울특별시가 공공누리 제1유형으로 개방한 '서울시 공동주택 아파트 정보'를 이용했으며, 해당 저작물은 서울 열린데이터광장(data.seoul.go.kr)에서 무료로 내려받을 수 있습니다.",
    links: [{ label: "서울시 공동주택 아파트 정보 OA-15818", url: seoulDatasetUrl("OA-15818") }],
  },
  {
    agency: "서울특별시", dataset: "서울시 도시정비사업 통계 OA-22856", terms: "이용 제한 없음",
    links: [{ label: "서울시 도시정비사업 통계 OA-22856", url: seoulDatasetUrl("OA-22856") }],
  },
  {
    agency: "한국부동산원", dataset: "부동산통계정보시스템(R-ONE) 상업용부동산 임대동향조사", terms: "출처표시 조건 자유이용",
    attribution: "출처: 한국부동산원 부동산통계정보시스템(R-ONE), 상업용부동산 임대동향조사",
    links: [{ label: "부동산통계정보시스템(R-ONE)", url: "https://www.reb.or.kr/r-one/" }],
  },
  {
    agency: "행정안전부", dataset: "지방행정 인허가 정보(일반음식점·휴게음식점·미용업·체력단련장업·당구장업·노래연습장업·인터넷컴퓨터게임시설제공업, 담배소매업)", terms: "이용 제한 없음",
    links: [{ label: "공공데이터포털 — 지방행정 인허가 정보", url: "https://www.data.go.kr/data/15154916/openapi.do" }],
  },
  {
    agency: "행정안전부", dataset: "주민등록 인구통계", terms: "이용 제한 없음",
    links: [{ label: "공공데이터포털 — 주민등록 인구통계", url: "https://www.data.go.kr/data/15097972/fileData.do" }],
  },
  {
    agency: "소상공인시장진흥공단", dataset: "상가(상권)정보", terms: "이용 제한 없음",
    links: [{ label: "공공데이터포털 — 상가(상권)정보", url: "https://www.data.go.kr/data/15012005/openapi.do" }],
  },
  {
    agency: "국토교통부", dataset: "아파트 매매 실거래가", terms: "이용 제한 없음",
    links: [{ label: "공공데이터포털 — 아파트 매매 실거래가", url: "https://www.data.go.kr/data/15126469/openapi.do" }],
  },
  {
    agency: "국토교통부", dataset: "부동산중개업 정보", terms: "이용 제한 없음",
    links: [{ label: "공공데이터포털 — 부동산중개업 정보", url: "https://www.data.go.kr/data/15123990/openapi.do" }],
  },
  {
    agency: "교육부", dataset: "어린이집정보공개포털 어린이집 기본정보", terms: "출처표시 조건",
    attribution: "출처: 교육부 어린이집정보공개포털(info.childcare.go.kr)",
    links: [{ label: "어린이집정보공개포털", url: "https://info.childcare.go.kr" }],
  },
  {
    agency: "한국은행", dataset: "경제통계시스템(ECOS) 기준금리·대출금리", terms: "원천 이용조건 확인",
    links: [{ label: "경제통계시스템(ECOS)", url: "https://ecos.bok.or.kr" }],
  },
  {
    agency: "중소벤처기업부", dataset: "기업마당 지원사업 공고", terms: "원천 이용조건 확인",
    attribution: "출처: 기업마당(중소벤처기업부)",
    links: [{ label: "기업마당", url: "https://www.bizinfo.go.kr" }],
  },
  {
    agency: "보건복지부", dataset: "코로나19 사회적 거리두기 현황", terms: "이용 제한 없음",
    links: [{ label: "공공데이터포털 — 코로나19 사회적 거리두기 현황", url: "https://www.data.go.kr/data/15098772/openapi.do" }],
  },
  {
    agency: "통계청", dataset: "통계지리정보서비스(SGIS) 주소 좌표 변환", terms: "원천 이용조건 확인",
    links: [{ label: "통계지리정보서비스(SGIS)", url: "https://sgis.mods.go.kr" }],
  },
  {
    agency: "국토교통부 공간정보 오픈플랫폼", dataset: "브이월드 배경지도·행정동 경계", terms: "© VWorld",
    links: [{ label: "브이월드", url: "https://www.vworld.kr" }],
  },
  {
    agency: "네이버", dataset: "뉴스 검색 API", terms: "네이버 검색 API 이용약관",
    attribution: "네이버 검색결과 — 리포트의 뉴스는 원문 링크로만 보여 줍니다",
    links: [{ label: "네이버 개발자센터", url: "https://developers.naver.com" }],
  },
];
