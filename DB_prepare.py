from pathlib import Path
import pandas as pd
from sqlalchemy import (create_engine, Column, Integer, String, Text, Numeric,
                        ForeignKey, Date)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# ORM модели 
Base = declarative_base()

class PartnerType(Base):
    __tablename__ = "partner_types"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    partners = relationship("Partner", back_populates="partner_type")

class Partner(Base):
    __tablename__ = "partners"
    id = Column(Integer, primary_key=True)
    partner_type_id = Column(Integer, ForeignKey("partner_types.id"), nullable=False)
    name = Column(String(255), nullable=False)
    legal_address = Column(Text)
    inn = Column(String(10))
    director = Column(String(255))
    phone = Column(String(50))
    email = Column(String(255))
    rating = Column(Integer)

    partner_type = relationship("PartnerType", back_populates="partners")
    products = relationship("PartnerProduct", back_populates="partner")

class ProductType(Base):
    __tablename__ = "product_types"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    coefficient = Column(Numeric(10, 4), nullable=False)

    products = relationship("Product", back_populates="product_type")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    product_type_id = Column(Integer, ForeignKey("product_types.id"), nullable=False)
    article = Column(Integer, unique=True)
    name = Column(String(255), nullable=False)
    min_partner_price = Column(Numeric(12, 2))

    product_type = relationship("ProductType", back_populates="products")
    partner_products = relationship("PartnerProduct", back_populates="product")

class MaterialType(Base):
    __tablename__ = "material_types"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    defect_percentage = Column(Numeric(10, 4))

class PartnerProduct(Base):
    __tablename__ = "partner_products"
    id = Column(Integer, primary_key=True)
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer)
    sale_date = Column(Date)

    partner = relationship("Partner", back_populates="products")
    product = relationship("Product", back_populates="partner_products")

# Конфигурация 
DATA_DIR = Path(__file__).resolve().parent
DB_PATH = DATA_DIR / "app.db"
EXCEL_FILES = {
    "product_types": DATA_DIR / "import_data/Product_type_import.xlsx",
    "products": DATA_DIR / "import_data/Products_import.xlsx",
    "material_types": DATA_DIR / "import_data/Material_type_import.xlsx",
    "partners": DATA_DIR / "import_data/Partners_import.xlsx",
    "partner_products": DATA_DIR / "import_data/Partner_products_import.xlsx",
}

# Загрузка данных 
def load_data(session):
    # 1. Product types
    df_ptypes = pd.read_excel(EXCEL_FILES["product_types"])
    for _, row in df_ptypes.iterrows():
        session.add(
            ProductType(
                name=row["Тип продукции"],
                coefficient=row["Коэффициент типа продукции"],
            )
        )
    session.commit()

    # 2. Products
    df_products = pd.read_excel(EXCEL_FILES["products"])
    for _, row in df_products.iterrows():
        ptype = (
            session.query(ProductType)
            .filter_by(name=row["Тип продукции"])
            .one()
        )
        session.add(
            Product(
                product_type=ptype,
                article=int(row["Артикул"]),
                name=row["Наименование продукции"],
                min_partner_price=row["Минимальная стоимость для партнера"],
            )
        )
    session.commit()

    # 3. Material types
    df_mtypes = pd.read_excel(EXCEL_FILES["material_types"])
    for _, row in df_mtypes.iterrows():
        session.add(
            MaterialType(
                name=row["Тип материала"],
                defect_percentage=row["Процент брака материала "],
            )
        )
    session.commit()

    # 4. Partner types (выделяем уникальные значения из таблицы партнёров)
    df_partners = pd.read_excel(EXCEL_FILES["partners"])
    for ptype_name in df_partners["Тип партнера"].unique():
        if not session.query(PartnerType).filter_by(name=ptype_name).first():
            session.add(PartnerType(name=ptype_name))
    session.commit()

    # 5. Partners
    for _, row in df_partners.iterrows():
        ptype = (
            session.query(PartnerType)
            .filter_by(name=row["Тип партнера"])
            .one()
        )
        session.add(
            Partner(
                partner_type=ptype,
                name=row["Наименование партнера"],
                legal_address=row["Юридический адрес партнера"],
                inn=str(int(row["ИНН"])).zfill(10) if pd.notna(row["ИНН"]) else None,
                director=row["Директор"],
                phone=row["Телефон партнера"],
                email=row["Электронная почта партнера"],
                rating=int(row["Рейтинг"]) if pd.notna(row["Рейтинг"]) else None,
            )
        )
    session.commit()

    # 6. Partner products
    df_pp = pd.read_excel(EXCEL_FILES["partner_products"])
    for _, row in df_pp.iterrows():
        partner = (
            session.query(Partner)
            .filter_by(name=row["Наименование партнера"])
            .first()
        )
        product = session.query(Product).filter_by(
            name=row["Продукция"]
        ).first()
        if partner is None or product is None:
            print(
                f"!!! Пропуск строки: не найден партнёр или продукт: {row.to_dict()}"
            )
            continue
        session.add(
            PartnerProduct(
                partner=partner,
                product=product,
                quantity=int(row["Количество продукции"]),
                sale_date=pd.to_datetime(row["Дата продажи"]).date()
                if pd.notna(row["Дата продажи"])
                else None,
            )
        )
    session.commit()

def main():
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    with Session() as session:
        load_data(session)
    print(f"Готово! База данных создана в {DB_PATH}")

if __name__ == "__main__":
    main()

ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)