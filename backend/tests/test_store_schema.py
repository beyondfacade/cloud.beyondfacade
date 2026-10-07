"""store 스키마 — 동·업종 점포 목록(list_open)용 부분 인덱스 (부하 테스트 H8, 5차: DB 시간의 약 66%)."""
from sqlalchemy import text
from core.matrix.grid_oracle_database_manager import session_scope


def test_동_업종_영업중_점포_목록을_정렬된_채로_읽는_부분_인덱스가_있다():
    with session_scope() as s:
        indexdef = s.execute(text(
            "SELECT indexdef FROM pg_indexes WHERE tablename='store' AND indexname='ix_store_region_industry_open'"
        )).scalar()
    assert indexdef is not None
    assert "(region_code, industry_id, store_id)" in indexdef
    assert "close_date IS NULL" in indexdef and "lat IS NOT NULL" in indexdef and "lng IS NOT NULL" in indexdef
