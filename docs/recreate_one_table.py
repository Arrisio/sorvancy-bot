from db.models import Document,MoneyTransfer
from  db.models.tmp_table import TmpTable, TmpTable2
from db.base import engine
from db.models._base import Base
from db.base import db_session
from db.helpers import register_base_modify_info_trigger




register_base_modify_info_trigger()

if __name__ == '__main__':
    Base.metadata.schema = "is_budget"
    Base.metadata.reflect(bind=engine)

    # MODEL = m.PurchaseRequestLineAllocation
    MODEL = MoneyTransfer
    # MODEL = db.models.PlanOrm
    TABLE = MODEL.__table__
    # TABLE = purchase_lines_assignees

    # TABLE =  db.models.
    try:
        TABLE.drop(bind=engine)
    except Exception as e:
        print('exception ...')
        db_session.rollback()
        print(e)

    TABLE.create(bind=engine)
