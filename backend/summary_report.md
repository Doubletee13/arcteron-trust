# `/backend/app/services/auth_service.py` - `register_step1`
```python
def register_step1(data: RegisterStep1, db: Session) -> User:
    # Check email exists
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check phone exists
    if db.query(User).filter(User.phone == data.phone).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )

    user = User(
        first_name=data.first_name,
        last_name=data.last_name,
        middle_name=data.middle_name,
        email=data.email,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        role=UserRole.user,
        status=UserStatus.active,
        is_kyc_complete=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user
```

# `/backend/app/services/auth_service.py` - `register_step3`
```python
def register_step3(user_id: str, data: RegisterStep3, db: Session) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.id_type = data.id_type
    user.id_number = data.id_number
    user.id_expiry_date = data.id_expiry_date
    user.employment_status = data.employment_status
    user.employer_name = data.employer_name
    user.annual_income = data.annual_income
    user.source_of_income = data.source_of_income
    user.account_purpose = data.account_purpose
    user.is_kyc_complete = True

    # Create bank account
    account_number = generate_account_number(db)
    account = Account(
        user_id=user.id,
        account_number=account_number,
        routing_number="021000021",
        account_type="checking",
        balance=0.00,
        currency="USD",
        swift_code="ARCTUSD1",
        bank_name="Arcteron Trust"
    )

    db.add(account)
    db.commit()
    db.refresh(user)

    # Generate token
    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    return {"access_token": token, "token_type": "bearer", "user": user_to_response(user)}
```

# `/backend/app/routers/auth.py` - `POST /api/auth/register/step1`
```python
@router.post("/register/step1")
def register_step_one(data: RegisterStep1, db: Session = Depends(get_db)):
    user = register_step1(data, db)
    return {
        "message": "Step 1 complete. Proceed to step 2.",
        "user_id": str(user.id)
    }
```

# `/backend/app/routers/auth.py` - `POST /api/auth/register/step3/{user_id}`
```python
@router.post("/register/step3/{user_id}", response_model=TokenResponse)
def register_step_three(user_id: str, data: RegisterStep3, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    result = register_step3(user_id, data, db)
    background_tasks.add_task(
        send_verification_email,
        result["user"]["email"],
        result["user"]["first_name"],
        generate_verification_token(result["user"]["email"])
    )
    return result
```

# `/backend/app/services/email_service.py` - `send_email`
```python
def send_email(to: str, subject: str, html_content: str):
    message = emails.Message(
        subject=subject,
        html=html_content,
        mail_from=(settings.APP_NAME, settings.MAIL_FROM)
    )

    response = message.send(
        to=to,
        smtp={
            "host": settings.MAIL_SERVER,
            "port": settings.MAIL_PORT,
            "tls": True,
            "user": settings.MAIL_USERNAME,
            "password": settings.MAIL_PASSWORD,
        }
    )
    print(f"EMAIL TO: {to} | STATUS: {response.status_code} | ERROR: {response.error}")
    if response.status_code not in (250, None):
        raise Exception(f"Email failed with status {response.status_code}: {response.error}")
    return response
```
