from app import db, Order, STATUS_CHOICES, app
from datetime import datetime, timedelta
import random

names = ["Juan Pérez", "Ana Gómez", "Carlos Ruiz", "María López", "Luis Rodríguez"]
plates = ["A123456", "B234567", "C345678", "D456789", "E567890"]
brands = ["Toyota", "Honda", "Nissan", "Hyundai", "Kia", "Mazda", "Suzuki", "Mitsubishi", "Ford", "Chevrolet"]
advisors = ["Roberto", "Laura", "Miguel", "Sofía"]
techs = ["T-01", "T-02", "T-03", "T-04"]
types = ["Mantenimiento", "Reparación", "Garantía", "Diagnóstico"]

with app.app_context():
    db.create_all()
    if Order.query.count() == 0:
        for i in range(20):
            created = datetime.utcnow() - timedelta(days=random.randint(0, 25))
            o = Order(
                order_number=f"OS-{1000+i}",
                plate=random.choice(plates),
                vin=f"VIN{i:06d}XYZ",
                chasis=f"CH{i:08d}",
                brand=random.choice(brands),
                customer_name=random.choice(names),
                advisor=random.choice(advisors),
                technician=random.choice(techs),
                service_type=random.choice(types),
                status=random.choice(STATUS_CHOICES[:-1]),
                priority=random.choice(["URGENTE", "NORMAL", "BAJA"]),
                promised_date=created + timedelta(days=random.randint(1, 7)),
                symptom="Ruido al frenar y vibración a 80km/h",
                created_at=created,
            )
            db.session.add(o)
        db.session.commit()
        print("Seeds cargados.")
    else:
        print("La base ya tiene datos. Nada que hacer.")
