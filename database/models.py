from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from config import CONFIG

Base = declarative_base()


class Rating(Base):
    __tablename__ = 'ratings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    question = Column(Text)
    answer = Column(Text)
    rating = Column(Integer)
    model = Column(String)


def get_database_url():
    db_type = CONFIG.get('DB_TYPE', 'sqlite')
    if db_type == 'postgres':
        user = CONFIG.get('POSTGRES_USER', 'postgres')
        password = CONFIG.get('POSTGRES_PASSWORD', 'password')
        host = CONFIG.get('POSTGRES_HOST', 'db')
        port = CONFIG.get('POSTGRES_PORT', '5432')
        db_name = CONFIG.get('POSTGRES_DB', 'ratings_db')

        return f'postgresql://{user}:{password}@{host}:{port}/{db_name}'
    else:
        return 'sqlite:///ratings.db'


DATABASE_URL = get_database_url()
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
