from fastapi import HTTPException, status
from sqlalchemy.orm import Session
# from app.utils.emailService import send_welcome_email
from app.utils.queryHelper import get_client_by_email
from app.utils.security import verify_password, create_access_token, hash_password
from app.model.client_model import Client
from app.schema.client_auth_schema import ClientCreate


def register_client(client: ClientCreate, db: Session):
    hashed = hash_password(client.password)
    fullName = f"{client.firstName} {client.lastName}"

    new_client = Client(
        fullName=fullName,
        firstName=client.firstName,
        lastName=client.lastName,
        email=client.email,
        role=client.role,
        hashedPassword=hashed,
        isEmailVerified= client.isEmailVerified
    )
    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    # send_welcome_email(client.email, client.role, fullName)

    return new_client


def login_client(email: str, password: str, db: Session):
    client = get_client_by_email(email, db)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address"
        )
    checkPassword = verify_password(password, client.hashedPassword)
    if not checkPassword:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        ) 
    token = create_access_token({"sub": client.email, "role": client.role})

    # return the client details together with the token
    return {
        "clientData": client,
        "access_token": token       
    }
