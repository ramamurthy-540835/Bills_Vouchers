import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.models import Account, AccountType

@pytest.fixture
def db():
    engine=create_engine("sqlite://"); Base.metadata.create_all(engine); session=sessionmaker(bind=engine)()
    session.add_all([Account(code="1000",name="Cash",account_type=AccountType.ASSET),Account(code="4000",name="Sales",account_type=AccountType.INCOME)])
    session.commit(); yield session; session.close()
