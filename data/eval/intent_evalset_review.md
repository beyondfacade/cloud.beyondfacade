# 관문 평가셋 검수 시트

입력에 맞는 정답이면 `판정: O`, 틀린 칸은 `정답:` 줄을 고친 뒤 O. 쓸 수 없는 문항은 X.
정답 줄 형식: `정답: region=<동 이름|null> industry=<업종 id|null> budget=<원 정수|null>`

---
## i001 (landmark)
입력: 홍대입구역 근처에서 카페 하나 열고 싶어요
정답: region=서교동 industry=cafe budget=null
판정: O

## i002 (landmark)
입력: 가로수길에 파스타 가게 내려고 하는데 어때요?
정답: region=신사동 industry=western_food budget=null
판정: X  # 가로수길=강남구 신사동이 맞지만 masters에 신사동이 강남구·관악구 둘 — region_name만으로 어느 동인지 식별 불가

## i003 (landmark)
입력: 연트럴파크 근처 술집 창업 고민 중입니다
정답: region=연남동 industry=pub budget=null
판정: O

## i004 (landmark)
입력: 해방촌에서 작은 초밥집 열고 싶어요
정답: region=용산2가동 industry=japanese_food budget=null
판정: O

## i005 (landmark)
입력: 익선동 한옥거리에 카페 차리면 어떨까요
정답: region=종로1.2.3.4가동 industry=cafe budget=null
판정: O

## i006 (landmark)
입력: 여의도 직장인 상대로 한식 백반집 열 생각이에요
정답: region=여의동 industry=korean_food budget=null
판정: O

## i007 (landmark)
입력: 문래창작촌 근처에 양식 비스트로 어때요
정답: region=문래동 industry=western_food budget=null
판정: O

## i008 (landmark)
입력: 광장시장 근처에 국밥집 내고 싶은데 3천 정도 있어요
정답: region=종로1.2.3.4가동 industry=korean_food budget=30000000
판정: O  # 사용자 수정: 광장시장 주소 예지동 6-1 → 종로1·2·3·4가동 관할

## i009 (landmark)
입력: 을지로 노가리골목에서 호프집 하려고요
정답: region=을지로동 industry=pub budget=null
판정: O

## i010 (landmark)
입력: 건대입구 맛의거리에서 치킨집 창업 상담 받고 싶어요
정답: region=화양동 industry=chicken budget=null
판정: O

## i011 (landmark)
입력: 신촌 연세로 쪽 PC방 자리 알아보는 중이에요
정답: region=신촌동 industry=pc_bang budget=null
판정: O

## i012 (landmark)
입력: 가산디지털단지 근처에 헬스장 열면 수요 있을까요
정답: region=가산동 industry=gym budget=null
판정: O

## i013 (landmark)
입력: 코엑스 근처에서 돈카츠집 하고 싶습니다
정답: region=삼성1동 industry=japanese_food budget=null
판정: O

## i014 (landmark)
입력: 서래마을에 브런치 양식당 내려고 해요, 예산 2억
정답: region=반포4동 industry=western_food budget=200000000
판정: O

## i015 (industry_slang)
입력: 연남동에서 커피집 하나 해볼까 하는데요
정답: region=연남동 industry=cafe budget=null
판정: O

## i016 (industry_slang)
입력: 합정동 피시방 창업 어떤가요
정답: region=합정동 industry=pc_bang budget=null
판정: O

## i017 (industry_slang)
입력: 한남동에 미장원 차리고 싶어요
정답: region=한남동 industry=hair_salon budget=null
판정: O

## i018 (industry_slang)
입력: 공덕동에 통닭집 자리 보고 있어요
정답: region=공덕동 industry=chicken budget=null
판정: O

## i019 (industry_slang)
입력: 서교동 쪽에서 포차 하나 해보려고요
정답: region=서교동 industry=pub budget=null
판정: O

## i020 (industry_slang)
입력: 신림동에 국밥집 내면 장사 될까요?
정답: region=신림동 industry=korean_food budget=null
판정: O

## i021 (industry_slang)
입력: 화곡1동에서 복덕방 하려는데요
정답: region=화곡제1동 industry=real_estate budget=null
판정: O

## i022 (industry_slang)
입력: 대치4동에 보습학원 열고 싶습니다
정답: region=대치4동 industry=academy budget=null
판정: O

## i023 (industry_slang)
입력: 잠실본동에서 코인노래방 해볼까 해요
정답: region=잠실본동 industry=karaoke budget=null
판정: O

## i024 (industry_slang)
입력: 청담동에 중국집 차리면 어떨까요
정답: region=청담동 industry=chinese_food budget=null
판정: O

## i025 (industry_slang)
입력: 망원1동 떡볶이집 창업 문의드려요
정답: region=망원제1동 industry=snack budget=null
판정: O

## i026 (industry_slang)
입력: 쌍문1동 근처에 포켓볼 치는 데 차리면 어떨까요
정답: region=쌍문제1동 industry=billiard budget=null
판정: O

## i027 (industry_slang)
입력: 상계6.7동에 가정어린이집 열려고 합니다
정답: region=상계6.7동 industry=childcare budget=null
판정: O

## i028 (industry_slang)
입력: 성내1동에서 피트니스센터 창업하려고요
정답: region=성내제1동 industry=gym budget=null
판정: O

## i029 (budget)
입력: 연희동에서 카페 하려는데 5천 정도 생각해요
정답: region=연희동 industry=cafe budget=50000000
판정: O

## i030 (budget)
입력: 을지로동 호프집, 예산은 1억 2천이에요
정답: region=을지로동 industry=pub budget=120000000
판정: O

## i031 (budget)
입력: 삼천만원으로 신당동에서 분식집 가능할까요?
정답: region=신당동 industry=snack budget=30000000
판정: O

## i032 (budget)
입력: 방배본동 미용실 창업, 3천5백 있어요
정답: region=방배본동 industry=hair_salon budget=35000000
판정: O

## i033 (budget)
입력: 반포4동에 양식 레스토랑, 2억 안쪽으로요
정답: region=반포4동 industry=western_food budget=200000000
판정: O

## i034 (budget)
입력: 상도1동 편의점 8천만 원이면 될까요
정답: region=상도제1동 industry=convenience_store budget=80000000
판정: O

## i035 (budget)
입력: 보광동에서 일식집 하는데 4500만원 있습니다
정답: region=보광동 industry=japanese_food budget=45000000
판정: O

## i036 (budget)
입력: 홍제1동 치킨집, 딱 1억 있어요
정답: region=홍제제1동 industry=chicken budget=100000000
판정: O

## i037 (budget)
입력: 도화동 한식당 차리는데 칠천 정도요
정답: region=도화동 industry=korean_food budget=70000000
판정: O

## i038 (budget)
입력: 하계1동 PC방, 1.5억 예산입니다
정답: region=하계1동 industry=pc_bang budget=150000000
판정: O

## i039 (budget)
입력: 성북동에 카페 낼 건데 6천만원 선이에요
정답: region=성북동 industry=cafe budget=60000000
판정: O

## i040 (budget)
입력: 천호2동 노래방 창업 2억5천 가능할까요
정답: region=천호제2동 industry=karaoke budget=250000000
판정: O

## i041 (budget)
입력: 길동 헬스장 창업비로 9천만원 잡고 있어요
정답: region=길동 industry=gym budget=90000000
판정: O

## i042 (budget)
입력: 수서동 학원 개원 예산 오천만 원입니다
정답: region=수서동 industry=academy budget=50000000
판정: O

## i043 (missing)
입력: 카페 창업하려면 어디가 좋을까요?
정답: region=null industry=cafe budget=null
판정: O

## i044 (missing)
입력: 연남동 요즘 상권 어때요?
정답: region=연남동 industry=null budget=null
판정: O

## i045 (missing)
입력: 예산 1억으로 할 수 있는 거 추천해주세요
정답: region=null industry=null budget=100000000
판정: O

## i046 (missing)
입력: 서교동에서 치킨집 하고 싶어요
정답: region=서교동 industry=chicken budget=null
판정: O

## i047 (missing)
입력: 3천만원 있는데 편의점 해볼까요
정답: region=null industry=convenience_store budget=30000000
판정: O

## i048 (missing)
입력: 합정동에 5천 정도로 뭐 할 수 있을까요
정답: region=합정동 industry=null budget=50000000
판정: O

## i049 (missing)
입력: 창업 상담 좀 받고 싶어요
정답: region=null industry=null budget=null
판정: O

## i050 (missing)
입력: 헬스장 차리면 망할까요?
정답: region=null industry=gym budget=null
판정: O

## i051 (missing)
입력: 이태원1동에 가게 하나 내고 싶어요
정답: region=이태원제1동 industry=null budget=null
판정: O

## i052 (missing)
입력: 분식집 예산 4천이면 충분한가요
정답: region=null industry=snack budget=40000000
판정: O

## i053 (missing)
입력: 강남 쪽에서 술집 하려고요
정답: region=null industry=pub budget=null
판정: O

## i054 (missing)
입력: 청파동에 부동산 사무실 열려고 합니다
정답: region=청파동 industry=real_estate budget=null
판정: O

## i055 (missing)
입력: 아직 업종은 못 정했고 2억 정도 있어요
정답: region=null industry=null budget=200000000
판정: O

## i056 (out_of_scope)
입력: 부산 해운대에서 카페 하고 싶어요
정답: region=null industry=cafe budget=null
판정: O

## i057 (out_of_scope)
입력: 분당 정자동 치킨집 창업, 5천 있어요
정답: region=null industry=chicken budget=50000000
판정: O

## i058 (out_of_scope)
입력: 인천 송도에 학원 내려는데요
정답: region=null industry=academy budget=null
판정: O

## i059 (out_of_scope)
입력: 일산 라페스타 쪽 호프집 어떨까요
정답: region=null industry=pub budget=null
판정: O

## i060 (out_of_scope)
입력: 수원역 근처 PC방, 1억 예산이에요
정답: region=null industry=pc_bang budget=100000000
판정: O

## i061 (out_of_scope)
입력: 연남동에서 꽃집 하고 싶어요
정답: region=연남동 industry=null budget=null
판정: O

## i062 (out_of_scope)
입력: 망원2동 세탁소 창업 3천만원 있어요
정답: region=망원제2동 industry=null budget=30000000
판정: O

## i063 (out_of_scope)
입력: 한남동에 반려동물 미용샵 차리려고요
정답: region=한남동 industry=null budget=null
판정: O

## i064 (out_of_scope)
입력: 서교동에 네일샵 내고 싶은데 4천 있어요
정답: region=서교동 industry=null budget=40000000
판정: O

## i065 (out_of_scope)
입력: 제주 애월에 카페 하려고 2억 모았어요
정답: region=null industry=cafe budget=200000000
판정: O

## i066 (out_of_scope)
입력: 대치1동에 약국 개업하려고 합니다
정답: region=대치1동 industry=null budget=null
판정: O

## i067 (out_of_scope)
입력: 하남 미사에서 꽃집 하려는데 예산 3천
정답: region=null industry=null budget=30000000
판정: O

## i068 (out_of_scope)
입력: 경기도 광명 철산동에 헬스장 어때요
정답: region=null industry=gym budget=null
판정: O

## i069 (compound)
입력: 전에 강남에서 했는데 이번엔 연남동에서 카페 5천 정도로 다시 해보려고요
정답: region=연남동 industry=cafe budget=50000000
판정: O

## i070 (compound)
입력: 치킨집 접고 이번엔 서교동에서 호프집, 예산은 1억 정도예요
정답: region=서교동 industry=pub budget=100000000
판정: O

## i071 (compound)
입력: 친구는 부산에서 하는데 저는 망원1동에서 분식집 3천으로 해보려고요
정답: region=망원제1동 industry=snack budget=30000000
판정: O

## i072 (compound)
입력: 작년에 2억 날렸고 지금은 7천 있어요. 공덕동 한식당 어떨까요
정답: region=공덕동 industry=korean_food budget=70000000
판정: O

## i073 (compound)
입력: 카페랑 고민했는데 결국 합정동에 일식집으로 정했어요, 1억 2천
정답: region=합정동 industry=japanese_food budget=120000000
판정: O

## i074 (compound)
입력: 홍대 말고 연희동 쪽에서 미용실 열 건데 예산 4천5백이요
정답: region=연희동 industry=hair_salon budget=45000000
판정: O

## i075 (compound)
입력: 원래 분당에서 학원 했는데 대치4동으로 옮겨서 2억 정도로 하려고요
정답: region=대치4동 industry=academy budget=200000000
판정: O

## i076 (compound)
입력: 권리금 빼고 보증금 포함 6천, 화양동 PC방 가능할까요?
정답: region=화양동 industry=pc_bang budget=60000000
판정: O

## i077 (compound)
입력: 여의도 회사 그만두고 문래동에서 양식 비스트로, 8천 정도 생각 중
정답: region=문래동 industry=western_food budget=80000000
판정: O

## i078 (compound)
입력: 가로수길은 너무 비싸서 성북동에 카페 차리려고요, 3천5백 있습니다
정답: region=성북동 industry=cafe budget=35000000
판정: O

## i079 (compound)
입력: 중국집 하던 자리 인수해서 신당동에서 치킨집 하려고 해요, 1억 안쪽
정답: region=신당동 industry=chicken budget=100000000
판정: O

## i080 (compound)
입력: 헬스장이랑 당구장 중에 당구장으로 마음 굳혔어요. 길동, 6천
정답: region=길동 industry=billiard budget=60000000
판정: O

## i081 (compound)
입력: 인천에서 3년 장사했고 이제 목5동에서 부동산 중개사무소 2천으로
정답: region=목5동 industry=real_estate budget=20000000
판정: O

