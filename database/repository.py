from sqlalchemy import Column, String, Integer, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
import datetime

class SQLLG:

class DatabaseRepository:
    def __init__(self, db):
        self.db = db

    def create_device(self, uuid: str, device_id: str, device_type: str, model_name: str, alias: str):
        new_device = DeviceModel(
            uuid=uuid,
            name=name,
            type=type,
            serial_number=serial_number,
            config=config
        )
        self.db.add(new_device)
        self.db.commit()
        self.db.refresh(new_device)
        return new_device