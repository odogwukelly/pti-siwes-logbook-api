from sqlalchemy.orm import Session
from app.model.client_model import Client
from app.schema.client_schema import ClientUpdate
from app.utils.security import hash_password

def update_client(client_id: int, update_data: ClientUpdate, db: Session):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        return None
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(client, field, value)
        
    db.commit()
    db.refresh(client)
    updated_user = db.query(Client).filter(Client.id == client_id).first()
    return updated_user
