
from sqlmodel import SQLModel, Session, Field, Relationship, create_engine
from typing import List, Optional

class Link(SQLModel, table=True):
    a_id: Optional[int] = Field(default=None, foreign_key="a.id", primary_key=True)
    b_id: Optional[int] = Field(default=None, foreign_key="b.id", primary_key=True)

class A(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    bs: List["B"] = Relationship(back_populates="as_list", link_model=Link)

class B(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    as_list: List["A"] = Relationship(back_populates="bs", link_model=Link)

def test_m2m_sync():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        a = A()
        b = B()
        session.add(a)
        session.add(b)
        session.commit()
        session.refresh(a)
        session.refresh(b)
        
        print(f"Before: a.bs={a.bs}, b.as_list={b.as_list}")
        
        # Action: Append to one side
        a.bs.append(b)
        # Check if other side is updated in memory
        print(f"After append to a.bs: a.bs={[x.id for x in a.bs]}, b.as_list={[x.id for x in b.as_list]}")
        
        if b in a.bs and a in b.as_list:
            print("Sync WORKED automatically.")
        else:
            print("Sync FAILED automatically.")

if __name__ == "__main__":
    test_m2m_sync()
