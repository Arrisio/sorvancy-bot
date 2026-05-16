# from db import public_models as models
from db import models as models
from db.models import Base

# skill2 = models.Skill(name='skilll2')
# skill3 = models.Skill(name='skilll3',external_id='a')
# skill4 = models.Skill(name='skilll3')


Base.metadata.schema = "is_budget"
Base.metadata.reflect()
# try:
#     CR.__table__.drop()
#     User.__table__.drop()
# e
#     print(e)

Base.metadata.drop_all(checkfirst=True)

#
#
Base.metadata.create_all(checkfirst=True)

#

# db_session.add(skill)
# db_session.add(skill2)
# db_session.add(skill3)
# db_session.add(skill4)
# db_session.commit()
#

